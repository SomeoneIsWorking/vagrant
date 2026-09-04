#!/usr/bin/env python3
"""Inspect the authenticated Vagrant Story PS-X EXE boot image.

This module is also the shared, read-only PS-X EXE image primitive used by the title's focused RE
instruments. It contains no execution-engine integration policy. Deeper crt0 measurements remain
recorded in ``docs/re-frontier.md``; executable boot belongs to the future psxport dynarec adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EXE = os.path.join(ROOT, "scratch", "bin", "vagrant", "SLUS_010.40")
FIXTURE_SHA1 = "fababcfd4325d42f350d95b3472874affeb0e48c"
HEADER_SIZE = 0x800


class Refuse(Exception):
    """Raised when an instrument cannot establish a result from its input."""


class Image:
    """Validated PS-X EXE with a bounded virtual-address-to-file mapping."""

    def __init__(self, path: str):
        self.path = path
        if not os.path.isfile(path):
            raise Refuse(
                f"no executable at {path}; nothing was scanned. "
                "Run tools/extract_exe.py against your own disc first"
            )
        with open(path, "rb") as source:
            self.data = source.read()
        if self.data[:8] != b"PS-X EXE":
            raise Refuse(
                f"{path}: expected PS-X EXE magic, found {self.data[:8]!r}; nothing was scanned"
            )
        if len(self.data) < 0x10 + 44:
            raise Refuse(f"{path}: truncated PS-X EXE header ({len(self.data)} bytes)")
        fields = struct.unpack("<11I", self.data[0x10 : 0x10 + 44])
        (
            self.pc0,
            self.gp0,
            self.t_addr,
            self.t_size,
            self.d_addr,
            self.d_size,
            self.b_addr,
            self.b_size,
            self.s_addr,
            self.s_size,
            self.sp_gp,
        ) = fields
        end = HEADER_SIZE + self.t_size
        if len(self.data) < end:
            raise Refuse(
                f"{path}: header declares 0x{self.t_size:X} loaded bytes but only "
                f"0x{max(0, len(self.data) - HEADER_SIZE):X} are present"
            )
        self.lo = self.t_addr
        self.hi = self.t_addr + self.t_size
        self.delta = self.t_addr - HEADER_SIZE
        if not self.inside(self.pc0):
            raise Refuse(
                f"{path}: entry 0x{self.pc0:08X} is outside loaded image "
                f"[0x{self.lo:08X},0x{self.hi:08X})"
            )

    def sha1(self) -> str:
        return hashlib.sha1(self.data).hexdigest()

    def inside(self, address: int) -> bool:
        return self.lo <= (address & 0xFFFFFFFF) < self.hi

    def off(self, address: int) -> int:
        return (address & 0xFFFFFFFF) - self.delta

    def r32(self, address: int) -> int:
        offset = self.off(address)
        if not (HEADER_SIZE <= offset <= len(self.data) - 4):
            raise Refuse(
                f"read 0x{address:08X} is outside loaded image "
                f"[0x{self.lo:08X},0x{self.hi:08X})"
            )
        return struct.unpack("<I", self.data[offset : offset + 4])[0]

    def word_at(self, address: int) -> int:
        return self.r32(address)


REGISTERS = (
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3",
    "t4", "t5", "t6", "t7", "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
)


def s16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def disasm1(word: int, pc: int) -> str:
    """Small audit disassembler; unknown instructions remain explicit raw words."""
    op = word >> 26
    rs, rt, rd = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    shift, function, immediate = (word >> 6) & 31, word & 63, word & 0xFFFF
    target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
    reg = lambda index: "$" + REGISTERS[index]
    if word == 0:
        return "nop"
    if op == 0:
        return {
            0x00: f"sll {reg(rd)}, {reg(rt)}, {shift}", 0x02: f"srl {reg(rd)}, {reg(rt)}, {shift}",
            0x03: f"sra {reg(rd)}, {reg(rt)}, {shift}", 0x08: f"jr {reg(rs)}",
            0x09: f"jalr {reg(rd)}, {reg(rs)}", 0x0D: "break",
            0x21: f"addu {reg(rd)}, {reg(rs)}, {reg(rt)}", 0x23: f"subu {reg(rd)}, {reg(rs)}, {reg(rt)}",
            0x24: f"and {reg(rd)}, {reg(rs)}, {reg(rt)}", 0x25: f"or {reg(rd)}, {reg(rs)}, {reg(rt)}",
            0x2A: f"slt {reg(rd)}, {reg(rs)}, {reg(rt)}", 0x2B: f"sltu {reg(rd)}, {reg(rs)}, {reg(rt)}",
        }.get(function, f".word 0x{word:08X}")
    return {
        0x02: f"j 0x{target:08X}", 0x03: f"jal 0x{target:08X}",
        0x04: f"beq {reg(rs)}, {reg(rt)}, 0x{pc + 4 + 4 * s16(immediate):08X}",
        0x05: f"bne {reg(rs)}, {reg(rt)}, 0x{pc + 4 + 4 * s16(immediate):08X}",
        0x08: f"addi {reg(rt)}, {reg(rs)}, {s16(immediate):#x}",
        0x09: f"addiu {reg(rt)}, {reg(rs)}, {s16(immediate):#x}",
        0x0A: f"slti {reg(rt)}, {reg(rs)}, {s16(immediate):#x}",
        0x0B: f"sltiu {reg(rt)}, {reg(rs)}, {s16(immediate):#x}",
        0x0C: f"andi {reg(rt)}, {reg(rs)}, {immediate:#x}",
        0x0D: f"ori {reg(rt)}, {reg(rs)}, {immediate:#x}",
        0x0F: f"lui {reg(rt)}, {immediate:#x}",
        0x23: f"lw {reg(rt)}, {s16(immediate):#x}({reg(rs)})",
        0x2B: f"sw {reg(rt)}, {s16(immediate):#x}({reg(rs)})",
    }.get(op, f".word 0x{word:08X}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("executable", nargs="?", default=DEFAULT_EXE)
    parser.add_argument("--disasm", type=lambda value: int(value, 0), metavar="ADDRESS")
    parser.add_argument("--count", type=int, default=32)
    args = parser.parse_args(argv)
    try:
        image = Image(args.executable)
        digest = image.sha1()
        if digest != FIXTURE_SHA1:
            raise Refuse(f"{args.executable}: sha1 {digest} != SLUS_010.40 {FIXTURE_SHA1}")
        print(f"sha1={digest}")
        print(
            f"entry=0x{image.pc0:08X} load=[0x{image.lo:08X},0x{image.hi:08X}) "
            f"size=0x{image.t_size:X}"
        )
        if args.disasm is not None:
            for index in range(args.count):
                address = args.disasm + index * 4
                word = image.word_at(address)
                print(f"{address:08X}  {word:08x}  {disasm1(word, address)}")
        return 0
    except (OSError, Refuse) as error:
        print(f"re_crt0 REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

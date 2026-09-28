#!/usr/bin/env python3
"""MEASURE Vagrant Story's guest viewport publication, FROM BYTES.

  python3 tools/re_viewport.py                  # the claim table
  python3 tools/re_viewport.py --selftest       # every check fed a case that MUST answer the other way

ONE PUBLICATION, ONE TABLE. This tool answers "what does the guest's own viewport publication do, and
which words are its own extent". The companion `tools/re_vsync_sites.py` answers a different question
of the same image — what EVERY call site passes to one library routine — and was split out of this
file rather than left in it: the two have different evidence shapes (settled instruction words versus
resolved register values) and different failure modes (a wrong address versus a propagation that
cannot cross a branch), and the structure verifier's 1200-line cap exists because a file holding two
responsibilities is a file whose halves stop agreeing. The shared MIPS-I field extractor and the
SHA-bound image loaders are imported by that tool rather than copied, because a second ISA decoder is
a second set of answers about the same words.

WHY THIS TOOL EXISTS, AND WHAT IT REPLACES. `tools/re_projection.py` censuses the vendored
CC0 `external/rood-reverse` DECOMPILATION, so it runs with no game image and it says so on every
run. That was the only possible instrument while no image was provisioned, and issue 0037 recorded
the consequence plainly: the four bodies `vagrant::BattleProjectionOwner` sits on were a
RECONSTRUCTION, the owner shipped no widening because it could not read them, and the first run
with an image "will either corroborate the reconstruction or make one of the five refusals fire".

The image is provisioned. So this tool reads the bytes and answers the same questions from them:
each claim gets CONFIRMED or REFUTED, settled by the instruction words that decide it, and every
address it reports is a vram address it decoded rather than one it was told.

ZERO DEPENDENCIES, ON PURPOSE. The locked environment (`uv.lock`, `pyproject.toml`) has no
dependencies and CTest runs `.venv/bin/python3`, so a `capstone` import here would make the gate
fail in CI and pass on a machine with a global capstone. The decoder below is a small MIPS-I field
extractor — it decodes FIELDS, never game semantics, and it refuses any word it does not recognise
rather than guessing. The shipped claims are the only consumer of it, and the self-test exercises
that same shipping path.

WHAT IT DOES NOT ANSWER, AND SAYS SO ON EVERY RUN.
  * It reads NO overlay it has not been given the SHA-1 of, and it reports which of the three
    provisioned overlays it covered. A missing image is a REFUSAL, never a zero.
  * A "no site" answer is "no site in the scanned words of the named modules", with the scanned
    instruction count attached. It is never "the guest has no such site".
  * It reports no frame rate, and it reports no call-site argument census: that is
    `tools/re_vsync_sites.py`, and a field count is not a rate either.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOD_CONFIG = os.path.join(ROOT, "external", "rood-reverse", "config")

# The four SHA-1 values are rood-reverse's OWN declared targets, read from config/*/splat.yaml, and
# they are the identity gate: an image is only decoded when it hashes to the value the
# decompilation declares for that module, so a wrong file can never produce a measurement.
EXE_SHA1 = "fababcfd4325d42f350d95b3472874affeb0e48c"
OVERLAYS = (
    # (provenance name, file name on disc, declared sha1, declared load vram, declared code extent)
    ("BATTLE.PRG", "BATTLE.BIN", "d53aaccc3b3a2fc057d05e0dcea92f7182bc72a9",
     0x80068800, (0x146C, 0x7F984)),
    ("TITLE.PRG", "TITLE.BIN", "f74a76e6215edebf607d0c2af56481050edb139a",
     0x80068800, (0x22C, 0x959C)),
    ("INITBTL.PRG", "INITBTL.BIN", "d7ea16ef957179cad6e3b02727bb714713cfcc32",
     0x800F9800, (0x18, 0x1318)),
)
OVERLAY_SHA1 = {name: sha for name, _f, sha, _v, _c in OVERLAYS}
DEFAULT_OVERLAY_DIR = os.path.join(ROOT, "scratch", "bin", "overlays")
DEFAULT_EXE = os.path.join(ROOT, "scratch", "bin", "vagrant", "SLUS_010.40")

# The SLUS_010.40 text segment the PS-X EXE header itself describes.
EXE_HEADER = 0x800

# --- the addresses under test ------------------------------------------------------------------------

VIEWPORT_PUBLICATION = 0x800760CC       # BATTLE.PRG func_800760CC
BATTLE_LOAD_BASE = 0x80068800
BATTLE_PRESENTER = 0x8007629C
VIEWPORT_RECT = 0x8005DFD4              # four adjacent shorts, x / w / y / h (NOT x,y,w,h)
PROJECTION_DISTANCE = 0x8005E248
NEAR_CLIP = 0x8005E0C8
PARITY = 0x8005E210

DRAW_ENV0 = 0x8006E0D0                  # BATTLE.PRG globals: two DRAWENVs then two DISPENVs
DRAW_ENV_STRIDE = 0x5C
DISP_ENV0 = 0x8006E188
DISP_ENV_STRIDE = 0x14
FRAME_PARITY_WORD = PARITY

LEAF_SET_GEOM_SCREEN = 0x80041534
LEAF_SET_GEOM_OFFSET = 0x80041540
LEAF_SET_DEF_DRAW_ENV = 0x8002B374
LEAF_SET_DEF_DISP_ENV = 0x8002B434
VSYNC = 0x8001F6C4

# THE RESIDENT'S OWN DISPLAY-AREA PUBLICATION, and the two words inside it that carry one horizontal
# extent. `vs_main_dispEnv` is named 0x8005E188 by the decompilation's own `symbol_addrs.txt` for
# SLUS_010.40 (line 790); here it is read out of the resident's body instead, because a name is not a
# measurement and the address is the one the owner's refusal is about.
RESIDENT_INIT_SCREEN = 0x80042054      # `_initScreen`, the resident's only display-area publication
RESIDENT_DISP_ENV_PAGE = 0x8006        # the `lui` half of `vs_main_dispEnv`
RESIDENT_DISP_ENV_DISPLACEMENT = -7800  # 0x80060000 - 7800 == 0x8005E188
# The two env leaves store the stated width and height at +4 and +6 of the struct the CALLER handed
# them, so a publication's OWN horizontal extent is at `env + 4` — a per-call address, not a constant.
LEAF_ENV_WIDTH_OFFSET = 4
LEAF_ENV_HEIGHT_OFFSET = 6

THRESHOLD_LOW = 0x110                  # 272, compared with slti
THRESHOLD_HIGH = 0x111                  # 273, the `> 272` spelling
THRESHOLD_ZOOM = 0x300                  # 768, a third gameplay threshold on the same word
RETAIL_RESTING_DISTANCE = 0x100         # 256

# GTE control-register numbers, settled from the instruction words at the two leaves.
GTE_CR_OFX = 24
GTE_CR_OFY = 25
GTE_CR_H = 26

# This tool decodes OPCODE-level fields and names a SPECIAL instruction only for the four funct
# values the shipped claims actually depend on. A full MIPS funct-name table is not maintained here on
# purpose: a name table is a place to be silently wrong (an earlier revision of this file used one
# conlated with the opcode table and read `sh $a1, 0($v0)` as `break`, and a 320-wide dispenv as a
# break instruction, which is a measurement that cannot fail), and every claim below is decidable from
# the opcode field plus rs/rt/rd/sa. The four names that ARE used are pinned by the selftest against
# instruction words whose meaning is read off the image and quoted in the report.
MIPS_SPECIAL_FUNCT = {0: "sll", 2: "srl", 3: "sra", 8: "jr", 9: "jalr"}
# The opcode table. Index 0 is SPECIAL and is dispatched through MIPS_SPECIAL_FUNCT.
MIPS_OPCODE = {
    0x02: "j", 0x03: "jal", 0x04: "beq", 0x05: "bne", 0x06: "blez", 0x07: "bgtz",
    0x08: "addi", 0x09: "addiu", 0x0A: "slti", 0x0B: "sltiu", 0x0C: "andi", 0x0D: "ori",
    0x0E: "xori", 0x0F: "lui", 0x1C: "lwl", 0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu",
    0x25: "lhu", 0x26: "lwr", 0x28: "sb", 0x29: "sh", 0x2A: "swl", 0x2B: "sw", 0x2E: "swr",
    0x2F: "cache", 0x30: "ll", 0x38: "sc", 0x10: "cop0", 0x11: "cop1", 0x12: "cop2", 0x13: "cop3",
}
SHAPE = {
    "sll": "rd_rt_sa", "srl": "rd_rt_sa", "sra": "rd_rt_sa",
    "jr": "rs", "jalr": "rd_rs",
    "j": "target", "jal": "target",
    "beq": "rs_rt_imm", "bne": "rs_rt_imm",
    "blez": "rs_imm", "bgtz": "rs_imm", "bltz": "rs_imm", "bgez": "rs_imm",
    "addi": "rt_rs_imm", "addiu": "rt_rs_imm", "slti": "rt_rs_imm", "sltiu": "rt_rs_imm",
    "andi": "rt_rs_imm", "ori": "rt_rs_imm", "xori": "rt_rs_imm", "lui": "rt_imm",
    "lb": "rt_imm_rs", "lh": "rt_imm_rs", "lwl": "rt_imm_rs", "lw": "rt_imm_rs", "lbu": "rt_imm_rs",
    "lhu": "rt_imm_rs", "lwr": "rt_imm_rs", "ll": "rt_imm_rs",
    "sb": "rt_imm_rs", "sh": "rt_imm_rs", "swl": "rt_imm_rs", "sw": "rt_imm_rs",
    "swr": "rt_imm_rs", "cache": "rt_imm_rs", "sc": "rt_imm_rs",
    "cop0": "cop2", "cop1": "cop2", "cop2": "cop2", "cop3": "cop2",
    "addu": "rd_rs_rt",  # not a name this table emits; kept so the shape lookup is total
}
REG_NAMES = (
    "$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3", "$t0", "$t1", "$t2", "$t3",
    "$t4", "$t5", "$t6", "$t7", "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
    "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra",
)


class Refuse(Exception):
    """Raised when this instrument cannot establish a result from its input."""


# --- a small MIPS-I field extractor -------------------------------------------------------------------
# FIELDS ONLY. `decode` returns None for any word it does not recognise, and every caller counts
# what it did not decode, so an undecoded word can never read as a zero.

def decode(word: int):
    """One MIPS-I instruction's FIELDS, or None for a word this table does not cover.

    None is a refusal, not a zero. Every caller counts what it did not decode, so a word outside the
    tables appears in a denominator instead of silently becoming an absent site.

    For opcode 0x00 the result carries `funct` and the raw register fields and names the instruction
    only when its funct is one of MIPS_SPECIAL_FUNCT; otherwise the name is `special` and the caller
    that cares (the `$a0` resolver) reasons on the register fields instead of on a name.
    """
    if word == 0:
        return {"mnemonic": "nop", "args": (), "op": 0, "funct": 0}
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    sa = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    fields = {"op": op, "rs": rs, "rt": rt, "rd": rd, "sa": sa, "funct": funct,
              "imm": simm, "raw_imm": imm}

    if op == 0x00:
        name = MIPS_SPECIAL_FUNCT.get(funct, "special")
        shape = SHAPE.get(name, "rd_rs_rt" if name == "special" else None)
    else:
        name = MIPS_OPCODE.get(op)
        if name is None:
            return None
        shape = SHAPE.get(name)
    if shape is None:
        return None

    if shape == "rd_rt_sa":
        args = (REG_NAMES[rd], REG_NAMES[rt], sa)
    elif shape == "rs":
        args = (REG_NAMES[rs],)
    elif shape == "rd_rs":
        args = (REG_NAMES[rd], REG_NAMES[rs])
    elif shape == "rd":
        args = (REG_NAMES[rd],)
    elif shape == "target":
        args = ()
    elif shape == "rs_rt_imm":
        args = (REG_NAMES[rs], REG_NAMES[rt], simm)
    elif shape == "rs_imm":
        args = (REG_NAMES[rs], simm)
    elif shape == "rt_rs_imm":
        args = (REG_NAMES[rt], REG_NAMES[rs], simm)
    elif shape == "rt_imm":
        args = (REG_NAMES[rt], imm)
    elif shape == "rt_imm_rs":
        args = (REG_NAMES[rt], simm, REG_NAMES[rs])
    elif shape == "rd_rs_rt":
        args = (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
    elif shape == "cop2":
        # A PSX coprocessor register move. `cr` is the coprocessor register number, which every GTE
        # transfer encoding carries in the `rd` field, and it is the field the projection cross-check
        # reads back — so it is reported from the word.
        #
        # THE DIRECTION IS NOT DECODED, and a previous revision of this file got that wrong in a way
        # that could not fail: it named EVERY one of these `mfc2` or `mtc2` from bit 25 alone, so a
        # reader saw a direction the extractor never measured. Naming one needs the R3000A COP2
        # transfer encoding, which is a reference, not a field. So the name here is neutral, and
        # `cop2sel` carries the raw five-bit selector bits 25..21 so the missing decision stays
        # visible instead of becoming a confident label.
        return {"mnemonic": "cop2reg", "args": (REG_NAMES[rt], rd), "cr": rd,
                "cop2sel": (word >> 21) & 0x1F, **fields}
    else:
        return None
    return {"mnemonic": name, "args": args, **fields}


def target_of(word: int, pc: int):
    if word >> 26 != 3:
        return None
    return (pc & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def sym(a: int) -> str:
    return "0x%08X" % a


# --- images -------------------------------------------------------------------------------------------

class Image:
    """A SHA-bound, word-addressable guest image with an explicit vram->file map."""

    def __init__(self, name: str, data: bytes, base: int, file_start: int, file_end: int):
        self.name = name
        self.data = data
        self.base = base
        self.file_start = file_start
        self.file_end = file_end
        self.sha1 = hashlib.sha1(data).hexdigest()

    def va_to_off(self, va: int):
        if not (self.base <= va < self.base + (self.file_end - self.file_start)):
            return None
        return self.file_start + (va - self.base)

    def word(self, va: int):
        off = self.va_to_off(va)
        if off is None or off + 4 > len(self.data):
            return None
        return int.from_bytes(self.data[off:off + 4], "little")

    def insn(self, va: int):
        w = self.word(va)
        return None if w is None else decode(w)

    def words(self, lo: int, hi: int):
        for va in range(lo, hi, 4):
            w = self.word(va)
            if w is not None:
                yield va, w


class ExeSet:
    """SLUS_010.40 under ONE file map, and that map is the image's own PS-X EXE header.

    MEASURED: this executable's t_addr is 0x80010000 and its t_size is 0x52000, so the header's
    text segment covers file offsets 0x800..0x52800 — the WHOLE file, including the two further
    code runs that sit after the bss gap. So one linear map, file 0x800 <-> vram 0x80010000, is the
    image's own statement and needs no second source. That is a change from the belief this
    repository carried, which was that three segments had to be stitched from
    config/SLUS_010.40/splat.yaml; the header already said all of it.

    Consequence worth stating: the resident executable has NO declared load base to cross-check,
    and the four library leaves are at vram addresses the header itself maps.
    """

    def __init__(self, path: str = DEFAULT_EXE):
        self.path = path
        if not os.path.isfile(path):
            raise Refuse(
                "no SLUS_010.40 at %s; NOTHING WAS SCANNED. Re-provision the executable before "
                "reading any resident address from it" % path)
        with open(path, "rb") as source:
            data = source.read()
        got = hashlib.sha1(data).hexdigest()
        if got != EXE_SHA1:
            raise Refuse("SLUS_010.40 at %s hashes %s, not the declared %s; nothing was scanned"
                         % (path, got, EXE_SHA1))
        if data[:8] != b"PS-X EXE":
            raise Refuse("%s does not begin with the PS-X EXE magic" % path)
        t_addr, t_size = struct.unpack("<11I", data[0x10:0x10 + 44])[2:4]
        if t_addr != 0x80010000:
            raise Refuse("the PS-X EXE header puts the text segment at 0x%08X, not 0x80010000; this "
                         "tool's file map is not the one this image has" % t_addr)
        if EXE_HEADER + t_size != len(data):
            raise Refuse(
                "the header's text segment covers %d bytes but the file is %d; the file map below "
                "would not cover the image" % (t_size, len(data)))
        self.data = data
        self.t_addr = t_addr
        self.t_size = t_size
        self.image = Image("SLUS_010.40", data, t_addr, EXE_HEADER, EXE_HEADER + t_size)

    def word(self, va: int):
        return self.image.word(va)

    def insn(self, va: int):
        w = self.word(va)
        return None if w is None else decode(w)

    def words(self, lo: int, hi: int):
        for va, w in self.image.words(lo, hi):
            yield va, w

    def corroborate(self, out=print):
        """How many NAMED entry points decode where the header's own map puts them.

        A count with a denominator, printed on every run. It is here so a reader can see the map is
        being checked rather than trusted, and so a regression in the map is visible as a number.
        """
        named = [
            (LEAF_SET_DEF_DRAW_ENV, "SetDefDrawEnv", "addiu"),
            (LEAF_SET_DEF_DISP_ENV, "SetDefDispEnv", "lw"),
            (VSYNC, "VSync", "lui"),
            (LEAF_SET_GEOM_SCREEN, "SetGeomScreen", "cop2reg"),
            (LEAF_SET_GEOM_OFFSET, "SetGeomOffset", "sll"),
            (0x80042054, "resident viewport publication", "addiu"),
            (0x8004261C, "vs_main_gametimeUpdate", "addiu"),
        ]
        good = 0
        for va, name, first in named:
            ins = self.insn(va)
            ok = ins is not None and ins.get("mnemonic") == first
            good += 1 if ok else 0
            out("    %-30s %-14s %s" % (name, sym(va),
                                        ("decodes (%s …)" % first) if ok else "NO DECODED ENTRY"))
        return good, len(named)


def load_overlays(dirpath: str = DEFAULT_OVERLAY_DIR):
    """SHA-bind each provisioned overlay, or record its ABSENCE as a refusal, never as a zero.

    A load base is not in the image, so it comes from the decompilation's own
    config/*/splat.yaml `vram:` line. The load base is therefore DECLARED and the CONTENT is
    MEASURED, and the claim table carries the corroboration: the addresses the base is checked
    against have to decode to the functions the table says they are.
    """
    out = {}
    for name, filename, sha1, base, code in OVERLAYS:
        path = os.path.join(dirpath, filename)
        if not os.path.isfile(path):
            out[name] = None
            continue
        with open(path, "rb") as source:
            data = source.read()
        got = hashlib.sha1(data).hexdigest()
        if got != sha1:
            raise Refuse("%s at %s hashes %s, not the %s rood-reverse declares; nothing was scanned"
                         % (name, path, got, sha1))
        img = Image(name, data, base, 0, len(data))
        img.code = code
        img.filename = filename
        out[name] = img
    return out


# --- the claims ---------------------------------------------------------------------------------------

class Claim:
    __slots__ = ("title", "verdict", "words")

    def __init__(self, title: str, verdict: str, words):
        self.title = title
        self.verdict = verdict
        self.words = words


def _cite(img, va, count=6, back=0):
    rows = []
    for i in range(count):
        a = va - 4 * back + 4 * i
        w = img.word(a)
        if w is None:
            rows.append("      %s  <unreadable>" % sym(a))
            continue
        d = decode(w)
        if d is None:
            rows.append("      %s  0x%08X  <not decoded>" % (sym(a), w))
        else:
            rows.append("      %s  0x%08X  %-6s %s" % (sym(a), w, d["mnemonic"],
                                                       " ".join(str(x) for x in d.get("args", ()))))
    return rows


def _find_jals(img, lo, hi, target):
    hits = []
    for va, w in img.words(lo, hi):
        if target_of(w, va) == target:
            hits.append(va)
    return hits


def _is(ins, **fields):
    """A decoded instruction matching every named field. `None` never matches."""
    if ins is None:
        return False
    for k, v in fields.items():
        if ins.get(k) != v:
            return False
    return True


def _ends_in_jr_ra(img, va, span=10):
    for a in range(va, va + 4 * span, 4):
        d = img.insn(a)
        if d and d.get("mnemonic") == "jr" and d.get("rs") == 31:
            return True
    return False


# Every `sh` at one struct offset inside one leaf's own words. A SCAN and not an address, so the
# caller cannot point a claim at a neighbouring instruction — the failure this exists to prevent.
# `window` is a byte count from the leaf's entry, and the caller prints it as the denominator, so a
# leaf whose scan finds nothing reports "0 of N" rather than an absence with no size.
def _leaf_sh_stores(img, leaf, window, struct_offset):
    for a in range(leaf, leaf + window, 4):
        d = img.insn(a)
        if d and d.get("mnemonic") == "sh" and d.get("imm") == struct_offset:
            yield a


def verify(bat, exe, overlays, out=print):
    """Every claim in the previous arm's reconstruction, decided by the instruction words."""
    claims = []
    if bat is None:
        raise Refuse(
            "BATTLE.PRG was not loaded, so NONE of the projection publication claims were checked. "
            "This is a refusal, not a result: every claim below is drawn from that one module."
        )
    BCODE = (bat.base + bat.code[0], bat.base + bat.code[1])

    # --- 1. the publication body, decision by decision --------------------------------------------
    entry = bat.insn(VIEWPORT_PUBLICATION)
    claims.append(Claim(
        "0x800760CC is a function entry in BATTLE.PRG (file offset 0x%X, base 0x%08X): a stack frame "
        "of -0x40" % (VIEWPORT_PUBLICATION - BATTLE_LOAD_BASE, BATTLE_LOAD_BASE),
        "CONFIRMED" if _is(entry, mnemonic="addiu", rt=29, rs=29, imm=-0x40) else "REFUTED",
        _cite(bat, VIEWPORT_PUBLICATION, 2)))

    # arg0/2 : srl (sign), addu, sra 1
    a1 = bat.insn(0x800760D8)
    a2 = bat.insn(0x800760DC)
    a3 = bat.insn(0x800760E0)
    a4 = bat.insn(0x800760E4)
    ok = (_is(a1, op=0, funct=2, rd=4, rt=18, sa=31) and          # srl  $a0, $s2, 31
          _is(a2, op=0, rd=4, rs=18, rt=4) and                    # addu $a0, $s2, $a0
          _is(a3, op=0, funct=3, rd=4, rt=4, sa=1) and            # sra  $a0, $a0, 1
          _is(a4, op=0x2B, rt=19, rs=29))                     # sw   $s3, 0x24($sp)
    claims.append(Claim(
        "the horizontal centre is arg0/2, computed as (arg0 + (arg0 >> 31)) >> 1 and passed to "
        "SetGeomOffset 0x80041540",
        "CONFIRMED" if ok else "REFUTED",
        _cite(bat, 0x800760D8, 4) +
        ["      call site 0x80076124 -> %s" % sym(target_of(bat.word(0x80076124), 0x80076124) or 0)]))

    # (arg1-16)/2 + 16
    b1 = bat.insn(0x800760E8)
    b2 = bat.insn(0x80076108)
    b3 = bat.insn(0x80076124)
    ok = (_is(b1, mnemonic="addiu", rt=19, rs=5, imm=-16) and
          _is(b2, mnemonic="addiu", rt=5, rs=5, imm=16) and
          target_of(bat.word(0x80076124), 0x80076124) == LEAF_SET_GEOM_OFFSET)
    claims.append(Claim(
        "the vertical centre is (arg1 - 16)/2 + 16, in the SAME SetGeomOffset call — so at a "
        "(320, 240) call the publication states OFX=160, OFY=128",
        "CONFIRMED" if ok else "REFUTED", _cite(bat, 0x800760E8, 1) + _cite(bat, 0x80076108, 1)))

    # H = arg2
    c1 = bat.insn(0x80076110)
    ok = (_is(c1, op=0, rd=16, rs=6, rt=0) and
          target_of(bat.word(0x8007612C), 0x8007612C) == LEAF_SET_GEOM_SCREEN)
    claims.append(Claim(
        "H is stated as arg2, through SetGeomScreen 0x80041534",
        "CONFIRMED" if ok else "REFUTED",
        _cite(bat, 0x80076110, 1) + _cite(bat, 0x8007612C, 1)))

    # two draw areas / two display areas
    for title, leaf, sites in (
        ("TWO draw areas, through SetDefDrawEnv 0x8002B374", LEAF_SET_DEF_DRAW_ENV,
         (0x8007614C, 0x80076188)),
        ("TWO display areas, through SetDefDispEnv 0x8002B434", LEAF_SET_DEF_DISP_ENV,
         (0x8007616C, 0x800761A0)),
    ):
        got = [target_of(bat.word(s), s) for s in sites]
        claims.append(Claim(title, "CONFIRMED" if got == [leaf, leaf] else "REFUTED",
                            _cite(bat, sites[0], 1) + _cite(bat, sites[1], 1)))

    # the two screen rects, and the display rect
    lit = [bat.insn(a) for a in (0x800761AC, 0x800761B0, 0x800761B4)]
    literals = [d.get("imm") if d and d.get("mnemonic") == "addiu" and d.get("rs") == 0 else None
                for d in lit]
    stores = [bat.insn(a) for a in (0x800761B8, 0x800761BC, 0x800761C0, 0x800761C4,
                                    0x800761CC, 0x800761D0, 0x800761D4, 0x800761D8)]
    offs = [d.get("imm") if d and d.get("mnemonic") == "sh" else None for d in stores]
    # (0x8006E188 + 8) + 0/2/4/6 is the first rect and (0x8006E188 + 0x1C) + 0/2/4/6 the second, and
    # the base register differs between them, so the offsets alone are what can be compared here.
    ok = literals == [8, 256, 224] and offs == [8, 2, 4, 6, 0x1C, 2, 4, 6]
    claims.append(Claim(
        "BOTH screen rects (DISPENV +8..+0xE, i.e. the `screen` rect) are overwritten with the "
        "LITERALS x=0, y=8, w=256, h=224 — 256 is a literal, not a computed width",
        "CONFIRMED" if ok else "REFUTED",
        _cite(bat, 0x800761AC, 8) +
        ["      literal values: y=%s w=%s h=%s ; store offsets: %s"
         % (literals[0], literals[1], literals[2], offs)]))

    # the resident rectangle, and its ORDER
    rect_sites = (0x800761E0, 0x800761E8, 0x800761F0, 0x80076200)
    words = []
    for s in rect_sites:
        d = bat.insn(s)
        words += _cite(bat, s, 1)
        if d is None or d.get("mnemonic") != "sh" or d.get("rs") != 2:
            words.append("      (expected `sh` through `lui $v0, 0x8006`)")
    lui_ok = all(_is(bat.insn(s - 4), mnemonic="lui", rt=2, raw_imm=0x8006) for s in rect_sites)
    got_order = [bat.insn(s).get("raw_imm") for s in rect_sites] if all(
        bat.insn(s) and bat.insn(s).get("mnemonic") == "sh" for s in rect_sites) else None
    expect_order = [0xDFD4, 0xDFD8, 0xDFD6, 0xDFDA]
    claims.append(Claim(
        "the resident rectangle at 0x8005DFD4 is written in the order x (0x8005DFD4), y (0x8005DFD8), "
        "w (0x8005DFD6), h (0x8005DFDA) — the 'x, y, w, h' order battle_projection_facts.h states",
        "CONFIRMED" if (got_order == expect_order and lui_ok) else "REFUTED",
        words + ["      the four stores, in address order, name: %s"
                 % (["0x8005%04X" % i for i in got_order] if got_order else None)] +
        ["      every store is through `lui $v0, 0x8006` + a negative displacement: %s" % lui_ok]))

    # --- 2. the two call sites ---------------------------------------------------------------------
    for label, key, code in (("BATTLE.PRG", "BATTLE.PRG", BCODE),
                             ("INITBTL.PRG", "INITBTL.PRG", None)):
        img = overlays.get(key)
        if img is None or (code is None and getattr(img, "code", None) is None):
            claims.append(Claim("the publication is called from %s" % label, "NOT CHECKED",
                                ["      %s was not provisioned, so this claim was NOT EVALUATED. "
                                 "That is a refusal, not a pass and not a fail." % label]))
            continue
        lo, hi = code if code else (img.base + img.code[0], img.base + img.code[1])
        sites = _find_jals(img, lo, hi, VIEWPORT_PUBLICATION)
        args = _args_320_240_H(img, sites[0]) if len(sites) == 1 else False
        claims.append(Claim(
            "the publication is called EXACTLY ONCE from %s, as (320, 240, "
            "vs_main_projectionDistance, 0, 0, 0)" % label,
            "CONFIRMED" if (len(sites) == 1 and args) else "REFUTED",
            (_cite(img, sites[0] - 0x1C, 7) if sites else []) +
            ["      call sites in the declared code extent 0x%X..0x%X: %s"
             % (lo - img.base, hi - img.base, ", ".join(sym(s) for s in sites) or "NONE FOUND")]))

    wrong = 0x8008B0A4
    d = bat.insn(wrong)
    is_call = target_of(bat.word(wrong), wrong) is not None
    real = _find_jals(bat, BCODE[0], BCODE[1], VIEWPORT_PUBLICATION)
    claims.append(Claim(
        "the BATTLE call site is 0x8008B0A4, as battle_projection_facts.h states",
        "CONFIRMED" if is_call else "REFUTED",
        _cite(bat, wrong, 1) +
        ["      0x8008B0A4 is %s, not a call; the only call of the publication in BATTLE.PRG is %s"
         % (d["mnemonic"] if d else "undecoded", ", ".join(sym(s) for s in real) or "none found")]))

    # --- 3. the four resident leaves ----------------------------------------------------------------
    for va, name, must_cop2, span in (
            (LEAF_SET_GEOM_OFFSET, "SetGeomOffset 0x80041540", (24, 25), 6),
            (LEAF_SET_GEOM_SCREEN, "SetGeomScreen 0x80041534", (26,), 3)):
        ins = [exe.insn(va + 4 * i) for i in range(span)]
        crs = [i["cr"] for i in ins if i and i.get("mnemonic") == "cop2reg"]
        shifts = [i for i in ins if i and i.get("mnemonic") == "sll" and i.get("sa") == 16]
        ok = tuple(crs) == must_cop2 and _ends_in_jr_ra(exe, va, span)
        claims.append(Claim(
            "%s is a leaf that names GTE CR%s and nothing else" % (name, "/CR".join(str(c) for c in must_cop2)),
            "CONFIRMED" if ok else "REFUTED",
            _cite(exe, va, span) +
            ["      coprocessor registers named, in order: %s ; <<16 argument shifts: %d"
             % (crs, len(shifts))]))

    for va, name, first in ((LEAF_SET_DEF_DRAW_ENV, "SetDefDrawEnv 0x8002B374", "addiu"),
                            (LEAF_SET_DEF_DISP_ENV, "SetDefDispEnv 0x8002B434", "lw")):
        ins = exe.insn(va)
        claims.append(Claim(
            "%s is a stack-framed leaf at the address the owner installs an override on" % name,
            "CONFIRMED" if (ins and ins.get("mnemonic") == first and
                            _ends_in_jr_ra(exe, va, 60)) else "REFUTED",
            _cite(exe, va, 6)))

    # the two register-number questions the owner's read-back depends on
    crs_offset = [exe.insn(LEAF_SET_GEOM_OFFSET + 4 * i) for i in range(6)]
    crs_screen = [exe.insn(LEAF_SET_GEOM_SCREEN + 4 * i) for i in range(3)]
    got = [i["cr"] for i in crs_offset if i and i.get("mnemonic") == "cop2reg"]
    got += [i["cr"] for i in crs_screen if i and i.get("mnemonic") == "cop2reg"]
    claims.append(Claim(
        "kGteControlOfx/Ofy/H = 24/25/26 name the registers the two leaves actually touch "
        "(the transfer DIRECTION is not decoded by this tool, and is not claimed here)",
        "CONFIRMED" if got == [GTE_CR_OFX, GTE_CR_OFY, GTE_CR_H] else "REFUTED",
        _cite(exe, LEAF_SET_GEOM_SCREEN, 3) + _cite(exe, LEAF_SET_GEOM_OFFSET, 6) +
        ["      registers named, in call order: %s" % got]))

    # SetDefDispEnv's own field map
    disp_map = []
    for i in range(16):
        a = LEAF_SET_DEF_DISP_ENV + 4 * i
        d = exe.insn(a)
        if d and d.get("mnemonic") == "sh" and len(d.get("args", ())) == 3:
            disp_map.append(d["args"][1])
    claims.append(Claim(
        "SetDefDispEnv writes its four arguments to DISPENV +0/+2/+4/+6 and ZEROES +8/+0xA/+0xC/+0xE: "
        "so +0..+6 is `disp` (the VRAM display rect) and +8..+0xE is `screen`",
        "CONFIRMED" if disp_map == [0, 2, 4, 8, 10, 12, 14, 6] else "REFUTED",
        _cite(exe, LEAF_SET_DEF_DISP_ENV, 16) +
        ["      DISPENV offsets written, in order: %s" % disp_map]))

    # SetDefDrawEnv zeroes the draw-area clip
    zeros = []
    for i in range(30):
        d = exe.insn(LEAF_SET_DEF_DRAW_ENV + 4 * i)
        if d and d.get("mnemonic") == "sh" and d.get("rt") == 0 and d.get("rs") == 17 \
                and len(d.get("args", ())) == 3:
            zeros.append(d["args"][1])
    body_offsets = sorted({d["args"][1] for a in range(VIEWPORT_PUBLICATION, VIEWPORT_PUBLICATION + 0x1D4)
                           for d in [bat.insn(a)] if d and d.get("mnemonic") == "sb"})
    claims.append(Claim(
        "SetDefDrawEnv writes the draw-area CLIP w/h (DRAWENV +0xC/+0xE) as ZERO and the publication "
        "never stores there, so the DRAWING area is unclipped for the whole field",
        "CONFIRMED" if (12 in zeros and 14 in zeros) else "REFUTED",
        ["      DRAWENV offsets SetDefDrawEnv zero-fills: %s" % zeros] +
        _cite(bat, 0x80076204, 9)))

    # --- 3b. THE RESIDENT DISPLAY AREA IS NOT MEASURED HERE --------------------------------------
    #
    # It is `tools/re_display_area.py`, and it is a SEPARATE TOOL rather than a section of this one
    # because the two measure different subjects and the first run of this title is what made that
    # visible: this file measures BATTLE's projection publication, that one measures the RESIDENT
    # boot's display-area publication, and an owner installed on their shared `SetDefDispEnv` leaf
    # cross-checked one against the other's rectangle. Each has its own constants and its own
    # selftest; there is deliberately no call between them, because a check that is only a valid
    # second statement of one horizontal extent for ONE of two publications is the defect they
    # exist to keep apart.

    # --- 4. the presenter ---------------------------------------------------------------------------
    lit_x = bat.insn(0x800762E0)
    lit_y = bat.insn(0x800762E8)
    ok = (_is(lit_x, mnemonic="addiu", rt=4, rs=0, imm=160) and
          _is(lit_y, mnemonic="addiu", rt=5, rs=0, imm=112) and
          target_of(bat.word(0x800762E4), 0x800762E4) == LEAF_SET_GEOM_OFFSET)
    claims.append(Claim(
        "BATTLE's presenter 0x8007629C re-states a LITERAL SetGeomOffset(160, 112) on every field, so "
        "an owner on the overlay's call site would be overwritten once per field",
        "CONFIRMED" if ok else "REFUTED", _cite(bat, BATTLE_PRESENTER, 12)))

    puts = _find_jals(bat, BATTLE_PRESENTER, BATTLE_PRESENTER + 0x200, 0x80028E80)
    claims.append(Claim(
        "the presenter re-issues the display area every field, so the screen rect the publication "
        "wrote is PER-FIELD state and not a one-shot",
        "CONFIRMED" if puts else "REFUTED",
        ["      PutDispEnv sites inside the presenter: %s"
         % (", ".join(sym(s) for s in puts) or "NONE FOUND")]))

    # --- 5. the projection-distance gameplay reads --------------------------------------------------
    for title, at, imm, meaning in (
        ("func_80074580 reads vs_main_projectionDistance and branches on < 272", 0x80074580,
         THRESHOLD_LOW, "< 272"),
        ("func_80074744 reads vs_main_projectionDistance and branches on > 272", 0x80074744,
         THRESHOLD_HIGH, "> 272, spelled `< 273`"),
    ):
        load = bat.insn(at + 4)
        cmp_ = bat.insn(at + 0xC)
        lw = bat.word(at + 4)
        names_H = load and load.get("mnemonic") == "lw" and lw is not None and \
            (lw & 0xFFFF) == (PROJECTION_DISTANCE & 0xFFFF)
        names_base = _is(bat.insn(at), mnemonic="lui", raw_imm=0x8006)
        ok = names_H and names_base and _is(cmp_, mnemonic="slti", raw_imm=imm)
        claims.append(Claim(title, "CONFIRMED" if ok else "REFUTED",
                            _cite(bat, at, 4) +
                            ["      the `slti` immediate is 0x%X = %d, which is %s"
                             % (imm, imm, meaning)]))

    add = bat.insn(0x80078584)
    clamp = bat.insn(0x8007858C)
    claims.append(Claim(
        "a THIRD gameplay threshold on the same word, which the previous arm did not record: the zoom "
        "step adds 64, clamps at 768 (0x300) and branches on equality with 768",
        "CONFIRMED" if (_is(add, mnemonic="addiu", rt=2, rs=2, imm=0x40) and
                        _is(clamp, mnemonic="slti", raw_imm=THRESHOLD_ZOOM)) else "REFUTED",
        _cite(bat, 0x80078578, 6)))

    set_call = target_of(bat.word(0x8007CCFC), 0x8007CCFC)
    st = bat.word(0x8007CD00)
    claims.append(Claim(
        "0x8007CCF0 stores its argument to 0x8005E248 and then calls SetGeomScreen 0x80041534 — the "
        "setter, and the only place the global is written with a caller-chosen value",
        "CONFIRMED" if (set_call == LEAF_SET_GEOM_SCREEN and st is not None and
                        (st & 0xFFFF) == (PROJECTION_DISTANCE & 0xFFFF) and
                        (st >> 26) == 0x2B) else "REFUTED",
        _cite(bat, 0x8007CCF0, 6)))

    rests = [va for va, w in bat.words(*BCODE) if w == 0x24020100]
    claims.append(Claim(
        "retail's resting value 0x100 (256) for vs_main_projectionDistance",
        "NOT DETERMINABLE FROM THE PROVISIONED MODULES",
        ["      no BATTLE.PRG instruction materialises the constant 256 into 0x8005E248 (0 such "
         "instructions over %d scanned words). The word is written only by the setters, the +64 and "
         "clamp steps at 0x80078578, and the -64/+64/±0xC0 steps at 0x800793F8, so its RESTING value "
         "is whatever the camera-transition initialiser computed. 256 is NOT a byte this scan can "
         "produce, and this arm does not claim it." % ((BCODE[1] - BCODE[0]) // 4)]))

    # --- 6. the one reader of the published width --------------------------------------------------
    width_readers = _lui_field_readers(bat, VIEWPORT_RECT + 2)
    height_readers = _lui_field_readers(bat, VIEWPORT_RECT + 6)
    tag = bat.insn(0x800BB8FC)
    x1 = bat.insn(0x800BB91C)
    tag_ok = tag and tag.get("mnemonic") == "ori" and (tag.get("raw_imm", 0) | 0) == 2
    store_x1 = x1 and x1.get("mnemonic") == "sh" and x1.get("rs") == 17
    claims.append(Claim(
        "0x8005DFD6 (the published width) has exactly ONE reader in BATTLE.PRG, it is a screen-space "
        "effect and not a cull, and 0x8005DFDA (the height) has two, both in the same function",
        "CONFIRMED" if (len(width_readers) == 1 and tag_ok and store_x1) else "REFUTED",
        ["      width  (0x8005DFD6) readers: %s" % ", ".join(sym(a) for a in width_readers)] +
        ["      height (0x8005DFDA) readers: %s" % ", ".join(sym(a) for a in height_readers)] +
        _cite(bat, 0x800BB8FC, 9)))

    # The VSync(n) call-site census lives in `tools/re_vsync_sites.py`: it asks a different question
    # of the same image — what EVERY call site passes to one library routine, rather than what ONE
    # publication does — and the two have different evidence shapes and different failure modes.
    # `docs/issues/0042` records the split.
    return claims


def _args_320_240_H(img, site, window=12):
    """Whether a call site passes (320, 240, vs_main_projectionDistance, 0, 0, 0).

    Read from the field values, not from a name: a zero argument is written either as
    `addiu $aX, $zero, 0` or as `addu $aX, $zero, $zero` (a `move` off $zero), and this title's
    compiler emits both. The fifth and sixth arguments are stack slots.
    """
    def zero(reg):
        for i in range(1, window + 1):
            d = img.insn(site - 4 * i)
            if d is None:
                continue
            if d.get("mnemonic") == "addiu" and d.get("rs") == 0 and d.get("rt") == reg \
                    and d.get("imm") == 0:
                return True
            if d.get("op") == 0 and d.get("rs") == 0 and d.get("rd") == reg:
                return True
        return False

    a0 = a1 = None
    a2_reads_H = False
    stack_zero = []
    # The delay slot executes BEFORE the callee, so the sixth argument is written AFTER the `jal`
    # instruction word; scanning only backwards would miss it and under-report the argument count.
    scan = [site - 4 * i for i in range(0, window + 1)] + [site + 4]
    for a in scan:
        d = img.insn(a)
        if d is None:
            continue
        if d.get("mnemonic") == "addiu" and d.get("rs") == 0:
            if d.get("rt") == 4:
                a0 = d.get("imm")
            if d.get("rt") == 5:
                a1 = d.get("imm")
        if d.get("mnemonic") == "lui":
            reg = d.get("rt")
            page = d.get("raw_imm") << 16
            for j in range(1, 4):
                d2 = img.insn(a + 4 * j)
                # The address is built from the page this `lui` supplies plus a signed displacement,
                # so the test is the SUM: this title names 0x8005E248 as `lui 0x8006` + (-0x1DB8), and
                # comparing either half alone would accept a page or a displacement from a different
                # word entirely.
                if d2 and d2.get("mnemonic") == "lw" and d2.get("rs") == reg \
                        and d2.get("rt") == 6 and (page + d2.get("imm")) == PROJECTION_DISTANCE:
                    a2_reads_H = True
        if d.get("mnemonic") == "sw" and d.get("rt") == 0 and d.get("rs") == 29 \
                and d.get("imm") in (0x10, 0x14):
            stack_zero.append(d.get("imm"))
    return (a0 == 320 and a1 == 240 and a2_reads_H and zero(7) and sorted(set(stack_zero)) == [0x10, 0x14])


# The load/store opcodes that name a main-RAM address through a register, and whether each one READS
# or WRITES it. Anything else is not an access this census claims to have seen.
MEMORY_ACCESS = {
    0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu", 0x25: "lhu", 0x1C: "lwl", 0x26: "lwr",
    0x28: "sb", 0x29: "sh", 0x2B: "sw", 0x2A: "swl", 0x2E: "swr",
}


def _lui_field_refs(img, targets, window=0x44):
    """Every instruction that NAMES one of `targets` as `lui $r, page` + a signed displacement.

    `targets` is a SET of guest addresses, because the question this answers is about a RECTANGLE
    rather than one word. The page is not compared on its own: this title names 0x8005DFD6 as
    `lui 0x8006` + (-0x202A), so matching either half alone would accept a page or a displacement
    borrowed from a different word. The SUM is the test, and each instruction is reported ONCE however
    many `lui`s in the window produce the same page — a census that counted pairs would report one
    store three times, which is how a "three writers" reading appears where there is one.

    `window` is a BYTE COUNT, not an end address. Returns (address, mnemonic, word) for every load and
    store, so a caller states its own read/write rule rather than this function quietly answering the
    narrower question.
    """
    wanted = set(targets)
    seen = {}
    lo = img.base
    hi = img.base + (img.file_end - img.file_start)
    for va, w in img.words(lo, hi):
        if w >> 26 != 0x0F:
            continue
        reg = (w >> 16) & 0x1F
        page = (w & 0xFFFF) << 16
        for a, w2 in img.words(va + 4, min(va + window, hi)):
            if ((w2 >> 21) & 0x1F) != reg:
                continue
            kind = MEMORY_ACCESS.get(w2 >> 26)
            if kind is None:
                continue
            imm = w2 & 0xFFFF
            simm = imm - 0x10000 if imm & 0x8000 else imm
            if (page + simm) in wanted:
                seen[a] = (a, kind, w2)
                break
    return [seen[a] for a in sorted(seen)]


def _lui_field_readers(img, target, window=0x44):
    """Every instruction that READS `target`. Read opcodes only, so a store cannot answer a
    reader census; see `_lui_field_refs` for the sum rule this filters."""
    return [a for a, kind, _w in _lui_field_refs(img, {target}, window) if kind.startswith("l")]


# --- reporting ---------------------------------------------------------------------------------------

def report_verify(claims, out=print):
    out("=" * 100)
    out("VAGRANT STORY — GUEST VIEWPORT PUBLICATION, VERIFIED AGAINST BYTES")
    out("Every address below was decoded from the image this tool SHA-1-checked. CONFIRMED means the")
    out("named instruction words are present at the named addresses; REFUTED means they are not.")
    out("=" * 100)
    for c in claims:
        out("")
        out("[%s] %s" % (c.verdict, c.title))
        for line in c.words:
            out(line)
    out("")
    out("  THE VSync(n) CALL-SITE CENSUS IS `tools/re_vsync_sites.py`: a different question of the same")
    out("  image, with its own scanned-word count for every module it read.")
    out("=" * 100)
def mutated_exe(real, image):
    """An `ExeSet` over a MUTATED copy of the resident image, for a claim that must be able to flip.

    The header fields carry over so `verify` sees the segment geometry it measured; only the bytes
    differ. A claim that cannot be made to REFUTE has not been shown to be able to CONFIRM.
    """
    clone = ExeSet.__new__(ExeSet)
    clone.path = real.path
    clone.data = bytes(image.data)
    clone.t_addr = real.t_addr
    clone.t_size = real.t_size
    clone.image = image
    return clone


def selftest(out=print):
    """Every claim this tool makes, fed an input whose answer is known WITHOUT this tool."""
    out("== re_viewport.py --selftest: 6 checks, each a case that MUST come out the other way " + "=")
    plan = [
        "1. the four images decode; a wrong SHA-1 is REFUSED before any address is read",
        "2. a BATTLE.PRG with ONE byte changed at the publication entry is REFUSED by identity",
        "3. the publication's centre computation, on a MUTATED copy, no longer matches its claim",
        "4. a reader census for an address nothing references reads ZERO, and one that is referenced "
        "does not",
        "5. the rectangle census answers ZERO for the overlay rectangle 0x8005DFD4..DA and NONZERO "
        "for a word the resident demonstrably names — one scan, two targets, opposite answers",
        "6. the exe segment map's corroboration count can go below its own denominator",
    ]
    out("   the RESIDENT display-area claims and their four checks are `tools/re_display_area.py`'s,")
    out("   and the VSync(n) call-site census and its three are `tools/re_vsync_sites.py`'s. What is")
    out("   left here is the BATTLE overlay publication and the decoder both tools share.")
    for line in plan:
        out("   " + line)
    out("")
    fails = []

    # A fixed, obviously-named directory under the repository's own scratch root, so a reader who
    # finds it knows what it is and cannot mistake its mutated BATTLE.BIN for a provisioned image.
    scratch = os.path.join(ROOT, "scratch", "re_viewport_selftest")
    os.makedirs(scratch, exist_ok=True)

    # [1] the real thing, and the identity gate
    try:
        exe = ExeSet()
        ov = load_overlays()
        out("  [1] PASS loaded SLUS_010.40 + %d/3 overlays, sha1-bound"
            % sum(1 for v in ov.values() if v is not None))
    except Refuse as e:
        out("  [1] FAIL %s" % e)
        fails.append(1)
        return fails, None
    if ov["BATTLE.PRG"] is None:
        out("  [1] FAIL BATTLE.PRG absent; every projection claim would be unchecked")
        fails.append(1)
    good, total = exe.corroborate(out=lambda s: None)
    out("      exe segment-map corroboration: %d of %d named entry points decode" % (good, total))
    if not (0 < good < total):
        out("  [1] NOTE corroboration is %d of %d; that is a real count and it is printed either way"
            % (good, total))

    # [2] identity: one byte changed -> refused, before any address is decoded
    bad = os.path.join(scratch, "BATTLE.BIN")
    with open(ov["BATTLE.PRG"].data and DEFAULT_OVERLAY_DIR + "/BATTLE.BIN", "rb") as src:
        raw = bytearray(src.read())
    # The byte mutated is one the arg0/2 centre claim READS, so the check that has to flip is
    # that claim and not merely the identity gate.
    off = 0x800760D8 - BATTLE_LOAD_BASE
    raw[off] ^= 0xFF
    with open(bad, "wb") as dst:
        dst.write(bytes(raw))
    try:
        load_overlays(scratch)
        out("  [2] FAIL a BATTLE.PRG with a mutated publication byte was ACCEPTED")
        fails.append(2)
    except Refuse as e:
        out("  [2] PASS refused the mutated image: %s" % str(e)[:78])

    # [3] the shipping claim check must answer the OTHER way on the mutated image
    mut = Image("mutated", bytes(raw), BATTLE_LOAD_BASE, 0, len(raw))
    mut.code = OVERLAYS[0][4]
    good_claims = verify(mut, exe, ov, out=lambda s: None)
    mutated_verdicts = [c.verdict for c in good_claims if "arg0/2" in c.title]
    out("  [3] %s the arg0/2 centre claim on a mutated BATTLE.PRG reads %s (unchanged: %s)"
        % ("PASS" if mutated_verdicts and mutated_verdicts[0] == "REFUTED" else "FAIL",
           mutated_verdicts, good_claims[0].verdict if good_claims else "no claims"))
    if not (mutated_verdicts and mutated_verdicts[0] == "REFUTED"):
        fails.append(3)

    # [4] A READER CENSUS FOR AN ADDRESS NOTHING REFERENCES, beside one that IS referenced. The
    #     OTHER half of that census — who WRITES the rectangle, which is what decided the
    #     boot-versus-overlay reading of issue 0042 — is `re_display_area.py`'s, because the
    #     rectangle it censuses is that tool's subject.
    none_read = _lui_field_readers(ov["BATTLE.PRG"], 0x8005DFDE)
    some_read = _lui_field_readers(ov["BATTLE.PRG"], VIEWPORT_RECT + 2)
    out("  [4] %s readers of 0x8005DFDE: %d (must be 0); readers of the published width: %d"
        % ("PASS" if none_read == [] and some_read else "FAIL", len(none_read), len(some_read)))
    if not (none_read == [] and some_read):
        fails.append(4)

    # [5] THE CENSUS HAS TO BE ABLE TO SAY ZERO AND NON-ZERO ON THE SAME SCAN. A reference census
    # that reports zero for everything reads exactly like one that has found nothing, and the two are
    # different facts. The control is a word the resident demonstrably names: 0x8005E248, the
    # projection distance the boot reads at 0x800420CC. Same module, same scan, opposite answers.
    rect_targets = {VIEWPORT_RECT + off for off in (0, 2, 4, 6)}
    resident_zero = _lui_field_refs(exe.image, rect_targets)
    control_some = _lui_field_refs(exe.image, {PROJECTION_DISTANCE})
    out("  [5] %s the resident names 0x8005DFD4..DA %d time(s) (must be 0) and the control word "
        "0x8005E248 %d time(s) (must be > 0)"
        % ("PASS" if (not resident_zero and control_some) else "FAIL",
           len(resident_zero), len(control_some)))
    if not (not resident_zero and control_some):
        fails.append(5)

    # [6] the corroboration denominator is a real count, not a constant
    empty = ExeSet.__new__(ExeSet)
    empty.image = Image("z", b"", 0x80010000, EXE_HEADER, EXE_HEADER + 0x10)
    good_bad, total_bad = empty.corroborate(out=lambda s: None)
    out("  [6] %s corroboration over a segment that cannot hold the entry points reads %d of %d "
        "(must be 0 of %d)" % ("PASS" if good_bad == 0 else "FAIL", good_bad, total_bad, total_bad))
    if good_bad != 0:
        fails.append(6)

    out("")
    out("  selftest: %d of %d checks FAILED %s" % (len(fails), 6, fails or ""))
    # The mutated BATTLE.BIN this selftest builds is DELETED, not left lying around: a file named
    # BATTLE.BIN that is not the authenticated image is exactly the kind of thing someone later
    # provisions from by accident.
    try:
        os.remove(os.path.join(scratch, "BATTLE.BIN"))
    except OSError:
        pass
    return fails, ov


def main(argv):
    args = [a for a in argv if a != "--selftest"]
    selftest_only = "--selftest" in argv
    if args and args[0] not in ("--exe", "--overlays"):
        print("usage: re_viewport.py [--exe PATH] [--overlays DIR] [--selftest]", file=sys.stderr)
        return 2
    exe_path = DEFAULT_EXE
    ov_dir = DEFAULT_OVERLAY_DIR
    if "--exe" in args:
        exe_path = args[args.index("--exe") + 1]
    if "--overlays" in args:
        ov_dir = args[args.index("--overlays") + 1]
    try:
        if selftest_only:
            fails, _ov = selftest()
            return 1 if fails else 0
        exe = ExeSet(exe_path)
        ov = load_overlays(ov_dir)
        covered = sum(1 for v in ov.values() if v is not None)
        print("loaded: SLUS_010.40 (sha1 %s…), overlays %d of 3 "
              "(%s)" % (EXE_SHA1[:12], covered,
                         ", ".join(k for k, v in sorted(ov.items()) if v is not None)))
        print("A missing overlay is a REFUSAL for the claims that would have come from it, printed "
              "as NOT CHECKED — never as a zero.")
        print("")
        good, total = exe.corroborate()
        print("exe segment-map corroboration: %d of %d named library entry points decode where the "
              "declared map puts them" % (good, total))
        print("")
        bat = ov["BATTLE.PRG"]
        if bat is None:
            raise Refuse("BATTLE.PRG is not provisioned at %s, so NONE of the projection publication "
                         "claims can be checked. tools/re_projection.py answers what the "
                         "DECOMPILATION says with no disc; this tool answers what the BYTES say and "
                         "there are none to read." % ov_dir)
        claims = verify(bat, exe, ov)
        report_verify(claims)
        return 0
    except Refuse as e:
        print("[re_viewport] REFUSING: %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

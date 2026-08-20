#!/usr/bin/env python3
"""Measure Vagrant Story's libpad buffers and pointer table from SLUS_010.40.

The result feeds GameConfig's pad seam.  The matching decomp is useful for names, but this tool finds
the setup by its instruction shape, derives every address from the owned executable, and compares the
shipping constants back to that measurement.
"""

import os
import re
import struct
import sys

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse, s16

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_SRC = os.path.join(ROOT, "game", "core", "game_config.cpp")


def read_config():
    with open(CONFIG_SRC) as src:
        return src.read()


def words(img):
    for va in range(img.lo, img.hi, 4):
        yield va, img.r32(va)


def jal_target(pc, word):
    if word >> 26 != 3:
        raise Refuse(f"expected jal at 0x{pc:08X}, found raw word 0x{word:08X}")
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def reg_base(lui_word, addiu_word, reg):
    want_lui = (0x0F << 26) | (reg << 16)
    want_addiu = (0x09 << 26) | (reg << 21) | (reg << 16)
    if lui_word & 0xFFFF0000 != want_lui or addiu_word & 0xFFFF0000 != want_addiu:
        raise Refuse(
            f"cannot decode r{reg} base from 0x{lui_word:08X}, 0x{addiu_word:08X}"
        )
    return (((lui_word & 0xFFFF) << 16) + s16(addiu_word & 0xFFFF)) & 0xFFFFFFFF


def find_setup(img):
    """Find _sysInit's PadInitDirect sequence without using an address or symbol as input."""
    matches = []
    scanned = 0
    for va, w in words(img):
        if va + 0x50 >= img.hi:
            break
        scanned += 1
        if w & 0xFFFF0000 != 0x3C100000:  # lui s0, hi(buffer0)
            continue
        if img.r32(va + 0x20) & 0xFFFF0000 != 0x26100000:  # addiu s0, s0, lo
            continue
        if img.r32(va + 0x28) & 0xFFFF0000 != 0x26110000:  # addiu s1, s0, stride
            continue
        if img.r32(va + 0x2C) != 0x02002021 or img.r32(va + 0x34) != 0x02202821:
            continue  # move a0,s0 / move a1,s1
        if img.r32(va + 0x30) >> 26 != 3:
            continue
        # The same helper resets slot 0 and slot 1 immediately after PadInitDirect. This rejects a
        # coincidentally similar two-buffer call and proves the second pointer is a pad slot.
        if (
            img.r32(va + 0x38) != 0x00002021
            or img.r32(va + 0x40) != 0x02002821
            or img.r32(va + 0x44) != 0x24040010
            or img.r32(va + 0x4C) != 0x02202821
        ):
            continue
        if img.r32(va + 0x3C) >> 26 != 3 or img.r32(va + 0x48) != img.r32(va + 0x3C):
            continue
        matches.append(va)
    if len(matches) != 1:
        shown = ", ".join(f"0x{x:08X}" for x in matches[:8]) or "none"
        raise Refuse(
            f"pad setup: scanned {scanned} word-aligned candidates, matched {len(matches)} "
            f"({shown}); cannot identify a unique two-slot setup"
        )
    return matches[0], scanned


def measure(img, verify_identity=True):
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(
            f"{img.path}: sha1 {img.sha1()} != SLUS_010.40 {FIXTURE_SHA1}; "
            "nothing was measured"
        )

    setup, scanned = find_setup(img)
    slot0 = reg_base(img.r32(setup), img.r32(setup + 0x20), 16)
    slot_stride = s16(img.r32(setup + 0x28) & 0xFFFF)
    slot1 = (slot0 + slot_stride) & 0xFFFFFFFF
    if slot_stride <= 0 or slot1 >= img.hi:
        raise Refuse(
            f"pad setup 0x{setup:08X}: invalid buffer stride {slot_stride}; "
            f"slot0=0x{slot0:08X}, image_hi=0x{img.hi:08X}"
        )

    pad_init = jal_target(setup + 0x30, img.r32(setup + 0x30))
    # PadInitDirect preserves a0/a1 in s1/s2, builds its driver-state base in s0, then records those
    # two pointers in equal-stride fields. These raw relations establish the optional pointer table.
    expected = {0x00: 0x27BDFFE0, 0x08: 0x00808821, 0x2C: 0x00A09021}
    for off, want in expected.items():
        got = img.r32(pad_init + off)
        if got != want:
            raise Refuse(
                f"PadInitDirect 0x{pad_init:08X}: contract mismatch at +0x{off:X}: "
                f"0x{got:08X} != 0x{want:08X}"
            )
    store0, store1 = img.r32(pad_init + 0xD8), img.r32(pad_init + 0xDC)
    if store0 & 0xFFFF0000 != 0xAE110000 or store1 & 0xFFFF0000 != 0xAE120000:
        raise Refuse(
            f"PadInitDirect 0x{pad_init:08X}: expected adjacent sw s1/s2 pointer stores, "
            f"found 0x{store0:08X}, 0x{store1:08X}"
        )
    table_offset = s16(store0 & 0xFFFF)
    second_offset = s16(store1 & 0xFFFF)
    table_stride = second_offset - table_offset
    if table_offset < 0 or table_stride <= 0:
        raise Refuse(
            f"PadInitDirect 0x{pad_init:08X}: invalid pointer offsets "
            f"{table_offset}, {second_offset}"
        )
    state = reg_base(img.r32(pad_init + 0x30), img.r32(pad_init + 0x34), 16)
    table = state + table_offset
    return {
        "setup": setup,
        "PadInitDirect": pad_init,
        "slot0": slot0,
        "slot1": slot1,
        "slot_stride": slot_stride,
        "table": table,
        "table_stride": table_stride,
        "scanned": scanned,
    }


def parse_constant(text, name):
    m = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+|[0-9]+)u?", text)
    if not m:
        raise Refuse(
            f"{CONFIG_SRC}: did not find {name}; cannot compare shipping pad seam"
        )
    return int(m.group(1), 0)


def check_config(measured, text):
    fields = {
        "kPadSlot0Buf": "slot0",
        "kPadSlot1Buf": "slot1",
        "kPadSlotPtrTable": "table",
        "kPadSlotPtrStride": "table_stride",
    }
    failures = []
    for constant, key in fields.items():
        got, want = parse_constant(text, constant), measured[key]
        ok = got == want
        print(
            f"  [{'ok' if ok else 'FAIL':>4}] {constant} shipped=0x{got:08X} measured=0x{want:08X}"
        )
        if not ok:
            failures.append(constant)
    for field, constant in (
        ("padSlot0Buf", "kPadSlot0Buf"),
        ("padSlot1Buf", "kPadSlot1Buf"),
        ("padSlotPtrTable", "kPadSlotPtrTable"),
        ("padSlotPtrStride", "kPadSlotPtrStride"),
    ):
        if not re.search(rf"\.{field}\s*=\s*{constant}\b", text):
            failures.append(f"{field} binding")
    if failures:
        raise Refuse("shipping mismatch: " + ", ".join(failures))


def selftest(img, measured):
    print("== re_pad selftest ==")
    checks = 0
    check_config(measured, read_config())
    checks += 1

    original = img.data
    mutable = bytearray(original)
    off = img.off(measured["setup"] + 0x2C)
    mutable[off : off + 4] = struct.pack("<I", 0)
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError("destroyed two-buffer call shape was accepted")
    except Refuse as e:
        if "scanned" not in str(e) or "matched 0" not in str(e):
            raise AssertionError(f"negative lacked denominator: {e}")
        print(f"  [ ok ] destroyed setup refused: {e}")
        checks += 1
    finally:
        img.data = original

    text = read_config()
    changed = text.replace(
        f"kPadSlot0Buf = 0x{measured['slot0']:08X}",
        f"kPadSlot0Buf = 0x{measured['slot0'] + 4:08X}",
        1,
    )
    if changed == text:
        raise AssertionError("shipping mutation anchor did not fire")
    try:
        check_config(measured, changed)
        raise AssertionError("+4 shipping slot was accepted")
    except Refuse as e:
        if "kPadSlot0Buf" not in str(e):
            raise AssertionError(f"shipping negative did not name kPadSlot0Buf: {e}")
        print(f"  [ ok ] +4 shipping slot refused: {e}")
        checks += 1
    print(f"re_pad selftest: {checks}/3 PASS")


def main(argv):
    args = list(argv)
    do_check = "--check-config" in args
    do_selftest = "--selftest" in args
    args = [a for a in args if a not in ("--check-config", "--selftest")]
    if len(args) > 1:
        print(
            "usage: re_pad.py [--check-config] [--selftest] [SLUS_010.40]",
            file=sys.stderr,
        )
        return 2
    try:
        img = Image(args[0] if args else DEFAULT_EXE)
        m = measure(img)
        print("== Vagrant libpad seam ==")
        print(
            f"  setup 0x{m['setup']:08X} -> PadInitDirect 0x{m['PadInitDirect']:08X} "
            f"({m['scanned']} candidates scanned)"
        )
        print(
            f"  slot buffers 0x{m['slot0']:08X}, 0x{m['slot1']:08X} "
            f"({m['slot_stride']} bytes each)"
        )
        print(
            f"  driver pointer table 0x{m['table']:08X}, stride {m['table_stride']} bytes"
        )
        print(
            "  boundary: this identifies input delivery only; no frame loop is claimed"
        )
        if do_check:
            check_config(m, read_config())
        if do_selftest:
            selftest(img, m)
        return 0
    except (Refuse, OSError, AssertionError) as e:
        print(f"re_pad REFUSED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

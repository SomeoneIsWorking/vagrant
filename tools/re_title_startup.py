#!/usr/bin/env python3
"""Measure TITLE's first direct-native sprite producer from the retail overlay.

The first non-black boot picture is publisher/developer art drawn through TITLE's immediate
``_drawSprt(xy, uvClut, wh, tpageFade)`` leaf. This instrument derives that leaf from the owned,
SHA-bound overlay using its complete semantic shape; verifies the calls, static packet buffer, GP0
opcode, and argument stores; then gates the shipping override address. No decomp symbol or guessed
address is an input to the measurement.
"""

import argparse
import re
import struct
import sys

from re_frame import DEFAULT_TITLE, TITLE_BASE, TITLE_SHA1, Overlay, jal_word
from re_crt0 import Refuse, s16
from re_spu_transfer import unique_shape

DRAW_SYNC = 0x80028650
DRAW_PRIM = 0x80028BE8
SOURCE = "game/render/title_startup.cpp"


def materialized_address(overlay, hi_offset, lo_offset, base_reg, destination_reg):
    hi_word = overlay.r32(hi_offset)
    lo_word = overlay.r32(lo_offset)
    if hi_word >> 26 != 0x0F or (hi_word >> 16) & 31 != base_reg:
        raise Refuse(f"expected lui for register {base_reg} at 0x{hi_offset:08X}")
    if (
        lo_word >> 26 not in (0x08, 0x09)
        or (lo_word >> 21) & 31 != base_reg
        or (lo_word >> 16) & 31 != destination_reg
    ):
        raise Refuse(
            f"expected addi/addiu from register {base_reg} to {destination_reg} "
            f"at 0x{lo_offset:08X}"
        )
    return (((hi_word & 0xFFFF) << 16) + s16(lo_word & 0xFFFF)) & 0xFFFFFFFF


def measure(title, verify_identity=True):
    if verify_identity:
        title.check_identity()

    # Four ABI arguments are preserved in s1/s2/s3/s0. The body waits for the GPU, builds one
    # immediate 0x64 SPRT in a static packet, then calls DrawPrim. The opcode and exact field stores
    # distinguish it from the overlay's other immediate primitive helpers.
    draw_sprite, scanned = unique_shape(
        title,
        "TITLE immediate sprite leaf",
        {
            0x00: 0x27BDFFD8,
            0x04: 0xAFB10014,
            0x08: 0x00808821,
            0x0C: 0xAFB20018,
            0x10: 0x00A09021,
            0x14: 0xAFB3001C,
            0x18: 0x00C09821,
            0x1C: 0xAFB00010,
            0x20: 0x00E08021,
            0x24: 0xAFBF0020,
            0x28: jal_word(DRAW_SYNC),
            0x2C: 0x00002021,
            0x30: 0x3C03800E,
            0x34: 0x2464ED28,
            0x38: 0x3C020500,
            0x40: 0x320209FF,
            0x44: 0x3C03E100,
            0x4C: 0x00108403,
            0x50: 0x24030080,
            0x6C: 0x3C036400,
            0x74: 0xAC820008,
            0x78: 0xAC91000C,
            0x7C: 0xAC920010,
            0x80: jal_word(DRAW_PRIM),
            0x84: 0xAC930014,
            0x9C: 0x03E00008,
            0xA0: 0x27BD0028,
        },
    )

    packet = materialized_address(title, draw_sprite + 0x30, draw_sprite + 0x34, 3, 4)
    if (title.r32(draw_sprite + 0x3C) & 0xFFFF) != (packet & 0xFFFF):
        raise Refuse("TITLE sprite leaf does not initialise the packet whose fields it stores")

    # The first boot splash owner is independently located by its 320x512 clear, embedded publisher
    # uploads, two 364-field loops, and calls to this measured leaf. This ties the generic leaf to the
    # observed boot frontier instead of merely proving a dormant renderer helper exists.
    publisher_owner, publisher_scanned = unique_shape(
        title,
        "TITLE publisher/developer splash owner",
        {
            0x00: 0x27BDFF50,
            0x04: 0x27A40090,
            0x14: 0x24020140,
            0x18: 0xA7A20094,
            0x1C: 0x24020200,
            0x34: 0xA7A00090,
            0x38: 0xA7A00092,
            0x3C: jal_word(0x800287D4),  # ClearImage
            0x40: 0xA7A20096,
            0x44: 0x3C040040,
            0x48: 0x34840140,
        },
    )
    calls = []
    for va in range(publisher_owner, min(publisher_owner + 0x500, title.hi), 4):
        if title.r32(va) == jal_word(draw_sprite):
            calls.append(va)
    if len(calls) != 2:
        shown = ", ".join(f"0x{va:08X}" for va in calls) or "none"
        raise Refuse(
            f"publisher/developer owner: scanned 0x500 bytes, matched {len(calls)} calls "
            f"to sprite leaf ({shown}); expected exactly 2"
        )

    return {
        "draw_sprite": draw_sprite,
        "packet": packet,
        "publisher_owner": publisher_owner,
        "publisher_calls": calls,
        "scanned": scanned,
        "publisher_scanned": publisher_scanned,
    }


def check_source(measured, text):
    match = re.search(r"\bkTitleDrawSprite\s*=\s*(0x[0-9A-Fa-f]+)u?", text)
    if not match:
        raise Refuse(f"{SOURCE}: kTitleDrawSprite is absent")
    shipped = int(match.group(1), 0)
    if shipped != measured["draw_sprite"]:
        raise Refuse(
            f"{SOURCE}: kTitleDrawSprite=0x{shipped:08X}, measured 0x{measured['draw_sprite']:08X}"
        )
    gen = f"ov_title_gen_{measured['draw_sprite']:08X}"
    if text.count(gen) < 2:
        raise Refuse(f"{SOURCE}: measured generated super body {gen} is not retained and installed")
    print(f"  [ ok ] shipping producer address/super-call: 0x{shipped:08X} / {gen}")


def selftest(title, measured, source_text):
    print("== re_title_startup selftest ==")
    checks = 0

    original = title.data
    mutable = bytearray(original)
    off = title.off(measured["draw_sprite"] + 0x80)
    mutable[off : off + 4] = struct.pack("<I", 0)
    title.data = bytes(mutable)
    try:
        measure(title, verify_identity=False)
        raise AssertionError("destroyed DrawPrim call was accepted")
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"destroyed DrawPrim negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed DrawPrim refused: {error}")
        checks += 1
    finally:
        title.data = original

    shifted = source_text.replace(
        f"0x{measured['draw_sprite']:08X}u", f"0x{measured['draw_sprite'] + 4:08X}u", 1
    )
    try:
        check_source(measured, shifted)
        raise AssertionError("shifted shipping producer address was accepted")
    except Refuse as error:
        print(f"  [ ok ] shifted shipping producer refused: {error}")
        checks += 1

    mutable = bytearray(original)
    mutable[0] ^= 1
    title.data = bytes(mutable)
    try:
        measure(title)
        raise AssertionError("one-byte-mutated overlay passed identity")
    except Refuse as error:
        if "sha1" not in str(error):
            raise AssertionError(f"identity negative did not name sha1: {error}")
        print(f"  [ ok ] one-byte-mutated TITLE refused before measurement: {error}")
        checks += 1
    finally:
        title.data = original

    print(f"== re_title_startup selftest PASS ({checks}/3) ==")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("title", nargs="?", default=DEFAULT_TITLE)
    parser.add_argument("--check-source", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    try:
        title = Overlay(args.title, TITLE_BASE, TITLE_SHA1)
        measured = measure(title)
        print("== TITLE startup producer measurement ==")
        print(f"  identity: sha1 {title.sha1()} ({len(title.data)} bytes)")
        print(
            f"  _drawSprt: 0x{measured['draw_sprite']:08X}; packet=0x{measured['packet']:08X}; "
            f"scanned={measured['scanned']}"
        )
        print(
            f"  publisher/developer: 0x{measured['publisher_owner']:08X}; calls="
            + ",".join(f"0x{va:08X}" for va in measured["publisher_calls"])
            + f"; scanned={measured['publisher_scanned']}"
        )
        with open(SOURCE, encoding="utf-8") as source:
            source_text = source.read()
        if args.check_source:
            check_source(measured, source_text)
        if args.selftest:
            selftest(title, measured, source_text)
    except (OSError, Refuse, AssertionError) as error:
        print(f"[re-title-startup] REFUSED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

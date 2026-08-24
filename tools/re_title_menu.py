#!/usr/bin/env python3
"""Measure TITLE's completed menu-pass producer from the retail overlay.

The title menu submits immediate DrawPrim packets in two display-buffer passes. This instrument
locates the two-pass owner by its complete draw/sync/VSync shape, derives the menu-item callee from
that owner, verifies the callee itself reaches DrawPrim, and gates the retained-super shipping owner.
No decomp symbol or menu address is an input to the measurement.
"""

import argparse
import re
import struct
import sys

from re_crt0 import Refuse
from re_frame import DEFAULT_TITLE, TITLE_BASE, TITLE_SHA1, Overlay, jal_word
from re_spu_transfer import unique_shape

DRAW_SYNC = 0x80028650
DRAW_PRIM = 0x80028BE8
VSYNC = 0x8001F6C4
SOURCE = "game/render/title_menu.cpp"


def jal_target(pc, word):
    if word >> 26 != 3:
        raise Refuse(f"expected jal at 0x{pc:08X}, found 0x{word:08X}")
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def measure(title, verify_identity=True):
    if verify_identity:
        title.check_identity()

    # This owner builds two background SPRTs, calls the same menu-item callee once per pass, and puts
    # DrawSync/VSync only between the passes. The loop bound and two packet constants make the shape
    # unique among TITLE's immediate-primitive helpers.
    owner, scanned = unique_shape(
        title,
        "TITLE two-pass menu owner",
        {
            0x00: 0x27BDFFD0,
            0x24: 0x00008821,
            0x34: 0x3C136480,
            0x38: 0x36738080,
            0x3C: 0x3C120040,
            0x40: 0x365200A0,
            0x48: 0x3C02E100,
            0x4C: 0x34420113,
            0x74: jal_word(DRAW_PRIM),
            0x80: 0x3C02E100,
            0x84: 0x34420115,
            0xAC: jal_word(DRAW_PRIM),
            0xC4: jal_word(DRAW_SYNC),
            0xCC: jal_word(VSYNC),
            0xEC: 0x2A220002,
            0xF0: 0x1440FFD5,
            0x114: 0x03E00008,
            0x118: 0x27BD0030,
        },
    )

    call = owner + 0xB4
    menu_items = jal_target(call, title.r32(call))
    if title.r32(menu_items) != 0x27BDFFB8 or title.r32(menu_items + 0x14) != 0x24160009:
        raise Refuse(
            f"two-pass owner callee 0x{menu_items:08X} lacks the menu-item prologue/ten-item bound"
        )
    if title.r32(menu_items + 0x12C) != jal_word(DRAW_PRIM):
        raise Refuse(f"menu-item callee 0x{menu_items:08X} does not submit its first completed SPRT")

    calls = [
        va
        for va in range(owner, owner + 0x11C, 4)
        if title.r32(va) == jal_word(menu_items)
    ]
    if calls != [call]:
        shown = ", ".join(f"0x{va:08X}" for va in calls) or "none"
        raise Refuse(
            f"two-pass owner: searched 0x11C bytes, found {len(calls)} menu-item calls "
            f"({shown}); expected exactly 0x{call:08X}"
        )

    return {"owner": owner, "menu_items": menu_items, "call": call, "scanned": scanned}


def check_source(measured, text):
    match = re.search(r"\bkTitleMenuItemsComplete\s*=\s*(0x[0-9A-Fa-f]+)u?", text)
    if not match:
        raise Refuse(f"{SOURCE}: kTitleMenuItemsComplete is absent")
    shipped = int(match.group(1), 0)
    if shipped != measured["menu_items"]:
        raise Refuse(
            f"{SOURCE}: kTitleMenuItemsComplete=0x{shipped:08X}, "
            f"measured 0x{measured['menu_items']:08X}"
        )
    generated = f"ov_title_gen_{measured['menu_items']:08X}"
    if text.count(generated) < 2:
        raise Refuse(f"{SOURCE}: measured generated super body {generated} is not retained and installed")
    print(f"  [ ok ] shipping completion/super: 0x{shipped:08X} / {generated}")


def selftest(title, measured, source_text):
    print("== re_title_menu selftest ==")
    checks = 0
    original = title.data

    mutable = bytearray(original)
    offset = title.off(measured["owner"] + 0x74)
    mutable[offset : offset + 4] = struct.pack("<I", 0)
    title.data = bytes(mutable)
    try:
        measure(title, verify_identity=False)
        raise AssertionError("destroyed menu DrawPrim was accepted")
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"DrawPrim negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed menu DrawPrim refused: {error}")
        checks += 1
    finally:
        title.data = original

    shifted = source_text.replace(
        f"0x{measured['menu_items']:08X}u", f"0x{measured['menu_items'] + 4:08X}u", 1
    )
    try:
        check_source(measured, shifted)
        raise AssertionError("shifted shipping completion was accepted")
    except Refuse as error:
        print(f"  [ ok ] shifted shipping completion refused: {error}")
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

    print(f"== re_title_menu selftest PASS ({checks}/3) ==")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("title", nargs="?", default=DEFAULT_TITLE)
    parser.add_argument("--check-source", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    try:
        title = Overlay(args.title, TITLE_BASE, TITLE_SHA1)
        measured = measure(title)
        print("== TITLE menu producer measurement ==")
        print(f"  identity: sha1 {title.sha1()} ({len(title.data)} bytes)")
        print(
            f"  two-pass owner=0x{measured['owner']:08X}; completed-items="
            f"0x{measured['menu_items']:08X}; call=0x{measured['call']:08X}; "
            f"scanned={measured['scanned']}"
        )
        with open(SOURCE, encoding="utf-8") as source:
            source_text = source.read()
        if args.check_source:
            check_source(measured, source_text)
        if args.selftest:
            selftest(title, measured, source_text)
    except (OSError, Refuse, AssertionError) as error:
        print(f"[re-title-menu] REFUSED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

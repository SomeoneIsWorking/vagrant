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
from re_spu_transfer import based_address, jal_target, unique_shape

DRAW_SYNC = 0x80028650
DRAW_PRIM = 0x80028BE8
SOURCE = "game/render/title_startup.cpp"
SPLASH_FACTS = "game/render/title_splash_facts.h"


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

    title_entry, title_entry_scanned = unique_shape(
        title,
        "TITLE entry",
        {
            0x00: 0x3C038006,
            0x08: 0x27BDFFC0,
            0x48: jal_word(0x80071B14),
            0x50: jal_word(0x80071254),
            0xB0: jal_word(0x8006FE30),
        },
    )
    init_environment = jal_target(title_entry + 0x50, title.r32(title_entry + 0x50))
    if jal_target(init_environment + 0x70, title.r32(init_environment + 0x70)) != publisher_owner:
        raise Refuse("TITLE environment no longer owns the measured publisher/developer splash")

    settings = materialized_address(title, init_environment + 0x08, init_environment + 0x10, 16, 17)
    title_screen_count = based_address(
        title.r32(init_environment + 0x4C), title.r32(init_environment + 0x5C), 3
    )
    inventory = materialized_address(title, init_environment + 0x9C, init_environment + 0xA0, 4, 4)
    state_flags = materialized_address(title, init_environment + 0xB0, init_environment + 0xB4, 2, 2)
    intro_playing = based_address(title.r32(title_entry + 0x60), title.r32(title_entry + 0x64), 3)
    menu_states = materialized_address(title, title_entry + 0x7C, title_entry + 0x80, 6, 6)
    publisher_data = materialized_address(title, publisher_owner + 0x4C, publisher_owner + 0x50, 16, 16)
    developer_data = materialized_address(title, publisher_owner + 0x1B0, publisher_owner + 0x1B4, 5, 5)
    buttons_hi = title.r32(publisher_owner + 0x1F0)
    buttons_read = title.r32(publisher_owner + 0x200)
    if (
        buttons_hi >> 26 != 0x0F
        or (buttons_hi >> 16) & 31 != 2
        or buttons_read >> 26 != 0x25
        or (buttons_read >> 21) & 31 != 2
    ):
        raise Refuse("TITLE developer splash no longer reads the button state through r2")
    buttons_state = (((buttons_hi & 0xFFFF) << 16) + s16(buttons_read & 0xFFFF)) & 0xFFFFFFFF

    splash_calls = {
        "clear_image": jal_target(publisher_owner + 0x3C, title.r32(publisher_owner + 0x3C)),
        "draw_image": jal_target(publisher_owner + 0x5C, title.r32(publisher_owner + 0x5C)),
        "set_def_disp": jal_target(publisher_owner + 0x8C, title.r32(publisher_owner + 0x8C)),
        "set_def_draw": jal_target(publisher_owner + 0xA8, title.r32(publisher_owner + 0xA8)),
        "put_disp": jal_target(publisher_owner + 0xC0, title.r32(publisher_owner + 0xC0)),
        "put_draw": jal_target(publisher_owner + 0xC8, title.r32(publisher_owner + 0xC8)),
        "draw_sync": jal_target(publisher_owner + 0xD0, title.r32(publisher_owner + 0xD0)),
        "set_disp_mask": jal_target(publisher_owner + 0xE0, title.r32(publisher_owner + 0xE0)),
        "process_pad": jal_target(publisher_owner + 0x288, title.r32(publisher_owner + 0x288)),
    }

    return {
        "draw_sprite": draw_sprite,
        "packet": packet,
        "publisher_owner": publisher_owner,
        "publisher_calls": calls,
        "title_entry": title_entry,
        "init_game_data": jal_target(title_entry + 0x48, title.r32(title_entry + 0x48)),
        "game_save_screen": jal_target(title_entry + 0x40, title.r32(title_entry + 0x40)),
        "memset": jal_target(init_environment + 0x34, title.r32(init_environment + 0x34)),
        "set_mono": jal_target(init_environment + 0x8C, title.r32(init_environment + 0x8C)),
        "set_cd_volume": jal_target(init_environment + 0x94, title.r32(init_environment + 0x94)),
        "save_file_exists": jal_target(title_entry + 0x6C, title.r32(title_entry + 0x6C)),
        "copy_title_bg": jal_target(title_entry + 0x98, title.r32(title_entry + 0x98)),
        "settings": settings,
        "title_screen_count": title_screen_count,
        "inventory": inventory,
        "state_flags": state_flags,
        "intro_playing": intro_playing,
        "menu_states": menu_states,
        "publisher_data": publisher_data,
        "developer_data": developer_data,
        "buttons_state": buttons_state,
        "splash_calls": splash_calls,
        "scanned": scanned,
        "publisher_scanned": publisher_scanned,
        "title_entry_scanned": title_entry_scanned,
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
    print(f"  [ ok ] native producer address: 0x{shipped:08X}")

    with open(SPLASH_FACTS, encoding="utf-8") as source:
        facts = source.read()
    expected = {
        "kInitGameData": measured["init_game_data"],
        "kGameSaveScreen": measured["game_save_screen"],
        "kMemset": measured["memset"],
        "kDrawImage": measured["splash_calls"]["draw_image"],
        "kDrawSprite": measured["draw_sprite"],
        "kClearImage": measured["splash_calls"]["clear_image"],
        "kSetDefDispEnv": measured["splash_calls"]["set_def_disp"],
        "kSetDefDrawEnv": measured["splash_calls"]["set_def_draw"],
        "kPutDispEnv": measured["splash_calls"]["put_disp"],
        "kPutDrawEnv": measured["splash_calls"]["put_draw"],
        "kDrawSync": measured["splash_calls"]["draw_sync"],
        "kSetDispMask": measured["splash_calls"]["set_disp_mask"],
        "kProcessPadState": measured["splash_calls"]["process_pad"],
        "kSetMonoSound": measured["set_mono"],
        "kSetCdVolume": measured["set_cd_volume"],
        "kCopyTitleBgData": measured["copy_title_bg"],
        "kSettings": measured["settings"],
        "kTitleScreenCount": measured["title_screen_count"],
        "kInventoryIndices": measured["inventory"],
        "kStateFlags": measured["state_flags"],
        "kIntroMoviePlaying": measured["intro_playing"],
        "kMenuItemStates": measured["menu_states"],
        "kButtonsState": measured["buttons_state"],
        "kPublisherData": measured["publisher_data"],
        "kDeveloperData": measured["developer_data"],
    }
    failures = []
    for name, want in expected.items():
        match = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+)u?", facts)
        if not match or int(match.group(1), 0) != want:
            failures.append(name)
    if failures:
        raise Refuse(f"{SPLASH_FACTS}: measured fact mismatch: " + ", ".join(failures))
    print(f"  [ ok ] native splash facts: {len(expected)}/{len(expected)} measured constants")


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
        print(
            f"  TITLE entry 0x{measured['title_entry']:08X}; settings=0x{measured['settings']:08X}; "
            f"publisher/developer data=0x{measured['publisher_data']:08X}/0x{measured['developer_data']:08X}"
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

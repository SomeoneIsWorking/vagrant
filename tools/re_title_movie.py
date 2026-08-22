#!/usr/bin/env python3
"""Measure TITLE's guest-decoded RGB24 movie producer and scanout boundary.

This instrument derives the MovieData initializer, MDEC-out completion callback, and intro display
owner directly from the SHA-bound retail TITLE.PRG. The guest owns STR/VLC/MDEC decode and uploads
each decoded slice to VRAM; the game-side native producer only observes the measured frame-complete
field and asks the shared renderer to scan out that live VRAM. No decomp symbols, movie bytes, or
decoded reference frames are inputs to the measurement.
"""

import argparse
import re
import struct
import sys

from re_crt0 import Refuse, s16
from re_frame import DEFAULT_TITLE, TITLE_BASE, TITLE_SHA1, Overlay, jal_word
from re_spu_transfer import unique_shape

LOAD_IMAGE = 0x800288FC
SET_DEF_DISP_ENV = 0x8002B434
PUT_DISP_ENV = 0x80028E80
SOURCE = "game/render/title_movie.cpp"


def jal_target(word, pc):
    if word >> 26 != 3:
        raise Refuse(f"expected jal at 0x{pc:08X}")
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def materialized_addiu(overlay, hi_va, lo_va, hi_reg, dst_reg):
    hi = overlay.r32(hi_va)
    lo = overlay.r32(lo_va)
    if hi >> 26 != 0x0F or (hi >> 16) & 31 != hi_reg:
        raise Refuse(f"expected lui ${hi_reg} at 0x{hi_va:08X}")
    if lo >> 26 != 0x09 or (lo >> 21) & 31 != hi_reg or (lo >> 16) & 31 != dst_reg:
        raise Refuse(f"expected addiu ${dst_reg},${hi_reg} at 0x{lo_va:08X}")
    return (((hi & 0xFFFF) << 16) + s16(lo & 0xFFFF)) & 0xFFFFFFFF


def measure(title, verify_identity=True):
    if verify_identity:
        title.check_identity()

    # This leaf initializes the MovieData ABI used by both the decode owner and callback. It fixes
    # the MDEC output slice at 24 VRAM halfwords (16 RGB24 pixels) and clears frameComplete at +0x34.
    movie_init, init_scanned = unique_shape(
        title,
        "TITLE MovieData initializer",
        {
            0x00: 0x3C02800F,
            0x08: 0xA4850018,
            0x0C: 0xA485002C,
            0x20: 0xAC800008,
            0x24: 0xAC800014,
            0x28: 0xA4870020,
            0x2C: 0xAC800028,
            0x44: 0x24020018,
            0x48: 0xA4820030,
            0x4C: 0xAC800034,
            0x60: 0x03E00008,
        },
    )

    # The callback copies the current RECT, advances by one 24-halfword slice, starts another MDEC
    # output DMA when the row is incomplete, and otherwise writes frameComplete=1 before LoadImage.
    dct_callback, callback_scanned = unique_shape(
        title,
        "TITLE MDEC-out slice callback",
        {
            0x00: 0x27BDFFE0,
            0x28: 0x3C02800E,
            0x2C: 0x2446EDA8,
            0x50: 0x8CD00014,
            0x54: 0x94C3002C,
            0x58: 0x94C50030,
            0x5C: 0x8CC70028,
            0x90: 0x0064182A,
            0xD0: 0x24020001,
            0xD4: 0xACC20034,
            0x100: 0x3C03800E,
            0x104: 0x2463EDA8,
            0x114: jal_word(LOAD_IMAGE),
            0x118: 0x27A40010,
            0x124: 0x03E00008,
        },
    )
    movie_data = materialized_addiu(title, dct_callback + 0x28, dct_callback + 0x2C, 2, 6)
    if materialized_addiu(title, dct_callback + 0x100, dct_callback + 0x104, 3, 3) != movie_data:
        raise Refuse("TITLE callback does not upload from the MovieData object it advances")
    frame_complete = movie_data + 0x34

    dec_dct_out = jal_target(title.r32(dct_callback + 0xC0), dct_callback + 0xC0)
    dec_dct_out_body = jal_target(title.r32(dec_dct_out + 0x08), dec_dct_out + 0x08)
    title.off(dec_dct_out_body)
    if [title.r32(dec_dct_out + offset) for offset in range(0, 0x20, 4)] != [
        0x27BDFFE8,
        0xAFBF0010,
        jal_word(dec_dct_out_body),
        0x00000000,
        0x8FBF0010,
        0x27BD0018,
        0x03E00008,
        0x00000000,
    ]:
        raise Refuse("TITLE callback's output-DMA target is not the measured DecDCTout leaf shape")

    # The playback owner independently materializes the same MovieData object, waits for the frame,
    # builds a 480-halfword x 224-line display environment, sets isrgb24=1, and publishes it.
    play_owner, play_scanned = unique_shape(
        title,
        "TITLE RGB24 intro display owner",
        {
            0x00: 0x27BDFFA8,
            0x10: 0x3C14800E,
            0x18: 0x2691EDA8,
            0x13C: 0x240701E0,
            0x140: jal_word(SET_DEF_DISP_ENV),
            0x144: 0xAFB00010,
            0x164: 0xA7B0002E,
            0x168: 0x24020008,
            0x16C: 0xA7A2002A,
            0x170: 0x24020001,
            0x178: 0xA3A20031,
            0x184: jal_word(PUT_DISP_ENV),
            0x1B8: 0x8FBF0054,
        },
    )
    if materialized_addiu(title, play_owner + 0x10, play_owner + 0x18, 20, 17) != movie_data:
        raise Refuse("TITLE display owner does not use the callback's MovieData object")
    if jal_target(title.r32(play_owner + 0x50), play_owner + 0x50) == dec_dct_out:
        raise Refuse("TITLE display owner unexpectedly calls DecDCTout in its DecDCTin slot")
    if jal_target(title.r32(play_owner + 0x88), play_owner + 0x88) != dec_dct_out:
        raise Refuse("TITLE display owner does not start the measured DecDCTout leaf")

    return {
        "movie_init": movie_init,
        "dct_callback": dct_callback,
        "movie_data": movie_data,
        "frame_complete": frame_complete,
        "dec_dct_out": dec_dct_out,
        "play_owner": play_owner,
        "slice_halfwords": 24,
        "display_halfwords": 480,
        "display_height": 224,
        "init_scanned": init_scanned,
        "callback_scanned": callback_scanned,
        "play_scanned": play_scanned,
    }


def source_constant(text, name):
    match = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+)u?", text)
    if not match:
        raise Refuse(f"{SOURCE}: {name} is absent")
    return int(match.group(1), 0)


def check_source(measured, text):
    callback = source_constant(text, "kTitleMovieDctOutCallback")
    complete = source_constant(text, "kMovieFrameComplete")
    if callback != measured["dct_callback"]:
        raise Refuse(f"{SOURCE}: callback=0x{callback:08X}, measured 0x{measured['dct_callback']:08X}")
    if complete != measured["frame_complete"]:
        raise Refuse(f"{SOURCE}: frameComplete=0x{complete:08X}, measured 0x{measured['frame_complete']:08X}")
    generated = f"ov_title_gen_{callback:08X}"
    if text.count(generated) < 2:
        raise Refuse(f"{SOURCE}: measured generated super body {generated} is not retained and installed")
    print(f"  [ ok ] shipping callback/frameComplete/super: 0x{callback:08X} / 0x{complete:08X} / {generated}")


def selftest(title, measured, source_text):
    print("== re_title_movie selftest ==")
    checks = 0
    original = title.data

    mutable = bytearray(original)
    offset = title.off(measured["dct_callback"] + 0x114)
    mutable[offset : offset + 4] = struct.pack("<I", 0)
    title.data = bytes(mutable)
    try:
        measure(title, verify_identity=False)
        raise AssertionError("callback with destroyed LoadImage was accepted")
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"destroyed LoadImage negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed LoadImage refused: {error}")
        checks += 1
    finally:
        title.data = original

    shifted = source_text.replace(
        f"0x{measured['frame_complete']:08X}u", f"0x{measured['frame_complete'] + 4:08X}u", 1
    )
    try:
        check_source(measured, shifted)
        raise AssertionError("shifted frameComplete address was accepted")
    except Refuse as error:
        print(f"  [ ok ] shifted shipping frameComplete refused: {error}")
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

    print(f"== re_title_movie selftest PASS ({checks}/3) ==")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("title", nargs="?", default=DEFAULT_TITLE)
    parser.add_argument("--check-source", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    try:
        title = Overlay(args.title, TITLE_BASE, TITLE_SHA1)
        measured = measure(title)
        print("== TITLE RGB24 movie producer measurement ==")
        print(f"  identity: sha1 {title.sha1()} ({len(title.data)} bytes)")
        print(
            f"  MovieData init=0x{measured['movie_init']:08X}; data=0x{measured['movie_data']:08X}; "
            f"frameComplete=0x{measured['frame_complete']:08X}; slice={measured['slice_halfwords']} halfwords"
        )
        print(
            f"  MDEC callback=0x{measured['dct_callback']:08X}; DecDCTout=0x{measured['dec_dct_out']:08X}; "
            f"display owner=0x{measured['play_owner']:08X}; "
            f"RGB24={measured['display_halfwords']} halfwords x {measured['display_height']} lines"
        )
        print(
            f"  denominators: init={measured['init_scanned']}, callback={measured['callback_scanned']}, "
            f"display={measured['play_scanned']} candidate starts"
        )
        with open(SOURCE, encoding="utf-8") as source:
            source_text = source.read()
        if args.check_source:
            check_source(measured, source_text)
        if args.selftest:
            selftest(title, measured, source_text)
    except (OSError, Refuse, AssertionError) as error:
        print(f"[re-title-movie] REFUSED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

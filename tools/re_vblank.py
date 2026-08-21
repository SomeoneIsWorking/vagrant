#!/usr/bin/env python3
"""Measure Vagrant's resident VBlank/VSync delivery route from the owned PS-EXE.

Sony libetc waits on a counter incremented by the guest's installed VBlank handler. This tool derives
VSync, its wait helper, startIntrVSync, the handler, callback table, registrar, callback-system
wrapper, and public wrapper without taking any address as a search input. It then gates the
game-owned host-turn seam that dispatches the intact handler at the framework's
video-standard-derived field rate.
"""

import os
import re
import struct
import sys

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse
from re_spu_transfer import (
    based_address,
    jal_target,
    materialized_address,
    unique_shape,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "game", "sync", "vblank.cpp")


def measure(img, verify_identity=True):
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(
            f"{img.path}: sha1 {img.sha1()} != SLUS_010.40 {FIXTURE_SHA1}; nothing was measured"
        )

    vsync, vsync_scanned = unique_shape(
        img,
        "Sony libetc VSync",
        {
            0x00: 0x3C028003,
            0x04: 0x8C420FDC,
            0x08: 0x3C058003,
            0x0C: 0x8CA50FE0,
            0x10: 0x27BDFFD8,
            0xB0: 0x0C007E0F,
            0xD4: 0x0C007E0F,
            0x170: 0x03E00008,
        },
    )
    wait_helper = jal_target(vsync + 0xB0, img.r32(vsync + 0xB0))
    if jal_target(vsync + 0xD4, img.r32(vsync + 0xD4)) != wait_helper:
        raise Refuse("VSync's two blocking paths do not call one wait helper")
    counter = based_address(img.r32(vsync + 0x60), img.r32(vsync + 0x64), 2)
    for hi_off, mem_off, reg in ((0xC8, 0xCC, 4), (0x124, 0x128, 2)):
        if (
            based_address(img.r32(vsync + hi_off), img.r32(vsync + mem_off), reg)
            != counter
        ):
            raise Refuse(
                "VSync's query, wait target, and completion paths do not share one counter"
            )

    helper, helper_scanned = unique_shape(
        img,
        "VSync counter wait helper",
        {
            0x00: 0x27BDFFE0,
            0x04: 0x00052BC0,
            0x0C: 0x3C028003,
            0x18: 0x0044102A,
            0x1C: 0x1040001A,
            0x70: 0x3C028003,
            0x7C: 0x0044102A,
            0x90: 0x03E00008,
        },
    )
    if helper != wait_helper:
        raise Refuse(
            f"VSync calls 0x{wait_helper:08X}, not unique counter wait helper 0x{helper:08X}"
        )
    for hi_off, mem_off in ((0x0C, 0x10), (0x70, 0x74)):
        if (
            based_address(img.r32(helper + hi_off), img.r32(helper + mem_off), 2)
            != counter
        ):
            raise Refuse(
                "VSync wait helper does not poll the counter returned by VSync"
            )

    start, start_scanned = unique_shape(
        img,
        "startIntrVSync",
        {
            0x00: 0x27BDFFE8,
            0x04: 0x3C048003,
            0x0C: 0x3C038003,
            0x1C: 0xAC620000,
            0x20: 0x3C018003,
            0x28: 0x0C008021,
            0x30: 0x3C058002,
            0x38: 0x0C007E41,
            0x40: 0x3C028002,
            0x50: 0x03E00008,
        },
    )
    callback_table = materialized_address(
        img.r32(start + 0x04), img.r32(start + 0x08), 4
    )
    start_counter = based_address(img.r32(start + 0x20), img.r32(start + 0x24), 1)
    handler = materialized_address(img.r32(start + 0x30), img.r32(start + 0x34), 5)
    registrar = materialized_address(img.r32(start + 0x40), img.r32(start + 0x44), 2)
    callback_register = jal_target(start + 0x38, img.r32(start + 0x38))
    if start_counter != counter:
        raise Refuse("startIntrVSync does not clear the counter polled by VSync")

    handler_match, handler_scanned = unique_shape(
        img,
        "resident VBlank handler",
        {
            0x00: 0x3C028003,
            0x08: 0x27BDFFE0,
            0x0C: 0xAFB10014,
            0x10: 0x00008821,
            0x18: 0x3C108003,
            0x24: 0x24420001,
            0x28: 0x3C018003,
            0x30: 0x8E020000,
            0x40: 0x0040F809,
            0x4C: 0x2A220008,
            0x64: 0x03E00008,
        },
    )
    if handler_match != handler:
        raise Refuse(
            f"startIntrVSync installs 0x{handler:08X}, not unique VBlank handler "
            f"0x{handler_match:08X}"
        )
    handler_counter = based_address(img.r32(handler), img.r32(handler + 0x04), 2)
    stored_counter = based_address(img.r32(handler + 0x28), img.r32(handler + 0x2C), 1)
    handler_table = materialized_address(
        img.r32(handler + 0x18), img.r32(handler + 0x1C), 16
    )
    if handler_counter != counter or stored_counter != counter:
        raise Refuse(
            "resident VBlank handler does not read, increment, and write the VSync counter"
        )
    if handler_table != callback_table:
        raise Refuse(
            "resident VBlank handler does not dispatch startIntrVSync's callback table"
        )

    registrar_table = materialized_address(
        img.r32(registrar), img.r32(registrar + 0x04), 2
    )
    if registrar_table != callback_table or img.r32(registrar + 0x08) != 0x00042080:
        raise Refuse(
            "startIntrVSync's returned registrar does not index its callback table by selector*4"
        )

    wrapper, wrapper_scanned = unique_shape(
        img,
        "public VSyncCallback wrapper",
        {
            0x00: 0x27BDFFE8,
            0x04: 0x3C028003,
            0x0C: 0x00802821,
            0x10: 0xAFBF0010,
            0x14: 0x8C420014,
            0x1C: 0x0040F809,
            0x20: 0x24040004,
            0x2C: 0x03E00008,
        },
    )
    callback_vector = based_address(img.r32(wrapper + 0x04), img.r32(wrapper + 0x08), 2)
    callback_register_vector = based_address(
        img.r32(callback_register), img.r32(callback_register + 0x04), 2
    )
    if (
        callback_register_vector != callback_vector
        or img.r32(callback_register + 0x10) != 0x8C420008
        or img.r32(callback_register + 0x18) != 0x0040F809
    ):
        raise Refuse(
            "startIntrVSync's callback-system wrapper does not call vector +8 from "
            "VSyncCallback's vector"
        )

    bootstraps = []
    for va in range(img.lo, img.hi - 0x18, 4):
        word = img.r32(va)
        if word >> 26 != 3 or jal_target(va, word) != start:
            continue
        if img.r32(va + 0x10) >> 26 != 3 or img.r32(va + 0x14) != 0xAC620014:
            continue
        try:
            vector = based_address(img.r32(va + 0x08), img.r32(va + 0x0C), 3)
        except Refuse:
            continue
        if vector == callback_vector:
            bootstraps.append(va)
    if len(bootstraps) != 1:
        shown = ", ".join(f"0x{x:08X}" for x in bootstraps) or "none"
        raise Refuse(
            f"VBlank callback bootstrap: scanned {img.t_size // 4} word-aligned candidates, "
            f"matched {len(bootstraps)} ({shown})"
        )

    return {
        "vsync": vsync,
        "wait_helper": wait_helper,
        "counter": counter,
        "start": start,
        "handler": handler,
        "callback_table": callback_table,
        "registrar": registrar,
        "callback_register": callback_register,
        "wrapper": wrapper,
        "callback_vector": callback_vector,
        "bootstrap": bootstraps[0],
        "vsync_scanned": vsync_scanned,
        "helper_scanned": helper_scanned,
        "start_scanned": start_scanned,
        "handler_scanned": handler_scanned,
        "wrapper_scanned": wrapper_scanned,
    }


def source_constant(text, name):
    match = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+)", text)
    if not match:
        raise Refuse(f"{SOURCE}: did not find {name}")
    return int(match.group(1), 0)


def check_source(measured, text):
    expected = {
        "kStartIntrVSync": measured["start"],
        "kVBlankHandler": measured["handler"],
        "kVBlankCounter": measured["counter"],
    }
    failures = []
    for name, value in expected.items():
        shipped = source_constant(text, name)
        ok = shipped == value
        print(
            f"  [{'ok' if ok else 'FAIL':>4}] {name} shipped=0x{shipped:08X} measured=0x{value:08X}"
        )
        if not ok:
            failures.append(name)

    wiring = {
        "guest handler dispatch": r"rec_dispatch\s*\(\s*c\s*,\s*kVBlankHandler\s*\)",
        "guest startIntrVSync super-call": r"gen_func_8001FF94\s*\(\s*c\s*\)",
        "measured arming override": r"overrides::install\s*\(\s*kStartIntrVSync\b",
        "video-standard field rate": (
            r"rec_host_turn_register\s*\(\s*c\s*,\s*vagrant_vblank_turn\s*,\s*"
            r"gpu_field_rate_millihz\s*\(\s*c\s*\)\s*\)"
        ),
    }
    for name, pattern in wiring.items():
        ok = re.search(pattern, text, re.DOTALL) is not None
        print(f"  [{'ok' if ok else 'FAIL':>4}] {name}")
        if not ok:
            failures.append(name)
    if failures:
        raise Refuse("shipping mismatch: " + ", ".join(failures))


def selftest(img, measured):
    print("== re_vblank selftest ==")
    checks = 0
    with open(SOURCE, encoding="utf-8") as source_file:
        text = source_file.read()
    check_source(measured, text)
    checks += 1

    original = img.data
    mutable = bytearray(original)
    off = img.off(measured["handler"] + 0x24)
    mutable[off : off + 4] = struct.pack("<I", 0)
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError(
            "VBlank handler with destroyed counter increment was accepted"
        )
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed counter increment refused: {error}")
        checks += 1
    finally:
        img.data = original

    old = f"kVBlankHandler = 0x{measured['handler']:08X}"
    changed = text.replace(old, f"kVBlankHandler = 0x{measured['handler'] + 4:08X}", 1)
    if changed == text:
        raise AssertionError("shipping mutation anchor did not fire")
    try:
        check_source(measured, changed)
        raise AssertionError("+4 shipping handler was accepted")
    except Refuse as error:
        if "kVBlankHandler" not in str(error):
            raise AssertionError(f"shipping negative did not name field: {error}")
        print(f"  [ ok ] +4 shipping handler refused: {error}")
        checks += 1
    print(f"re_vblank selftest: {checks}/3 PASS")


def main(argv):
    args = list(argv)
    do_check = "--check-source" in args
    do_selftest = "--selftest" in args
    args = [arg for arg in args if arg not in ("--check-source", "--selftest")]
    if len(args) > 1:
        print(
            "usage: re_vblank.py [--check-source] [--selftest] [SLUS_010.40]",
            file=sys.stderr,
        )
        return 2
    try:
        img = Image(args[0] if args else DEFAULT_EXE)
        measured = measure(img)
        print("== Vagrant resident VBlank/VSync delivery route ==")
        print(
            f"  VSync 0x{measured['vsync']:08X} -> wait helper 0x{measured['wait_helper']:08X} "
            f"-> counter 0x{measured['counter']:08X}"
        )
        print(
            f"  startIntrVSync 0x{measured['start']:08X} installs handler "
            f"0x{measured['handler']:08X} and returns registrar 0x{measured['registrar']:08X}"
        )
        print(
            f"  handler increments the counter and dispatches 8 callbacks from "
            f"0x{measured['callback_table']:08X}"
        )
        print(
            f"  callback register wrapper 0x{measured['callback_register']:08X}; public "
            f"VSyncCallback 0x{measured['wrapper']:08X}; bootstrap 0x{measured['bootstrap']:08X}"
        )
        print(
            "  boundary: the host supplies display-field timing; the intact guest handler owns "
            "counter and callback semantics"
        )
        if do_check:
            with open(SOURCE, encoding="utf-8") as source_file:
                check_source(measured, source_file.read())
        if do_selftest:
            selftest(img, measured)
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_vblank REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Measure retail VBlank/VSync, then gate Vagrant's native-field ownership.

Sony libetc waits on a counter incremented by the guest's installed VBlank handler. This tool derives
VSync, its wait helper, startIntrVSync, the handler, callback table, registrar, callback-system
wrapper, and public wrapper without taking any address as a search input. The retail route remains
evidence, but the shipping gate requires VagrantFrameDriver to own the field and guest VSync to be a
fatal PlatformHle binding; the guest handler and its host-turn injection are forbidden.
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
FACTS = os.path.join(ROOT, "game", "sync", "vsync_facts.h")
FRAME = os.path.join(ROOT, "game", "sync", "frame_loop.cpp")


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

    bootstrap = bootstraps[0]
    owner = bootstrap - 0x94
    setjmp_call = bootstrap - 0x34
    hook_entry_call = bootstrap - 0x0C
    if (
        img.r32(owner) != 0x27BDFFE8
        or img.r32(owner + 0x08) >> 26 != 0x0F
        or img.r32(owner + 0x0C) >> 26 != 0x09
        or img.r32(setjmp_call) >> 26 != 0x03
        or img.r32(setjmp_call + 0x04) != 0x26040038
        or img.r32(hook_entry_call) >> 26 != 0x03
        or img.r32(hook_entry_call + 0x04) != 0xAE020000
    ):
        raise Refuse(
            "VBlank callback bootstrap does not contain the measured setjmp/HookEntryInt route"
        )
    owner_base = materialized_address(img.r32(owner + 0x08), img.r32(owner + 0x0C), 16)
    jmp_buffer = owner_base + (img.r32(setjmp_call + 0x04) & 0xFFFF)
    reentry = setjmp_call + 0x08
    if img.r32(reentry) != 0x10400003:
        raise Refuse(
            "setjmp return PC is not the branch that distinguishes initial and restored entry"
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
        "bootstrap": bootstrap,
        "bootstrap_owner": owner,
        "setjmp": jal_target(setjmp_call, img.r32(setjmp_call)),
        "jmp_buffer": jmp_buffer,
        "reentry": reentry,
        "hook_entry_int": jal_target(hook_entry_call, img.r32(hook_entry_call)),
        "vsync_scanned": vsync_scanned,
        "helper_scanned": helper_scanned,
        "start_scanned": start_scanned,
        "handler_scanned": handler_scanned,
        "wrapper_scanned": wrapper_scanned,
    }


def source_constant(path, text, name):
    match = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+)", text)
    if not match:
        raise Refuse(f"{path}: did not find {name}")
    return int(match.group(1), 0)


def read_shipping_sources():
    return {
        path: open(path, encoding="utf-8").read()
        for path in (FACTS, FRAME)
    }


def check_source(measured, sources):
    facts = sources[FACTS]
    frame = sources[FRAME]
    failures = []
    shipped = source_constant(FACTS, facts, "kVSync")
    ok = shipped == measured["vsync"]
    print(
        f"  [{'ok' if ok else 'FAIL':>4}] kVSync shipped=0x{shipped:08X} measured=0x{measured['vsync']:08X}"
    )
    if not ok:
        failures.append("kVSync")

    wiring = {
        "input field service": r"\.input\s*=\s*serviceInput\b",
        "audio field service": r"\.audio\s*=\s*serviceAudio\b",
        "single presentation fence": r"services_\.present\(core\)\s*;",
        "native field pacing": r"services_\.pace\(core\)\s*;",
    }
    for name, pattern in wiring.items():
        haystack = frame
        ok = re.search(pattern, haystack, re.DOTALL) is not None
        print(f"  [{'ok' if ok else 'FAIL':>4}] {name}")
        if not ok:
            failures.append(name)

    present_calls = len(re.findall(r"services_\.present\s*\(\s*core\s*\)", frame))
    one_present = present_calls == 1
    print(f"  [{'ok' if one_present else 'FAIL':>4}] exactly one driver presentation call site")
    if not one_present:
        failures.append("presentation call count")

    forbidden = {
        "guest VBlank handler dispatch": r"kVBlankHandler",
        "guest VBlank host-turn injection": r"vagrant_vblank_turn",
    }
    shipping = frame
    for name, pattern in forbidden.items():
        absent = re.search(pattern, shipping, re.DOTALL) is None
        print(f"  [{'ok' if absent else 'FAIL':>4}] no {name}")
        if not absent:
            failures.append(name)

    if failures:
        raise Refuse("shipping mismatch: " + ", ".join(failures))


def selftest(img, measured):
    print("== re_vblank selftest ==")
    checks = 0
    sources = read_shipping_sources()
    check_source(measured, sources)
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

    old = f"kVSync = 0x{measured['vsync']:08X}"
    changed = sources[FACTS].replace(old, f"kVSync = 0x{measured['vsync'] + 4:08X}", 1)
    if changed == sources[FACTS]:
        raise AssertionError("shipping mutation anchor did not fire")
    sabotaged = dict(sources)
    sabotaged[FACTS] = changed
    try:
        check_source(measured, sabotaged)
        raise AssertionError("+4 shipping VSync was accepted")
    except Refuse as error:
        if "kVSync" not in str(error):
            raise AssertionError(f"shipping negative did not name field: {error}")
        print(f"  [ ok ] +4 shipping VSync refused: {error}")
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
        print("== Vagrant retail VBlank/VSync evidence and native ownership ==")
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
            f"  interrupt bootstrap 0x{measured['bootstrap_owner']:08X}: setjmp buffer "
            f"0x{measured['jmp_buffer']:08X} restores PC 0x{measured['reentry']:08X}; "
            f"HookEntryInt 0x{measured['hook_entry_int']:08X}"
        )
        print(
            "  retail evidence only: the future dynarec adapter owns ordinary guest execution; "
            "the native frame owner must not invoke the retail handler directly"
        )
        if do_check:
            check_source(measured, read_shipping_sources())
        if do_selftest:
            selftest(img, measured)
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_vblank REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

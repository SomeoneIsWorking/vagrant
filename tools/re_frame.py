#!/usr/bin/env python3
"""Measure Vagrant Story's guest-owned frame/present boundary from retail overlays.

The title and battle overlays each own their page flip and DrawOTag submission. Battle does not use
a fixed, statically addressed OT/packet pair: it allocates two OT blocks and two packet pools from
the guest heap, then keeps only their pointers in resident arrays. That contract cannot be encoded
in psxport's legacy fixed-base GameConfig frame fields. This tool proves both facts from the owned
overlay bytes and keeps those fields zero until a compatible game-owned seam exists.
"""

import hashlib
import os
import re
import struct
import sys

from re_crt0 import Refuse, s16
from re_spu_transfer import based_address, unique_shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TITLE = os.path.join(ROOT, "scratch", "raw", "prg", "TITLE.PRG")
DEFAULT_BATTLE = os.path.join(ROOT, "scratch", "raw", "prg", "BATTLE.PRG")
DEFAULT_INITBTL = os.path.join(ROOT, "scratch", "raw", "prg", "INITBTL.PRG")
CONFIG = os.path.join(ROOT, "game", "core", "game_config.cpp")
BATTLE_SOURCE = os.path.join(ROOT, "game", "render", "battle_frame.cpp")

TITLE_SHA1 = "f74a76e6215edebf607d0c2af56481050edb139a"
BATTLE_SHA1 = "d53aaccc3b3a2fc057d05e0dcea92f7182bc72a9"
INITBTL_SHA1 = "d7ea16ef957179cad6e3b02727bb714713cfcc32"

TITLE_BASE = 0x80068800
BATTLE_BASE = 0x80068800
INITBTL_BASE = 0x800F9800

# Resident SDK/game targets. They are search discriminators, not answers: each overlay shape must
# independently materialise the frame globals and satisfy a unique complete call sequence.
DRAW_SYNC = 0x80028650
CLEAR_OTAG_R = 0x80028B3C
DRAW_OTAG = 0x80028C44
PUT_DRAW_ENV = 0x80028CB4
PUT_DISP_ENV = 0x80028E80
GAMETIME_UPDATE = 0x8004261C
ALLOC_HEAP = 0x80043EC4
SET_GEOM_SCREEN = 0x80041534
SET_GEOM_OFFSET = 0x80041540
SET_DEF_DRAW_ENV = 0x8002B374
SET_DEF_DISP_ENV = 0x8002B434


class Overlay:
    def __init__(self, path, base, expected_sha1):
        self.path = path
        self.base = base
        with open(path, "rb") as source:
            self.data = source.read()
        self.lo = base
        self.hi = base + len(self.data)
        self.t_size = len(self.data)
        self.expected_sha1 = expected_sha1

    def sha1(self):
        return hashlib.sha1(self.data).hexdigest()

    def check_identity(self):
        actual = self.sha1()
        if actual != self.expected_sha1:
            raise Refuse(
                f"{self.path}: sha1 {actual} != expected {self.expected_sha1}; nothing was measured"
            )

    def off(self, va):
        offset = va - self.base
        if offset < 0 or offset + 4 > len(self.data):
            raise Refuse(f"0x{va:08X} lies outside {self.path}")
        return offset

    def r32(self, va):
        return struct.unpack_from("<I", self.data, self.off(va))[0]


def jal_word(target):
    return 0x0C000000 | ((target >> 2) & 0x03FFFFFF)


def address_from_lui_memory(img, lui_va, memory_va, reg):
    return based_address(img.r32(lui_va), img.r32(memory_va), reg)


def measure(title, battle, initbtl, verify_identity=True):
    if verify_identity:
        title.check_identity()
        battle.check_identity()
        initbtl.check_identity()

    # TITLE's sole DrawOTag owner toggles the resident parity word, waits for GPU and guest VBlank,
    # installs the indexed display/draw environments, then submits the caller-provided OT head.
    title_present, title_scanned = unique_shape(
        title,
        "TITLE guest frame presenter",
        {
            0x00: 0x27BDFFD8,
            0x10: 0x3C108006,
            0x14: 0x8E02E210,
            0x24: 0x2C420001,
            0x28: jal_word(DRAW_SYNC),
            0x2C: 0xAE02E210,
            0x30: jal_word(GAMETIME_UPDATE),
            0x54: jal_word(PUT_DISP_ENV),
            0x80: jal_word(PUT_DRAW_ENV),
            0x88: jal_word(DRAW_OTAG),
            0xA4: 0x03E00008,
        },
    )
    title_frame_buf = address_from_lui_memory(
        title, title_present + 0x10, title_present + 0x14, 16
    )
    if (
        address_from_lui_memory(title, title_present + 0x10, title_present + 0x2C, 16)
        != title_frame_buf
    ):
        raise Refuse("TITLE presenter does not write the parity word it reads")
    # The environment bases are materialised with addiu, not used directly as a memory operand.
    title_disp_env = (
        ((title.r32(title_present + 0x4C) & 0xFFFF) << 16)
        + s16(title.r32(title_present + 0x50) & 0xFFFF)
    ) & 0xFFFFFFFF
    title_draw_env = (
        ((title.r32(title_present + 0x78) & 0xFFFF) << 16)
        + s16(title.r32(title_present + 0x7C) & 0xFFFF)
    ) & 0xFFFFFFFF

    # BATTLE uses the same resident parity/environment globals and the same submission ordering.
    # Its additional pause/debug path is guest behaviour and remains inside this measured owner.
    battle_present, battle_scanned = unique_shape(
        battle,
        "BATTLE guest frame presenter",
        {
            0x00: 0x27BDFFC8,
            0x0C: 0x3C038006,
            0x10: 0x8C62E210,
            0x38: 0x2C420001,
            0x40: 0xAC62E210,
            0x44: 0x240400A0,
            0x48: jal_word(SET_GEOM_OFFSET),
            0x4C: 0x24050070,
            0x50: jal_word(DRAW_SYNC),
            0x60: jal_word(GAMETIME_UPDATE),
            0x164: jal_word(PUT_DISP_ENV),
            0x190: jal_word(PUT_DRAW_ENV),
            0x1A0: jal_word(DRAW_OTAG),
            0x1D8: 0x03E00008,
        },
    )
    battle_frame_buf = address_from_lui_memory(
        battle, battle_present + 0x0C, battle_present + 0x10, 3
    )
    if (
        address_from_lui_memory(battle, battle_present + 0x0C, battle_present + 0x40, 3)
        != battle_frame_buf
    ):
        raise Refuse("BATTLE presenter does not write the parity word it reads")
    if battle_frame_buf != title_frame_buf:
        raise Refuse(
            "TITLE and BATTLE presenters do not share one resident parity word"
        )

    # BATTLE establishes the 320x224 world viewport in one initializer. Its presenter then restores
    # the matching 160,112 GTE center every field, so a widescreen owner must replace this game-owned
    # projection boundary rather than globally changing the SDK calls used by 2D overlays too.
    battle_view_init, battle_view_init_scanned = unique_shape(
        battle,
        "BATTLE viewport initializer",
        {
            0x00: 0x27BDFFC0,
            0x1C: 0x24B3FFF0,
            0x58: jal_word(SET_GEOM_OFFSET),
            0x60: jal_word(SET_GEOM_SCREEN),
            0x68: 0x3C108006,
            0x6C: 0x2610E0D0,
            0x80: jal_word(SET_DEF_DRAW_ENV),
            0x84: 0xAFB30010,
            0xA0: jal_word(SET_DEF_DISP_ENV),
            0xA4: 0xAFB30010,
        },
    )

    battle_view_call, battle_view_call_scanned = unique_shape(
        battle,
        "BATTLE 320x240 viewport call",
        {
            0x00: 0x24040140,
            0x04: 0x240500F0,
            0x08: 0x3C028006,
            0x0C: 0x8C46E248,
            0x10: 0x00003821,
            0x14: 0xAFA00010,
            0x18: jal_word(battle_view_init),
            0x1C: 0xAFA00014,
        },
    )
    projection_global = address_from_lui_memory(
        battle, battle_view_call + 0x08, battle_view_call + 0x0C, 2
    )

    projection_setter, projection_setter_scanned = unique_shape(
        battle,
        "BATTLE projection-distance setter",
        {
            0x00: 0x27BDFFE8,
            0x04: 0x3C028006,
            0x08: 0xAFBF0010,
            0x0C: jal_word(SET_GEOM_SCREEN),
            0x14: 0x8FBF0010,
            0x1C: 0x03E00008,
            0x20: 0x27BD0018,
        },
    )
    setter_projection_global = address_from_lui_memory(
        battle, projection_setter + 0x04, projection_setter + 0x10, 2
    )
    if setter_projection_global != projection_global:
        raise Refuse(
            "BATTLE viewport call and projection setter do not share one projection-distance word"
        )

    # INITBTL constructs the two OT allocations. The two results are stored at [array+0] and
    # [array+4]. The 0x2088 allocation size is larger than the 0x800-word OT because each block also
    # carries the small per-frame side area BATTLE addresses around the table.
    ot_alloc, ot_alloc_scanned = unique_shape(
        initbtl,
        "INITBTL double OT allocator",
        {
            0x90: 0x24042088,
            0xA0: jal_word(ALLOC_HEAP),
            0xA8: 0x24042088,
            0xAC: 0xAE225C80,
            0xB0: jal_word(ALLOC_HEAP),
            0xB4: 0x26315C80,
            0xCC: 0xAE220004,
        },
    )
    if (
        initbtl.r32(ot_alloc + 0x9C) != 0xAC400004
        or initbtl.r32(ot_alloc + 0xA4) != 0xAC60E0C0
    ):
        raise Refuse(
            "INITBTL does not explicitly clear both resident packet-pool pointers"
        )
    ot_ptr_array = (
        ((initbtl.r32(ot_alloc + 0x78) & 0xFFFF) << 16)
        + s16(initbtl.r32(ot_alloc + 0xB4) & 0xFFFF)
    ) & 0xFFFFFFFF

    # BATTLE allocates the two 0x20000-byte packet pools only after a room has loaded. Their bases
    # therefore vary with guest heap history; a fixed GameConfig base/stride would be a counterfeit.
    pool_alloc, pool_alloc_scanned = unique_shape(
        battle,
        "BATTLE room double packet-pool allocator",
        {
            0x00: 0x27BDFF98,
            0x8C: 0x3C040002,
            0x90: jal_word(ALLOC_HEAP),
            0x98: 0x3C040002,
            0x9C: 0xAE02E0C0,
            0xA0: jal_word(ALLOC_HEAP),
            0xA4: 0x2610E0C0,
            0xAC: 0xAE020004,
        },
    )
    pool_ptr_array = (
        ((battle.r32(pool_alloc + 0x88) & 0xFFFF) << 16)
        + s16(battle.r32(pool_alloc + 0xA4) & 0xFFFF)
    ) & 0xFFFFFFFF

    # The battle submit caller indexes the OT pointer array by the parity word, clears exactly
    # 0x800 entries at block+0x10, and hands block+0x10+0x1FFC to the measured presenter.
    battle_submit, battle_submit_scanned = unique_shape(
        battle,
        "BATTLE OT clear/submit owner",
        {
            0x00: 0x27BDFFE0,
            0x18: 0x3C028005,
            0x20: 0x24525C80,
            0x28: 0x3C028006,
            0x2C: 0x8C42E210,
            0x40: 0x24050800,
            0x44: 0x24840010,
            0x48: jal_word(CLEAR_OTAG_R),
            0x68: jal_word(battle_present),
            0x6C: 0x24841FFC,
            0x74: 0x1440FFED,
        },
    )
    submit_ot_ptr_array = (
        ((battle.r32(battle_submit + 0x18) & 0xFFFF) << 16)
        + s16(battle.r32(battle_submit + 0x20) & 0xFFFF)
    ) & 0xFFFFFFFF
    submit_frame_buf = address_from_lui_memory(
        battle, battle_submit + 0x28, battle_submit + 0x2C, 2
    )
    if submit_ot_ptr_array != ot_ptr_array or submit_frame_buf != battle_frame_buf:
        raise Refuse(
            "BATTLE submit owner does not use the measured OT pointer array/parity word"
        )

    return {
        "title_present": title_present,
        "battle_present": battle_present,
        "battle_submit": battle_submit,
        "battle_view_init": battle_view_init,
        "battle_view_call": battle_view_call,
        "projection_setter": projection_setter,
        "projection_global": projection_global,
        "ot_alloc": ot_alloc,
        "pool_alloc": pool_alloc,
        "frame_buf": title_frame_buf,
        "draw_env": title_draw_env,
        "disp_env": title_disp_env,
        "ot_ptr_array": ot_ptr_array,
        "pool_ptr_array": pool_ptr_array,
        "ot_size": 0x2088,
        "pool_size": 0x20000,
        "title_scanned": title_scanned,
        "battle_scanned": battle_scanned,
        "ot_alloc_scanned": ot_alloc_scanned,
        "pool_alloc_scanned": pool_alloc_scanned,
        "battle_submit_scanned": battle_submit_scanned,
        "battle_view_init_scanned": battle_view_init_scanned,
        "battle_view_call_scanned": battle_view_call_scanned,
        "projection_setter_scanned": projection_setter_scanned,
    }


def config_value(text, field):
    match = re.search(rf"\.{re.escape(field)}\s*=\s*(0x[0-9A-Fa-f]+|[0-9]+)\b", text)
    if not match:
        raise Refuse(f"{CONFIG}: did not find .{field}")
    return int(match.group(1), 0)


def check_config(text):
    failures = []
    # These fields describe the retired fixed-layout native frame loop. Vagrant's measured guest
    # contract is dynamic, so a non-zero value would assert an address/layout the bytes contradict.
    zero_fields = (
        "otRegionBase",
        "otRegionStride",
        "packetPoolBase",
        "packetPoolStride",
        "otBasePtr",
        "poolPtrCur",
        "poolPtrLast",
        "clearOtagR",
        "putDrawEnv",
        "drawSync",
    )
    for field in zero_fields:
        value = config_value(text, field)
        ok = value == 0
        print(
            f"  [{'ok' if ok else 'FAIL':>4}] {field}=0x{value:08X} (dynamic guest owner)"
        )
        if not ok:
            failures.append(field)
    for field, expected in (("preserveVramBackdrop", 1), ("paceQuota", 1)):
        value = config_value(text, field)
        ok = value == expected
        print(f"  [{'ok' if ok else 'FAIL':>4}] {field}={value} expected={expected}")
        if not ok:
            failures.append(field)
    if failures:
        raise Refuse("shipping frame contract mismatch: " + ", ".join(failures))


def check_battle_source(measured, text):
    match = re.search(
        r"\bkBattleFramePresenter\s*=\s*(0x[0-9A-Fa-f]+)u?", text
    )
    if not match:
        raise Refuse(f"{BATTLE_SOURCE}: kBattleFramePresenter is absent")
    shipped = int(match.group(1), 0)
    if shipped != measured["battle_present"]:
        raise Refuse(
            f"{BATTLE_SOURCE}: kBattleFramePresenter=0x{shipped:08X}, "
            f"measured 0x{measured['battle_present']:08X}"
        )
    generated = f"ov_battle_gen_{measured['battle_present']:08X}"
    if text.count(generated) < 2:
        raise Refuse(
            f"{BATTLE_SOURCE}: measured generated super body {generated} "
            "is not retained and installed"
        )
    print(
        f"  [ ok ] BATTLE shipping completion/super: "
        f"0x{shipped:08X} / {generated}"
    )


def selftest(title, battle, initbtl, measured, battle_source):
    print("== re_frame selftest ==")
    checks = 0
    with open(CONFIG, encoding="utf-8") as source:
        config = source.read()
    check_config(config)
    checks += 1

    original = title.data
    mutable = bytearray(original)
    off = title.off(measured["title_present"] + 0x88)
    mutable[off : off + 4] = struct.pack("<I", 0)
    title.data = bytes(mutable)
    try:
        measure(title, battle, initbtl, verify_identity=False)
        raise AssertionError("TITLE presenter with destroyed DrawOTag was accepted")
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"presenter negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed TITLE DrawOTag refused: {error}")
        checks += 1
    finally:
        title.data = original

    original = battle.data
    mutable = bytearray(original)
    off = battle.off(measured["pool_alloc"] + 0x8C)
    mutable[off : off + 4] = struct.pack("<I", 0)
    battle.data = bytes(mutable)
    try:
        measure(title, battle, initbtl, verify_identity=False)
        raise AssertionError("BATTLE packet allocator with destroyed size was accepted")
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"allocator negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed BATTLE packet allocation refused: {error}")
        checks += 1
    finally:
        battle.data = original

    mutable = bytearray(original)
    off = battle.off(measured["battle_view_call"])
    mutable[off : off + 4] = struct.pack("<I", 0)
    battle.data = bytes(mutable)
    try:
        measure(title, battle, initbtl, verify_identity=False)
        raise AssertionError("BATTLE viewport call with destroyed width was accepted")
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"viewport negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed BATTLE viewport width refused: {error}")
        checks += 1
    finally:
        battle.data = original

    changed = config.replace(".otRegionBase = 0", ".otRegionBase = 4", 1)
    if changed == config:
        raise AssertionError("shipping mutation anchor did not fire")
    try:
        check_config(changed)
        raise AssertionError("non-zero fixed OT base was accepted")
    except Refuse as error:
        if "otRegionBase" not in str(error):
            raise AssertionError(f"shipping negative did not name field: {error}")
        print(f"  [ ok ] counterfeit fixed OT base refused: {error}")
        checks += 1

    shifted = battle_source.replace(
        f"0x{measured['battle_present']:08X}u",
        f"0x{measured['battle_present'] + 4:08X}u",
        1,
    )
    try:
        check_battle_source(measured, shifted)
        raise AssertionError("shifted BATTLE shipping completion was accepted")
    except Refuse as error:
        print(f"  [ ok ] shifted BATTLE shipping completion refused: {error}")
        checks += 1
    print(f"re_frame selftest: {checks}/6 PASS")


def main(argv):
    args = list(argv)
    do_check = "--check-config" in args
    do_check_source = "--check-source" in args
    do_selftest = "--selftest" in args
    args = [
        arg
        for arg in args
        if arg not in ("--check-config", "--check-source", "--selftest")
    ]
    if len(args) not in (0, 3):
        print(
            "usage: re_frame.py [--check-config] [--check-source] [--selftest] "
            "[TITLE.PRG BATTLE.PRG INITBTL.PRG]",
            file=sys.stderr,
        )
        return 2
    try:
        title_path, battle_path, initbtl_path = (
            args if args else (DEFAULT_TITLE, DEFAULT_BATTLE, DEFAULT_INITBTL)
        )
        title = Overlay(title_path, TITLE_BASE, TITLE_SHA1)
        battle = Overlay(battle_path, BATTLE_BASE, BATTLE_SHA1)
        initbtl = Overlay(initbtl_path, INITBTL_BASE, INITBTL_SHA1)
        measured = measure(title, battle, initbtl)
        print("== Vagrant guest-owned frame/present contract ==")
        print(
            f"  TITLE presenter 0x{measured['title_present']:08X}; BATTLE presenter "
            f"0x{measured['battle_present']:08X}; both submit through DrawOTag 0x{DRAW_OTAG:08X}"
        )
        print(
            f"  resident parity 0x{measured['frame_buf']:08X}; DRAWENV "
            f"0x{measured['draw_env']:08X}; DISPENV 0x{measured['disp_env']:08X}"
        )
        print(
            f"  BATTLE submit owner 0x{measured['battle_submit']:08X}: OT pointers "
            f"0x{measured['ot_ptr_array']:08X}, 2 x 0x{measured['ot_size']:X}; packet pointers "
            f"0x{measured['pool_ptr_array']:08X}, 2 x 0x{measured['pool_size']:X}"
        )
        print(
            f"  BATTLE viewport init 0x{measured['battle_view_init']:08X}, call sequence at "
            f"0x{measured['battle_view_call']:08X} with 320x240 input / 320x224 draw area; "
            "presenter restores OFX/OFY 160,112 each field"
        )
        print(
            f"  projection distance 0x{measured['projection_global']:08X}; setter "
            f"0x{measured['projection_setter']:08X} stores it and calls SetGeomScreen"
        )
        print(
            "  boundary: OT/pool bases are guest-heap results, not fixed regions; keep the legacy "
            "native-loop GameConfig fields zero"
        )
        if do_check:
            with open(CONFIG, encoding="utf-8") as source:
                check_config(source.read())
        with open(BATTLE_SOURCE, encoding="utf-8") as source:
            battle_source = source.read()
        if do_check_source:
            check_battle_source(measured, battle_source)
        if do_selftest:
            selftest(title, battle, initbtl, measured, battle_source)
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_frame REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

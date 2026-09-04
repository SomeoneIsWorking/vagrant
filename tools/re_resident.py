#!/usr/bin/env python3
"""Measure and gate the finite resident -> TITLE bootstrap split.

The shipping owner must reproduce the executable's finite leaf order around InitCARD's VSync(0)
and _displayLoadingScreen's VSync(2), preserve _diskReset's VSync(3), replace each blocking
_loadMenuSound read with a complete native-owned field, and prevent ClearImage's GPU-timeout arm
from querying guest VSync. This tool derives those owners and callees from the owned SLUS bytes,
then compares the typed facts and source wiring to that measurement.
"""

import os
import re
import struct
import sys
from pathlib import Path

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse, s16
from re_spu_transfer import (
    based_address,
    jal_target,
    materialized_address,
    unique_shape,
)
from re_vblank import measure as measure_vblank

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = os.path.join(ROOT, "game", "core", "resident_facts.h")
CD_FACTS = os.path.join(ROOT, "game", "cd", "cd_facts.h")
PHASE = os.path.join(ROOT, "game", "core", "resident_phase.cpp")
FRAME = os.path.join(ROOT, "game", "sync", "frame_loop.cpp")
GPU_FACTS = os.path.join(ROOT, "game", "render", "gpu_sync_facts.h")


def calls(img, owner, offsets):
    return [jal_target(owner + offset, img.r32(owner + offset)) for offset in offsets]


def immediate_from_zero(word, reg):
    if (
        word >> 26 not in (0x09, 0x0D)
        or (word >> 21) & 31 != 0
        or (word >> 16) & 31 != reg
    ):
        raise Refuse(
            f"expected immediate materialisation for register {reg}, found 0x{word:08X}"
        )
    value = word & 0xFFFF
    return value if word >> 26 == 0x0D else s16(value) & 0xFFFFFFFF


def split_immediate(hi_word, lo_word, reg):
    if hi_word >> 26 != 0x0F or (hi_word >> 16) & 31 != reg:
        raise Refuse(f"expected lui for register {reg}, found 0x{hi_word:08X}")
    if (
        lo_word >> 26 not in (0x09, 0x0D)
        or (lo_word >> 21) & 31 != reg
        or (lo_word >> 16) & 31 != reg
    ):
        raise Refuse(
            f"expected split immediate for register {reg}, found 0x{lo_word:08X}"
        )
    low = lo_word & 0xFFFF
    return (
        ((hi_word & 0xFFFF) << 16) + (low if lo_word >> 26 == 0x0D else s16(low))
    ) & 0xFFFFFFFF


def measure(img, verify_identity=True):
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(
            f"{img.path}: sha1 {img.sha1()} != SLUS_010.40 {FIXTURE_SHA1}; nothing was measured"
        )
    vsync = measure_vblank(img, verify_identity=False)["vsync"]

    gpu_timeout_arm, gpu_timeout_scanned = unique_shape(
        img,
        "libgpu GPU-timeout arm",
        {
            0x00: 0x27BDFFE8,
            0x04: 0xAFBF0010,
            0x0C: 0x2404FFFF,
            0x10: 0x244200F0,
            0x14: 0x3C018003,
            0x18: 0xAC223580,
            0x1C: 0x3C018003,
            0x20: 0xAC203584,
            0x28: 0x27BD0018,
            0x2C: 0x03E00008,
        },
    )
    if jal_target(gpu_timeout_arm + 0x08, img.r32(gpu_timeout_arm + 0x08)) != vsync:
        raise Refuse(
            f"GPU-timeout arm 0x{gpu_timeout_arm:08X} no longer queries measured VSync"
        )
    gpu_timeout_deadline = based_address(
        img.r32(gpu_timeout_arm + 0x14), img.r32(gpu_timeout_arm + 0x18), 1
    )
    gpu_timeout_flag = based_address(
        img.r32(gpu_timeout_arm + 0x1C), img.r32(gpu_timeout_arm + 0x20), 1
    )

    sys_init, sys_scanned = unique_shape(
        img,
        "_sysInit",
        {
            0x00: 0x27BDFFE0,
            0x04: 0x00002021,
            0x50: 0x02002021,
            0x5C: 0x00002021,
            0x68: 0x24040010,
            0xB4: 0x24020001,
            0xC4: 0x03E00008,
            0xC8: 0x27BD0020,
        },
    )
    sys_calls = calls(
        img,
        sys_init,
        [
            0x10,
            0x18,
            0x20,
            0x28,
            0x30,
            0x38,
            0x40,
            0x48,
            0x54,
            0x60,
            0x6C,
            0x74,
            0x7C,
            0x84,
            0x8C,
            0x94,
            0x9C,
        ],
    )
    pad0 = materialized_address(img.r32(sys_init + 0x24), img.r32(sys_init + 0x44), 16)
    pad1 = (pad0 + s16(img.r32(sys_init + 0x4C) & 0xFFFF)) & 0xFFFFFFFF

    init_card = sys_calls[5]
    if (
        img.r32(init_card) != 0x27BDFFE0
        or jal_target(init_card + 0x1C, img.r32(init_card + 0x1C)) != vsync
    ):
        raise Refuse(
            f"InitCARD 0x{init_card:08X}: its first field boundary is not measured VSync 0x{vsync:08X}"
        )
    init_card_calls = calls(
        img, init_card, [0x14, 0x1C, 0x24, 0x2C, 0x40, 0x48, 0x50, 0x58, 0x60, 0x74]
    )

    loading, loading_scanned = unique_shape(
        img,
        "_displayLoadingScreen",
        {
            0x00: 0x27BDFFC8,
            0x04: 0x24040140,
            0x08: 0x240500F0,
            0x4C: 0x24020400,
            0x50: 0xA7A2001C,
            0x54: 0x24020200,
            0x1B0: 0x03E00008,
            0x1B4: 0x27BD0038,
        },
    )
    loading_vsync = jal_target(loading + 0x70, img.r32(loading + 0x70))
    if loading_vsync != vsync or img.r32(loading + 0x74) != 0x24040002:
        raise Refuse(
            f"loading screen 0x{loading:08X}: expected VSync(2), found target 0x{loading_vsync:08X}"
        )
    loading_calls = calls(
        img, loading, [0x34, 0x60, 0x68, 0x70, 0x100, 0x180, 0x188, 0x190]
    )
    loading_hi = img.r32(loading + 0x7C)
    loading_read = img.r32(loading + 0x98)
    if (
        loading_hi >> 26 != 0x0F
        or (loading_hi >> 16) & 31 != 19
        or loading_read >> 26 != 0x24
        or (loading_read >> 21) & 31 != 19
    ):
        raise Refuse(
            "loading screen no longer materialises its image header through s3"
        )
    loading_header = (
        ((loading_hi & 0xFFFF) << 16) + s16(loading_read & 0xFFFF)
    ) & 0xFFFFFFFF

    sys_reinit, reinit_scanned = unique_shape(
        img,
        "_sysReinit",
        {
            0x00: 0x27BDFFD0,
            0x64: 0x24040001,
            0x6C: 0x00002021,
            0xBC: 0x3C048010,
            0xC0: 0x3484C000,
            0xC4: 0x3C05000F,
            0xFC: 0x2403001F,
            0x140: 0x03E00008,
            0x144: 0x27BD0030,
        },
    )
    reinit_calls = calls(
        img,
        sys_reinit,
        [
            0x58,
            0x60,
            0x68,
            0x7C,
            0x84,
            0x8C,
            0x94,
            0x9C,
            0xA8,
            0xB4,
            0xC8,
            0xD0,
            0xD8,
            0xE0,
            0xE8,
            0xF4,
        ],
    )
    if reinit_calls[5] != loading:
        raise Refuse("_sysReinit does not call the unique loading-screen owner")

    disk_reset = reinit_calls[12]
    if (
        img.r32(disk_reset) != 0x27BDFFE8
        or img.r32(disk_reset + 0x70) != 0x24040003
        or img.r32(disk_reset + 0x7C) != 0x03E00008
    ):
        raise Refuse(
            f"_diskReset 0x{disk_reset:08X}: expected 0x18-byte owner ending after VSync(3)"
        )
    disk_reset_calls = calls(img, disk_reset, [0x14, 0x24, 0x5C, 0x6C])
    if disk_reset_calls[0] != disk_reset_calls[2] or disk_reset_calls[3] != vsync:
        raise Refuse(
            f"_diskReset 0x{disk_reset:08X}: blocking controls or VSync edge drifted"
        )
    disk_state = (
        ((img.r32(disk_reset + 0x2C) & 0xFFFF) << 16)
        + s16(img.r32(disk_reset + 0x30) & 0xFFFF)
    ) & 0xFFFFFFFF
    if (
        img.r32(disk_reset + 0x2C) >> 26 != 0x0F
        or (img.r32(disk_reset + 0x2C) >> 16) & 31 != 4
        or img.r32(disk_reset + 0x30) >> 26 != 0x09
        or (img.r32(disk_reset + 0x30) >> 21) & 31 != 4
    ):
        raise Refuse("_diskReset no longer materialises its state block through r4")
    control_hi = img.r32(disk_reset + 0x28)
    control_lo = img.r32(disk_reset + 0x58)
    if (
        control_hi >> 26 != 0x0F
        or (control_hi >> 16) & 31 != 16
        or control_lo >> 26 != 0x09
        or (control_lo >> 21) & 31 != 16
        or (control_lo >> 16) & 31 != 5
    ):
        raise Refuse("_diskReset no longer materialises its control buffer into r5")
    control_buffer = (
        ((control_hi & 0xFFFF) << 16) + s16(control_lo & 0xFFFF)
    ) & 0xFFFFFFFF
    read_buffer_word = img.r32(disk_reset + 0x50)
    if read_buffer_word >> 26 != 0x2B or (read_buffer_word >> 21) & 31 != 2:
        raise Refuse("_diskReset no longer clears the CD read buffer through r2")
    cd_read_buffer = (
        ((img.r32(disk_reset + 0x4C) & 0xFFFF) << 16) + s16(read_buffer_word & 0xFFFF)
    ) & 0xFFFFFFFF

    game_main, main_scanned = unique_shape(
        img,
        "vs_main_exec",
        {
            0x00: 0x27BDFFE8,
            0x18: 0x3C048005,
            0x20: 0x24840474,
            0x2C: 0x8FBF0010,
            0x34: 0x03E00008,
            0x38: 0x27BD0018,
        },
    )
    main_calls = calls(img, game_main, [0x08, 0x10, 0x1C, 0x24])
    if main_calls[1] != sys_init:
        raise Refuse("vs_main_exec does not call the unique _sysInit")

    exec_title = main_calls[3]
    if (
        img.r32(exec_title) != 0x27BDFFE8
        or jal_target(exec_title + 0x1C, img.r32(exec_title + 0x1C)) != sys_reinit
    ):
        raise Refuse(
            f"vs_main_execTitle 0x{exec_title:08X}: measured _sysReinit edge drifted"
        )
    load_title = jal_target(exec_title + 0x24, img.r32(exec_title + 0x24))
    title_entry = jal_target(exec_title + 0x2C, img.r32(exec_title + 0x2C))
    if (
        img.r32(load_title) != 0x27BDFFD8
        or img.r32(load_title + 0x48) != 0x24020004
        or img.r32(load_title + 0x54) != 0x0C010987
        or img.r32(load_title + 0x88) != 0x03E00008
        or img.r32(load_title + 0x8C) != 0x27BD0028
    ):
        raise Refuse(
            f"_loadTitlePrg 0x{load_title:08X}: finite queue/read/wait shape drifted"
        )
    title_lba = split_immediate(
        img.r32(load_title + 0x04), img.r32(load_title + 0x08), 3
    )
    title_size = split_immediate(
        img.r32(load_title + 0x0C), img.r32(load_title + 0x10), 2
    )
    title_slot_pointer = based_address(
        img.r32(load_title + 0x34), img.r32(load_title + 0x38), 2
    )
    title_base = img.r32(title_slot_pointer)
    title_start_state = based_address(
        img.r32(exec_title + 0x34), img.r32(exec_title + 0x38), 3
    )
    if title_base < 0x80010000 or title_base >= 0x80200000:
        raise Refuse(
            f"_loadTitlePrg slot 0x{title_slot_pointer:08X} contains invalid guest base 0x{title_base:08X}"
        )

    menu_sound = reinit_calls[13]
    if img.r32(menu_sound) != 0x27BDFFE8 or img.r32(menu_sound + 0x138) != 0x27BD0018:
        raise Refuse(
            f"_loadMenuSound 0x{menu_sound:08X}: expected 0x18-byte finite owner"
        )
    menu_calls = calls(
        img,
        menu_sound,
        [
            0x08,
            0x10,
            0x18,
            0x2C,
            0x38,
            0x40,
            0x4C,
            0x64,
            0x70,
            0x78,
            0x84,
            0xA0,
            0xB0,
            0xB8,
            0xD4,
            0xDC,
        ],
    )
    disk_load = menu_calls[3]
    disk_init_read = jal_target(disk_load + 0x18, img.r32(disk_load + 0x18))
    disk_get_state = jal_target(disk_load + 0x38, img.r32(disk_load + 0x38))
    gametime_update = jal_target(disk_load + 0x78, img.r32(disk_load + 0x78))
    if jal_target(gametime_update + 0x10, img.r32(gametime_update + 0x10)) != vsync:
        raise Refuse(
            "diskLoadFile's gametime update no longer begins with measured VSync"
        )
    process_cd_queue = jal_target(
        gametime_update + 0x30, img.r32(gametime_update + 0x30)
    )
    game_time_hi = img.r32(gametime_update + 0x38)
    game_time_lo = img.r32(gametime_update + 0x3C)
    if game_time_hi >> 26 != 0x0F or (game_time_hi >> 16) & 31 != 5:
        raise Refuse("gametimeUpdate no longer materialises game time through r5")
    if game_time_lo >> 26 not in (0x08, 0x09) or (game_time_lo >> 21) & 31 != 5:
        raise Refuse(
            "gametimeUpdate no longer derives the game-time byte owner from r5"
        )
    game_time = (
        ((game_time_hi & 0xFFFF) << 16) + s16(game_time_lo & 0xFFFF)
    ) & 0xFFFFFFFF
    tick_hi = img.r32(gametime_update + 0x50)
    tick_read = img.r32(gametime_update + 0x58)
    if tick_hi >> 26 != 0x0F or (tick_hi >> 16) & 31 != 2:
        raise Refuse("gametimeUpdate no longer materialises tick speed through r2")
    if tick_read >> 26 != 0x24 or (tick_read >> 21) & 31 != 2:
        raise Refuse("gametimeUpdate no longer loads the byte tick speed through r2")
    tick_speed = (((tick_hi & 0xFFFF) << 16) + s16(tick_read & 0xFFFF)) & 0xFFFFFFFF
    sfx_data = materialized_address(
        img.r32(menu_sound + 0xCC), img.r32(menu_sound + 0xD0), 16
    )
    menu_loads = [
        (
            immediate_from_zero(img.r32(menu_sound + 0x24), 4),
            immediate_from_zero(img.r32(menu_sound + 0x28), 5),
        ),
        (
            immediate_from_zero(img.r32(menu_sound + 0x58), 4),
            split_immediate(img.r32(menu_sound + 0x5C), img.r32(menu_sound + 0x60), 5),
        ),
        (
            split_immediate(img.r32(menu_sound + 0x90), img.r32(menu_sound + 0x94), 4),
            split_immediate(img.r32(menu_sound + 0x98), img.r32(menu_sound + 0x9C), 5),
        ),
        (
            split_immediate(img.r32(menu_sound + 0xC0), img.r32(menu_sound + 0xC4), 4),
            immediate_from_zero(img.r32(menu_sound + 0xC8), 5),
        ),
    ]

    return {
        "vsync": vsync,
        "game_main": game_main,
        "cxx_main": main_calls[0],
        "sys_init": sys_init,
        "sys_calls": sys_calls,
        "pad0": pad0,
        "pad1": pad1,
        "overlay_get_sp": main_calls[2],
        "title_outer_stack": 0x80050474,
        "exec_title": exec_title,
        "load_title": load_title,
        "title_lba": title_lba,
        "title_size": title_size,
        "title_slot_pointer": title_slot_pointer,
        "title_base": title_base,
        "title_entry": title_entry,
        "title_start_state": title_start_state,
        "init_card": init_card,
        "init_card_calls": init_card_calls,
        "loading": loading,
        "loading_calls": loading_calls,
        "loading_header": loading_header,
        "sys_reinit": sys_reinit,
        "reinit_calls": reinit_calls,
        "disk_reset": disk_reset,
        "disk_reset_calls": disk_reset_calls,
        "disk_state": disk_state,
        "ds_control_buffer": control_buffer,
        "cd_read_buffer": cd_read_buffer,
        "load_menu_sound": menu_sound,
        "menu_calls": menu_calls,
        "disk_load": disk_load,
        "disk_init_read": disk_init_read,
        "disk_get_state": disk_get_state,
        "gametime_update": gametime_update,
        "process_cd_queue": process_cd_queue,
        "game_time": game_time,
        "tick_speed": tick_speed,
        "gpu_timeout_arm": gpu_timeout_arm,
        "gpu_timeout_deadline": gpu_timeout_deadline,
        "gpu_timeout_flag": gpu_timeout_flag,
        "sfx_data": sfx_data,
        "menu_loads": menu_loads,
        "scanned": sys_scanned + loading_scanned + reinit_scanned + main_scanned + gpu_timeout_scanned,
    }


def source_constant(text, name):
    match = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+)u?", text)
    if not match:
        raise Refuse(f"source facts: did not find literal {name}")
    return int(match.group(1), 0)


def check_source(measured, sources=None):
    if sources is None:
        sources = {
            path: Path(path).read_text(encoding="utf-8")
            for path in (FACTS, CD_FACTS, PHASE, FRAME, GPU_FACTS)
        }
    facts, cd_facts, phase, frame, gpu_facts = (
        sources[path] for path in (FACTS, CD_FACTS, PHASE, FRAME, GPU_FACTS)
    )
    expected = {
        "kCxxMain": measured["cxx_main"],
        "kPadBuffer0": measured["pad0"],
        "kPadBuffer1": measured["pad1"],
        "kOverlayGetSp": measured["overlay_get_sp"],
        "kTitleOuterStack": measured["title_outer_stack"],
        "kTitlePrgLba": measured["title_lba"],
        "kTitlePrgSize": measured["title_size"],
        "kTitleOverlayBase": measured["title_base"],
        "kTitleEntry": measured["title_entry"],
        "kTitleStartState": measured["title_start_state"],
        "kLoadingImageHeader": measured["loading_header"],
        "kLoadMenuSound": measured["load_menu_sound"],
        "kInitSound": measured["menu_calls"][0],
        "kSetCdVolume": measured["menu_calls"][1],
        "kAllocHeapR": measured["menu_calls"][2],
        "kFreeHeapR": measured["menu_calls"][5],
        "kDiskInitRead": measured["disk_init_read"],
        "kDiskGetState": measured["disk_get_state"],
        "kProcessCdQueue": measured["process_cd_queue"],
        "kLoadWaveBank": measured["menu_calls"][4],
        "kLoadProgramBank": measured["menu_calls"][12],
        "kBindSfxBlob": measured["menu_calls"][15],
        "kSfxData": measured["sfx_data"],
        "kGameTime": measured["game_time"],
        "kGameTimeTickSpeed": measured["tick_speed"],
        "kWave0000Lba": measured["menu_loads"][0][0],
        "kWave0000Size": measured["menu_loads"][0][1],
        "kWave0005Lba": measured["menu_loads"][1][0],
        "kWave0005Size": measured["menu_loads"][1][1],
        "kWave0200Lba": measured["menu_loads"][2][0],
        "kWave0200Size": measured["menu_loads"][2][1],
        "kEffect00Lba": measured["menu_loads"][3][0],
        "kEffect00Size": measured["menu_loads"][3][1],
    }
    failures = []
    for name, want in expected.items():
        got = source_constant(facts, name)
        ok = got == want
        print(
            f"  [{'ok' if ok else 'FAIL':>4}] {name}=0x{got:08X} measured=0x{want:08X}"
        )
        if not ok:
            failures.append(name)
    cd_expected = {
        "kDsControlB": measured["disk_reset_calls"][0],
        "kDsFlush": measured["disk_reset_calls"][1],
        "kDiskState": measured["disk_state"],
        "kDsControlBuffer": measured["ds_control_buffer"],
        "kCdReadBuffer": measured["cd_read_buffer"],
    }
    for name, want in cd_expected.items():
        got = source_constant(cd_facts, name)
        ok = got == want
        print(
            f"  [{'ok' if ok else 'FAIL':>4}] {name}=0x{got:08X} measured=0x{want:08X}"
        )
        if not ok:
            failures.append(name)
    gpu_expected = {
        "kTimeoutArm": measured["gpu_timeout_arm"],
        "kTimeoutDeadline": measured["gpu_timeout_deadline"],
        "kTimeoutFlag": measured["gpu_timeout_flag"],
    }
    for name, want in gpu_expected.items():
        got = source_constant(gpu_facts, name)
        ok = got == want
        print(f"  [{'ok' if ok else 'FAIL':>4}] {name}=0x{got:08X} measured=0x{want:08X}")
        if not ok:
            failures.append(name)
    wiring = {
        "finite InitCARD field state": (phase, r"kCardStop.*InitCardFieldWait"),
        "two-field loading state": (
            phase,
            r"loadingFieldsRemaining_\s*=\s*2u.*LoadingScreenFieldWait",
        ),
        "finite disk-reset field owner": (
            phase,
            r"kDsControlB.*diskResetFieldsRemaining_\s*=\s*3u.*DiskResetFieldWait",
        ),
        "finite menu-sound read owner": (
            phase,
            r"beginMenuSoundBody.*beginMenuLoad.*readFile.*MenuSoundLoadFieldWait",
        ),
        "post-field native read consumer": (
            phase,
            r"advanceMenuLoad.*game_time::advance.*finishMenuLoad",
        ),
        "TITLE native file owner": (
            phase,
            r"finishTitleReinit.*kTitlePrgLba.*kTitlePrgSize.*kTitleOverlayBase.*TitleProgramLoadFieldWait",
        ),
        "TITLE overlay entry after field": (
            phase,
            r"TitleProgramLoadFieldWait.*enterTitleProgram.*titleSplash\.begin",
        ),
        "resume occurs after pace": (
            frame,
            r"services_\.pace\(core\).*services_\.resumeResident\(core\)",
        ),
    }
    for name, (text, pattern) in wiring.items():
        ok = re.search(pattern, text, re.DOTALL) is not None
        print(f"  [{'ok' if ok else 'FAIL':>4}] {name}")
        if not ok:
            failures.append(name)
    if re.search(r"\bkVSync\b", phase):
        failures.append("guest-owned wait dispatch")
    if re.search(
        r"services_\.(?:call0|call1|call2|call4)\s*\([^;]*kLoadMenuSound", phase
    ):
        failures.append("asynchronous menu-sound whole dispatch")
    if failures:
        raise Refuse("shipping mismatch: " + ", ".join(failures))


def selftest(img, measured):
    print("== re_resident selftest ==")
    checks = 0
    check_source(measured)
    checks += 1
    original = img.data
    mutable = bytearray(original)
    off = img.off(measured["init_card"] + 0x1C)
    mutable[off : off + 4] = struct.pack("<I", 0)
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError("destroyed InitCARD VSync edge was accepted")
    except Refuse as error:
        print(f"  [ ok ] destroyed InitCARD VSync edge refused: {error}")
        checks += 1
    finally:
        img.data = original
    sources = {
        path: Path(path).read_text(encoding="utf-8")
        for path in (FACTS, CD_FACTS, PHASE, FRAME, GPU_FACTS)
    }
    sabotaged = dict(sources)
    old = f"kLoadMenuSound = 0x{measured['load_menu_sound']:08X}u"
    sabotaged[FACTS] = sabotaged[FACTS].replace(
        old, f"kLoadMenuSound = 0x{measured['load_menu_sound'] + 4:08X}u", 1
    )
    try:
        check_source(measured, sabotaged)
        raise AssertionError("+4 menu-sound boundary was accepted")
    except Refuse as error:
        print(f"  [ ok ] +4 menu-sound boundary refused: {error}")
        checks += 1
    sabotaged = dict(sources)
    old = f"kTitleEntry = 0x{measured['title_entry']:08X}u"
    sabotaged[FACTS] = sabotaged[FACTS].replace(
        old, f"kTitleEntry = 0x{measured['title_entry'] + 4:08X}u", 1
    )
    try:
        check_source(measured, sabotaged)
        raise AssertionError("+4 TITLE entry was accepted")
    except Refuse as error:
        print(f"  [ ok ] +4 TITLE entry refused: {error}")
        checks += 1
    sabotaged = dict(sources)
    changed_frame = sabotaged[FRAME]
    resume_line = "  services_.resumeResident(core);\n"
    resume_at = changed_frame.rfind(resume_line)
    if resume_at < 0:
        raise AssertionError("resident resume mutation anchor did not fire")
    changed_frame = (
        changed_frame[:resume_at] + changed_frame[resume_at + len(resume_line) :]
    )
    changed_frame = changed_frame.replace(
        "  services_.pace(core);\n", resume_line + "  services_.pace(core);\n", 1
    )
    sabotaged[FRAME] = changed_frame
    try:
        check_source(measured, sabotaged)
        raise AssertionError("resident resume before field completion was accepted")
    except Refuse as error:
        print(f"  [ ok ] pre-pace resident resume refused: {error}")
        checks += 1
    sabotaged = dict(sources)
    old = f"kTimeoutArm = 0x{measured['gpu_timeout_arm']:08X}u"
    sabotaged[GPU_FACTS] = sabotaged[GPU_FACTS].replace(
        old, f"kTimeoutArm = 0x{measured['gpu_timeout_arm'] + 4:08X}u", 1
    )
    try:
        check_source(measured, sabotaged)
        raise AssertionError("+4 GPU-timeout arm was accepted")
    except Refuse as error:
        print(f"  [ ok ] +4 GPU-timeout arm refused: {error}")
        checks += 1
    print(f"re_resident selftest: {checks}/6 PASS")


def main(argv):
    args = list(argv)
    do_check = "--check-source" in args
    do_selftest = "--selftest" in args
    args = [arg for arg in args if arg not in ("--check-source", "--selftest")]
    if len(args) > 1:
        print(
            "usage: re_resident.py [--check-source] [--selftest] [SLUS_010.40]",
            file=sys.stderr,
        )
        return 2
    try:
        img = Image(args[0] if args else DEFAULT_EXE)
        measured = measure(img)
        print("== Vagrant finite resident -> TITLE evidence ==")
        print(
            f"  scanned {measured['scanned']} owner candidates; vs_main_exec 0x{measured['game_main']:08X} "
            f"-> _sysInit 0x{measured['sys_init']:08X} -> InitCARD 0x{measured['init_card']:08X}"
        )
        print(
            f"  InitCARD waits at VSync 0x{measured['vsync']:08X}; TITLE _sysReinit "
            f"0x{measured['sys_reinit']:08X} reaches loading screen 0x{measured['loading']:08X}"
        )
        print(
            f"  loading screen waits VSync(2), then _sysReinit reaches _loadMenuSound "
            f"0x{measured['load_menu_sound']:08X}"
        )
        print(
            f"  ClearImage's GPU queue arms timeout 0x{measured['gpu_timeout_arm']:08X} via VSync(-1); "
            f"deadline 0x{measured['gpu_timeout_deadline']:08X}, flag 0x{measured['gpu_timeout_flag']:08X}"
        )
        print(
            f"  _diskReset 0x{measured['disk_reset']:08X} preserves VSync(3); state "
            f"0x{measured['disk_state']:08X}, control 0x{measured['ds_control_buffer']:08X}"
        )
        print(
            f"  _loadMenuSound's blocking disk owner 0x{measured['disk_load']:08X} calls "
            f"gametimeUpdate 0x{measured['gametime_update']:08X}; finite host fields own its real-disc reads"
        )
        print(
            f"  _loadTitlePrg 0x{measured['load_title']:08X} reads LBA {measured['title_lba']} "
            f"size 0x{measured['title_size']:X} to 0x{measured['title_base']:08X}, then "
            f"vs_main_execTitle calls entry 0x{measured['title_entry']:08X}"
        )
        if do_check:
            check_source(measured)
        if do_selftest:
            selftest(img, measured)
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_resident REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

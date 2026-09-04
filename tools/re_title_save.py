#!/usr/bin/env python3
"""Measure and gate TITLE's finite _saveFileExists owner.

The owned TITLE bytes and resident executable establish the complete top-down caller chain. The
shipping phase must preserve every non-VSync leaf and state transition while returning each retail
VSync(2) to VagrantFrameDriver. No decomp label or shipping address is an input to the measurement.
"""

import argparse
import re
import struct
import sys

from re_crt0 import DEFAULT_EXE, Image, Refuse, s16
from re_frame import DEFAULT_TITLE, TITLE_BASE, TITLE_SHA1, Overlay, jal_word
from re_resident import measure as measure_resident
from re_spu_transfer import jal_target, unique_shape

FACTS = "game/save/title_save_facts.h"
MEMCARD_FACTS = "game/save/title_memcard_facts.h"
SOURCE = "game/save/title_save_check.cpp"
RESIDENT_PHASE = "game/core/resident_phase.cpp"


def measure(title, resident, verify_identity=True):
    if verify_identity:
        title.check_identity()
    resident_facts = measure_resident(resident, verify_identity=verify_identity)
    vsync = resident_facts["vsync"]

    owner, scanned = unique_shape(
        title,
        "TITLE _saveFileExists",
        {
            0x00: 0x27BDFF98,
            0x04: 0xAFB3005C,
            0x08: 0x00009821,
            0x0C: 0x24040001,
            0x10: 0xAFBF0064,
            0x14: 0xAFB40060,
            0x18: 0xAFB20058,
            0x1C: 0xAFB10054,
            0x24: 0xAFB00050,
            0x2C: 0x24040002,
            0x34: 0x00002021,
            0x38: 0x1040FFFB,
            0x40: 0x27B20038,
            0x44: 0x3C148007,
            0x4C: 0x02202021,
            0x54: 0x00002021,
            0x58: 0x24040002,
            0x5C: jal_word(vsync),
            0x60: 0x30500003,
            0x64: 0x1200FFFA,
            0x68: 0x24020001,
            0x74: 0x8E85288C,
            0x7C: 0x24060016,
            0x80: 0x02402021,
            0x84: 0x27A50010,
            0x88: 0x2622002F,
            0x8C: 0xA3A2003A,
            0x90: 0x2402003F,
            0x98: 0xA3A2004C,
            0xB0: 0x2A220003,
            0xB4: 0x1440FFE4,
            0xC4: 0x02601021,
        },
    )
    calls = {
        "init_memcard": jal_target(owner + 0x20, title.r32(owner + 0x20)),
        "game_time_update": jal_target(owner + 0x28, title.r32(owner + 0x28)),
        "memcard_event_handler": jal_target(owner + 0x48, title.r32(owner + 0x48)),
        "vsync": jal_target(owner + 0x5C, title.r32(owner + 0x5C)),
        "r_memcpy": jal_target(owner + 0x78, title.r32(owner + 0x78)),
        "first_file": jal_target(owner + 0x94, title.r32(owner + 0x94)),
        "shutdown_memcard": jal_target(owner + 0xBC, title.r32(owner + 0xBC)),
    }
    if calls["game_time_update"] != resident_facts["gametime_update"]:
        raise Refuse(
            f"TITLE caller reaches 0x{calls['game_time_update']:08X}, resident measurement owns "
            f"0x{resident_facts['gametime_update']:08X}"
        )
    if calls["vsync"] != vsync:
        raise Refuse("_saveFileExists direct field wait no longer reaches measured Sony VSync")

    template_load = title.r32(owner + 0x74)
    if template_load >> 26 != 0x23 or (template_load >> 21) & 31 != 20 or (template_load >> 16) & 31 != 5:
        raise Refuse("_saveFileExists no longer loads its filename template pointer through s4/a1")
    template_pointer = (0x80070000 + s16(template_load & 0xFFFF)) & 0xFFFFFFFF
    template = title.r32(template_pointer)
    expected = b"bu00:BASLUS-01040VAG0"
    start = title.off(template)
    if title.data[start : start + len(expected)] != expected:
        raise Refuse("_saveFileExists template pointer no longer names the retail wildcard base")

    gametime = calls["game_time_update"]
    if jal_target(gametime + 0x10, resident.r32(gametime + 0x10)) != vsync:
        raise Refuse("gametimeUpdate no longer begins at the measured VSync field boundary")
    asm_nop = jal_target(gametime + 0x28, resident.r32(gametime + 0x28))
    process_cd_queue = jal_target(gametime + 0x30, resident.r32(gametime + 0x30))
    if process_cd_queue != resident_facts["process_cd_queue"]:
        raise Refuse("gametimeUpdate CD-queue tail disagrees with resident measurement")

    return {
        "owner": owner,
        "scanned": scanned,
        **calls,
        "asm_nop": asm_nop,
        "process_cd_queue": process_cd_queue,
        "template_pointer": template_pointer,
        "stack_size": (-s16(title.r32(owner) & 0xFFFF)) & 0xFFFFFFFF,
        "filename_offset": title.r32(owner + 0x84) & 0xFFFF,
        "directory_offset": title.r32(owner + 0x40) & 0xFFFF,
        "filename_size": title.r32(owner + 0x7C) & 0xFFFF,
    }


def source_constant(text, name):
    found = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+|[0-9]+)u?", text)
    if not found:
        raise Refuse(f"{FACTS}: missing {name}")
    return int(found.group(1), 0)


def check_source(measured, sources=None):
    if sources is None:
        with open(FACTS, encoding="utf-8") as source:
            facts = source.read()
        with open(MEMCARD_FACTS, encoding="utf-8") as source:
            memcard_facts = source.read()
        with open(SOURCE, encoding="utf-8") as source:
            owner = source.read()
        with open(RESIDENT_PHASE, encoding="utf-8") as source:
            resident_phase = source.read()
    else:
        facts, memcard_facts, owner, resident_phase = sources
    expected = {
        "kOwner": measured["owner"],
        "kGameTimeUpdate": measured["game_time_update"],
        "kAsmNop": measured["asm_nop"],
        "kProcessCdQueue": measured["process_cd_queue"],
        "kMemcardEventHandler": measured["memcard_event_handler"],
        "kRMemcpy": measured["r_memcpy"],
        "kFirstFile": measured["first_file"],
        "kShutdownMemcard": measured["shutdown_memcard"],
        "kFilenameTemplatePointer": measured["template_pointer"],
        "kStackFrameSize": measured["stack_size"],
        "kFilenameOffset": measured["filename_offset"],
        "kDirectoryEntryOffset": measured["directory_offset"],
        "kFilenameSize": measured["filename_size"],
    }
    failures = [name for name, want in expected.items() if source_constant(facts, name) != want]
    if source_constant(memcard_facts, "kOwner") != measured["init_memcard"]:
        failures.append("TITLE memcard-init owner")
    wiring = {
        "gametime tail order": r"kAsmNop.*kProcessCdQueue.*game_time::advance.*title_memcard::kOwner",
        "event wait state": r"kMemcardEventHandler.*eventState_.*EventFieldWait",
        "retail filename probe": r"kRMemcpy.*kFilenameSize.*mem_w8\(filename \+ 2u.*mem_w8\(filename \+ 20u.*kFirstFile",
        "stack restored on completion": r"kShutdownMemcard.*kStackFrameSize.*Complete",
    }
    for name, pattern in wiring.items():
        if re.search(pattern, owner, re.DOTALL) is None:
            failures.append(name)
    if "kVSync" in owner or "kGameTimeUpdate" in re.sub(r"//.*", "", owner):
        failures.append("guest wait dispatch retained")
    if re.search(r"titleSaveCheck\.begin.*TitleSaveCheckRunning", resident_phase, re.DOTALL) is None:
        failures.append("resident title-save boundary")
    if re.search(r"TitleSaveCheckRunning.*titleSaveCheck.*advanceAfterField", resident_phase, re.DOTALL) is None:
        failures.append("resident title-save resume")
    if failures:
        raise Refuse("shipping mismatch: " + ", ".join(failures))
    print(f"  [ ok ] native TITLE save-check facts: {len(expected)}/{len(expected)}")
    print("  [ ok ] whole caller split: every guest field wait returns to VagrantFrameDriver")


def selftest(title, resident, measured):
    print("== re_title_save selftest ==")
    checks = 0
    with open(FACTS, encoding="utf-8") as source:
        facts = source.read()
    with open(MEMCARD_FACTS, encoding="utf-8") as source:
        memcard_facts = source.read()
    with open(SOURCE, encoding="utf-8") as source:
        owner = source.read()
    with open(RESIDENT_PHASE, encoding="utf-8") as source:
        resident_phase = source.read()

    original = title.data
    mutated = bytearray(original)
    off = title.off(measured["owner"] + 0x5C)
    mutated[off : off + 4] = struct.pack("<I", 0)
    title.data = bytes(mutated)
    try:
        measure(title, resident, verify_identity=False)
        raise AssertionError("destroyed direct VSync was accepted")
    except Refuse as error:
        if "matched 0" not in str(error) or "scanned" not in str(error):
            raise AssertionError(f"destroyed VSync negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed direct VSync refused: {error}")
        checks += 1
    finally:
        title.data = original

    shifted = facts.replace(
        f"kOwner = 0x{measured['owner']:08X}u", f"kOwner = 0x{measured['owner'] + 4:08X}u", 1
    )
    try:
        check_source(measured, (shifted, memcard_facts, owner, resident_phase))
        raise AssertionError("shifted owner was accepted")
    except Refuse as error:
        print(f"  [ ok ] shifted owner refused: {error}")
        checks += 1

    reordered = owner.replace(
        "  services_.call0(core, title_save::kProcessCdQueue);\n  game_time::advance(core);",
        "  game_time::advance(core);\n  services_.call0(core, title_save::kProcessCdQueue);",
        1,
    )
    try:
        check_source(measured, (facts, memcard_facts, reordered, resident_phase))
        raise AssertionError("reordered gametime tail was accepted")
    except Refuse as error:
        print(f"  [ ok ] reordered gametime tail refused: {error}")
        checks += 1

    mutated = bytearray(original)
    mutated[0] ^= 1
    title.data = bytes(mutated)
    try:
        measure(title, resident)
        raise AssertionError("one-byte-mutated TITLE passed identity")
    except Refuse as error:
        if "sha1" not in str(error):
            raise AssertionError(f"identity negative did not name sha1: {error}")
        print(f"  [ ok ] one-byte-mutated TITLE refused: {error}")
        checks += 1
    finally:
        title.data = original
    print(f"== re_title_save selftest PASS ({checks}/4) ==")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("title", nargs="?", default=DEFAULT_TITLE)
    parser.add_argument("--resident", default=DEFAULT_EXE)
    parser.add_argument("--check-source", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    try:
        title = Overlay(args.title, TITLE_BASE, TITLE_SHA1)
        resident = Image(args.resident)
        measured = measure(title, resident)
        print("== TITLE save-file field-owner measurement ==")
        print(
            f"  owner 0x{measured['owner']:08X}; gametime 0x{measured['game_time_update']:08X}; "
            f"direct VSync 0x{measured['vsync']:08X}; scanned {measured['scanned']}"
        )
        print(
            f"  memcard init/event/shutdown 0x{measured['init_memcard']:08X}/"
            f"0x{measured['memcard_event_handler']:08X}/0x{measured['shutdown_memcard']:08X}"
        )
        if args.check_source:
            check_source(measured)
        if args.selftest:
            selftest(title, resident, measured)
    except (OSError, Refuse, AssertionError) as error:
        print(f"[re-title-save] REFUSED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Measure and gate TITLE's finite `_initMemcard` owner.

The SHA-bound overlay identifies both restricted disc extents, the complete pointer graph, the
SPMCIMG upload, and the eight-event lifecycle. Shipping source may replace the interrupt-driven CD
queue with finite reads of those exact extents; it may not fake queue state or weaken guest VSync.
"""

import argparse
import re
import struct
import sys

from re_crt0 import Refuse, s16
from re_frame import DEFAULT_TITLE, TITLE_BASE, TITLE_SHA1, Overlay
from re_spu_transfer import based_address, jal_target, unique_shape

FACTS = "game/save/title_memcard_facts.h"
SOURCE = "game/save/title_memcard_init.cpp"
SAVE_SOURCE = "game/save/title_save_check.cpp"


def unsigned_pair(hi_word, lo_word, reg):
    if hi_word >> 26 != 0x0F or (hi_word >> 16) & 31 != reg:
        raise Refuse(f"expected lui for register {reg}, found 0x{hi_word:08X}")
    if lo_word >> 26 != 0x0D or (lo_word >> 21) & 31 != reg or (lo_word >> 16) & 31 != reg:
        raise Refuse(f"expected ori for register {reg}, found 0x{lo_word:08X}")
    return ((hi_word & 0xFFFF) << 16) | (lo_word & 0xFFFF)


def copied_address(hi_word, lo_word, base_reg, destination_reg):
    if hi_word >> 26 != 0x0F or (hi_word >> 16) & 31 != base_reg:
        raise Refuse(f"expected lui for register {base_reg}, found 0x{hi_word:08X}")
    if (
        lo_word >> 26 not in (0x08, 0x09)
        or (lo_word >> 21) & 31 != base_reg
        or (lo_word >> 16) & 31 != destination_reg
    ):
        raise Refuse(
            f"expected addi/addiu from register {base_reg} to {destination_reg}, found 0x{lo_word:08X}"
        )
    return (((hi_word & 0xFFFF) << 16) + s16(lo_word & 0xFFFF)) & 0xFFFFFFFF


def measure(title, verify_identity=True):
    if verify_identity:
        title.check_identity()
    owner, scanned = unique_shape(
        title,
        "TITLE _initMemcard",
        {
            0x00: 0x27BDFFD8,
            0x04: 0xAFBF0024,
            0x0C: 0xAFB1001C,
            0x10: 0x10800025,
            0x18: 0x3C040001,
            0x20: 0x3484C000,
            0x2C: 0x3C070001,
            0x30: 0x34E74C98,
            0xA4: 0xA060C8C4,
            0x12C: 0x3C020001,
            0x130: 0x34424CD0,
            0x13C: 0x24022000,
            0x19C: 0x3C028007,
            0x1A0: 0x24522894,
            0x1C4: 0x24062000,
            0x1E8: 0x2A020008,
            0x214: 0x2A020008,
            0x21C: 0x24020001,
        },
    )
    calls = {
        "alloc_heap": jal_target(owner + 0x1C, title.r32(owner + 0x1C)),
        "allocate_queue": jal_target(owner + 0x7C, title.r32(owner + 0x7C)),
        "enqueue": jal_target(owner + 0x90, title.r32(owner + 0x90)),
        "free_queue": jal_target(owner + 0x100, title.r32(owner + 0x100)),
        "draw_image": jal_target(owner + 0x11C, title.r32(owner + 0x11C)),
        "enable_reset": jal_target(owner + 0x18C, title.r32(owner + 0x18C)),
        "enter_critical": jal_target(owner + 0x194, title.r32(owner + 0x194)),
        "open_event": jal_target(owner + 0x1DC, title.r32(owner + 0x1DC)),
        "exit_critical": jal_target(owner + 0x1F4, title.r32(owner + 0x1F4)),
        "enable_event": jal_target(owner + 0x20C, title.r32(owner + 0x20C)),
    }
    if jal_target(owner + 0x140, title.r32(owner + 0x140)) != calls["allocate_queue"]:
        raise Refuse("second extent no longer uses the first measured queue allocator")
    if jal_target(owner + 0x158, title.r32(owner + 0x158)) != calls["enqueue"]:
        raise Refuse("second extent no longer uses the first measured queue enqueue leaf")
    if jal_target(owner + 0x184, title.r32(owner + 0x184)) != calls["free_queue"]:
        raise Refuse("second extent no longer uses the first measured queue free leaf")

    spmcimg_size = unsigned_pair(title.r32(owner + 0x18), title.r32(owner + 0x20), 4)
    if unsigned_pair(title.r32(owner + 0x34), title.r32(owner + 0x38), 6) != spmcimg_size:
        raise Refuse("allocation size and first extent size no longer agree")
    mcdata_offset = unsigned_pair(title.r32(owner + 0x24), title.r32(owner + 0x28), 5)
    spmcimg_lba = unsigned_pair(title.r32(owner + 0x2C), title.r32(owner + 0x30), 7)
    mcdata_lba = unsigned_pair(title.r32(owner + 0x12C), title.r32(owner + 0x130), 2)
    second_size = title.r32(owner + 0x13C) & 0xFFFF

    spmcimg_pointer = based_address(title.r32(owner + 0x40), title.r32(owner + 0x48), 16)
    mcdata_pointer = based_address(title.r32(owner + 0x44), title.r32(owner + 0x54), 3)
    text_pointer = based_address(title.r32(owner + 0x50), title.r32(owner + 0x5C), 5)
    save_info_pointer = based_address(title.r32(owner + 0x60), title.r32(owner + 0x68), 5)
    directory_pointer = based_address(title.r32(owner + 0x6C), title.r32(owner + 0x74), 3)
    init_state = based_address(title.r32(owner + 0x9C), title.r32(owner + 0xA4), 3)
    event_specs = copied_address(title.r32(owner + 0x19C), title.r32(owner + 0x1A0), 2, 18)
    event_descriptors = copied_address(title.r32(owner + 0x1A4), title.r32(owner + 0x1A8), 2, 17)

    return {
        "owner": owner,
        "scanned": scanned,
        **calls,
        "spmcimg_lba": spmcimg_lba,
        "spmcimg_size": spmcimg_size,
        "mcdata_lba": mcdata_lba,
        "second_size": second_size,
        "mcdata_offset": mcdata_offset,
        "text_offset": title.r32(owner + 0x58) & 0xFFFF,
        "save_info_offset": title.r32(owner + 0x64) & 0xFFFF,
        "directory_offset": title.r32(owner + 0x70) & 0xFFFF,
        "spmcimg_pointer": spmcimg_pointer,
        "mcdata_pointer": mcdata_pointer,
        "text_pointer": text_pointer,
        "save_info_pointer": save_info_pointer,
        "directory_pointer": directory_pointer,
        "event_descriptors": event_descriptors,
        "event_specs": event_specs,
        "init_state": init_state,
        "image_xy": unsigned_pair(title.r32(owner + 0x108), title.r32(owner + 0x10C), 4),
        "image_wh": unsigned_pair(title.r32(owner + 0x110), title.r32(owner + 0x120), 6),
        "sw_event": unsigned_pair(title.r32(owner + 0x1AC), title.r32(owner + 0x1B8), 4),
        "hw_event": unsigned_pair(title.r32(owner + 0x1BC), title.r32(owner + 0x1C0), 4),
        "event_mode": title.r32(owner + 0x1C4) & 0xFFFF,
        "event_count": title.r32(owner + 0x1E8) & 0xFFFF,
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
        with open(SOURCE, encoding="utf-8") as source:
            owner = source.read()
        with open(SAVE_SOURCE, encoding="utf-8") as source:
            save_owner = source.read()
    else:
        facts, owner, save_owner = sources
    expected = {
        "kOwner": measured["owner"],
        "kAllocHeap": measured["alloc_heap"],
        "kAllocateCdQueueSlot": measured["allocate_queue"],
        "kFreeCdQueueSlot": measured["free_queue"],
        "kCdEnqueue": measured["enqueue"],
        "kDrawImage": measured["draw_image"],
        "kEnableReset": measured["enable_reset"],
        "kEnterCriticalSection": measured["enter_critical"],
        "kOpenEvent": measured["open_event"],
        "kExitCriticalSection": measured["exit_critical"],
        "kEnableEvent": measured["enable_event"],
        "kSpmcimgLba": measured["spmcimg_lba"],
        "kSpmcimgSize": measured["spmcimg_size"],
        "kMcdataLba": measured["mcdata_lba"],
        "kMcdataAndMcmanSize": measured["second_size"],
        "kMcdataOffset": measured["mcdata_offset"],
        "kTextTableOffset": measured["text_offset"],
        "kSaveFileInfoOffset": measured["save_info_offset"],
        "kDirectoryEntryOffset": measured["directory_offset"],
        "kSpmcimgPointer": measured["spmcimg_pointer"],
        "kMcdataPointer": measured["mcdata_pointer"],
        "kTextTablePointer": measured["text_pointer"],
        "kSaveFileInfoPointer": measured["save_info_pointer"],
        "kDirectoryEntryPointer": measured["directory_pointer"],
        "kEventDescriptors": measured["event_descriptors"],
        "kEventSpecs": measured["event_specs"],
        "kInitState": measured["init_state"],
        "kSpmcimgImageXy": measured["image_xy"],
        "kSpmcimgImageWh": measured["image_wh"],
        "kSwCardEvent": measured["sw_event"],
        "kHwCardEvent": measured["hw_event"],
        "kEventModeNoInterrupt": measured["event_mode"],
        "kEventCount": measured["event_count"],
    }
    failures = [name for name, want in expected.items() if source_constant(facts, name) != want]
    wiring = {
        "first finite extent": r"kAllocHeap.*kSpmcimgPointer.*kMcdataPointer.*kSpmcimgLba.*FirstExtentReady",
        "SPMCIMG upload boundary": r"finishFirstExtent.*kDrawImage.*kSpmcimgImageXy.*kSpmcimgImageWh.*SecondExtentReady",
        "second finite extent": r"finishSecondExtent.*kMcdataLba.*kMcdataAndMcmanSize.*EventSetupReady",
        "event lifecycle": r"kEnableReset.*kEnterCriticalSection.*kOpenEvent.*kEventDescriptors.*kExitCriticalSection.*kEnableEvent.*Complete",
    }
    for name, pattern in wiring.items():
        if re.search(pattern, owner, re.DOTALL) is None:
            failures.append(name)
    forbidden = ("kAllocateCdQueueSlot", "kFreeCdQueueSlot", "kCdEnqueue", "kVSync", "kProcessCdQueue")
    for name in forbidden:
        if name in owner:
            failures.append(f"retired guest boundary {name}")
    if "title_memcard::kOwner" not in save_owner:
        failures.append("save-check does not call the finite init owner")
    if failures:
        raise Refuse("shipping mismatch: " + ", ".join(failures))
    print(f"  [ ok ] native TITLE memcard facts: {len(expected)}/{len(expected)}")
    print("  [ ok ] finite extents + pointer/image/event state; guest queue absent")


def selftest(title, measured):
    print("== re_title_memcard selftest ==")
    with open(FACTS, encoding="utf-8") as source:
        facts = source.read()
    with open(SOURCE, encoding="utf-8") as source:
        owner = source.read()
    with open(SAVE_SOURCE, encoding="utf-8") as source:
        save_owner = source.read()
    checks = 0

    original = title.data
    mutated = bytearray(original)
    offset = title.off(measured["owner"] + 0x30)
    mutated[offset : offset + 4] = struct.pack("<I", 0)
    title.data = bytes(mutated)
    try:
        measure(title, verify_identity=False)
        raise AssertionError("destroyed first extent was accepted")
    except Refuse as error:
        if "matched 0" not in str(error) or "scanned" not in str(error):
            raise AssertionError(f"destroyed extent negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed first extent refused: {error}")
        checks += 1
    finally:
        title.data = original

    shifted = facts.replace(
        f"kSpmcimgLba = 0x{measured['spmcimg_lba']:08X}u",
        f"kSpmcimgLba = 0x{measured['spmcimg_lba'] + 1:08X}u",
        1,
    )
    try:
        check_source(measured, (shifted, owner, save_owner))
        raise AssertionError("shifted SPMCIMG extent was accepted")
    except Refuse as error:
        print(f"  [ ok ] shifted SPMCIMG extent refused: {error}")
        checks += 1

    queued = owner.replace(
        "  state_ = TitleMemcardInitState::FirstExtentReady;",
        "  services_.call0(core, title_memcard::kCdEnqueue);\n  state_ = TitleMemcardInitState::FirstExtentReady;",
        1,
    )
    try:
        check_source(measured, (facts, queued, save_owner))
        raise AssertionError("retired queue call was accepted")
    except Refuse as error:
        print(f"  [ ok ] retired queue call refused: {error}")
        checks += 1

    mutated = bytearray(original)
    mutated[0] ^= 1
    title.data = bytes(mutated)
    try:
        measure(title)
        raise AssertionError("one-byte-mutated TITLE passed identity")
    except Refuse as error:
        if "sha1" not in str(error):
            raise AssertionError(f"identity negative did not name sha1: {error}")
        print(f"  [ ok ] one-byte-mutated TITLE refused: {error}")
        checks += 1
    finally:
        title.data = original
    print(f"== re_title_memcard selftest PASS ({checks}/4) ==")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("title", nargs="?", default=DEFAULT_TITLE)
    parser.add_argument("--check-source", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    try:
        title = Overlay(args.title, TITLE_BASE, TITLE_SHA1)
        measured = measure(title)
        print("== TITLE finite memcard-init measurement ==")
        print(
            f"  owner 0x{measured['owner']:08X}; SPMCIMG ({measured['spmcimg_lba']},0x{measured['spmcimg_size']:X}); "
            f"MCDATA+MCMAN ({measured['mcdata_lba']},0x{measured['second_size']:X}); scanned {measured['scanned']}"
        )
        print(
            f"  globals spmcimg/mcdata/events 0x{measured['spmcimg_pointer']:08X}/"
            f"0x{measured['mcdata_pointer']:08X}/0x{measured['event_descriptors']:08X}"
        )
        if args.check_source:
            check_source(measured)
        if args.selftest:
            selftest(title, measured)
    except (OSError, Refuse, AssertionError) as error:
        print(f"[re-title-memcard] REFUSED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Classify TITLE's natural/skip movie exits and their shared menu continuation.

This instrument answers one narrow question from issue #26: does the retail program select a
different title/menu path from `_playIntroMovie`'s return value when the movie ends naturally?
It reuses `re_title_movie`'s independently measured playback owner, decodes both exit conditions
from the SHA-bound TITLE.PRG, finds every call to that owner, and proves that the sole caller uses
neither return value before entering one common title/menu initialization chain.

It deliberately does not diagnose the remaining black composite. The result narrows that bug to
state/timing/render ownership carried across movie teardown, rather than a caller-side branch.
"""

import struct
import sys

from re_crt0 import Refuse, s16
from re_frame import DEFAULT_TITLE, TITLE_BASE, TITLE_SHA1, Overlay, jal_word
from re_spu_transfer import jal_target
from re_title_movie import measure as measure_movie

SET_DISP_MASK = 0x800285B8


def branch_target(pc, word):
    if word >> 26 not in (0x04, 0x05):
        raise Refuse(f"expected conditional branch at 0x{pc:08X}, found 0x{word:08X}")
    return (pc + 4 + (s16(word & 0xFFFF) << 2)) & 0xFFFFFFFF


def unique_word(title, name, start, stop, predicate):
    matches = [pc for pc in range(start, stop, 4) if predicate(pc, title.r32(pc))]
    scanned = max(0, (stop - start) // 4)
    if len(matches) != 1:
        shown = ", ".join(f"0x{pc:08X}" for pc in matches[:8]) or "none"
        raise Refuse(
            f"{name}: scanned {scanned} word-aligned candidates, matched {len(matches)} "
            f"({shown}); cannot identify a unique instruction"
        )
    return matches[0], scanned


def measure(title, verify_identity=True):
    if verify_identity:
        title.check_identity()

    # Reuse the existing movie instrument's owner rather than defining a second signature for the
    # same function. Its callback/display checks establish the function's identity independently.
    movie = measure_movie(title, verify_identity=False)
    play = movie["play_owner"]
    function_stop = play + 0x1DC

    # Natural completion is the sole `sltiu v0,v0,<ticks>` in the measured owner. Its following
    # `beq v0,zero` returns v0=0 in the delay slot. Parse the immediate instead of keeping a second
    # copy of the answer here: the self-test changes it and requires the measured answer to move.
    natural_test, natural_scanned = unique_word(
        title,
        "TITLE natural movie-end timer",
        play,
        function_stop,
        lambda pc, word: word >> 26 == 0x0B
        and (word >> 21) & 31 == 2
        and (word >> 16) & 31 == 2
        and title.r32(pc + 4) >> 26 == 0x04
        and title.r32(pc + 8) == 0x00001021,
    )
    natural_branch = natural_test + 4
    natural_branch_word = title.r32(natural_branch)
    if (
        natural_branch_word >> 26 != 0x04
        or (natural_branch_word >> 21) & 31 != 2
        or (natural_branch_word >> 16) & 31 != 0
        or title.r32(natural_branch + 4) != 0x00001021
    ):
        raise Refuse(
            f"natural timer at 0x{natural_test:08X} does not branch on v0==0 with return v0=0"
        )
    natural_exit = branch_target(natural_branch, natural_branch_word)

    # The input exit is the sole `andi v0,v0,<mask>` in this owner. No-button loops backward; the
    # delay slot sets v0=1, and pressed input falls through to the instruction after that slot.
    input_test, input_scanned = unique_word(
        title,
        "TITLE intro-skip input mask",
        play,
        function_stop,
        lambda _pc, word: word >> 26 == 0x0C
        and (word >> 21) & 31 == 2
        and (word >> 16) & 31 == 2,
    )
    input_branch = input_test + 4
    input_branch_word = title.r32(input_branch)
    input_return_word = title.r32(input_branch + 4)
    if (
        input_branch_word >> 26 != 0x04
        or (input_branch_word >> 21) & 31 != 2
        or (input_branch_word >> 16) & 31 != 0
        or input_return_word >> 26 != 0x09
        or (input_return_word >> 21) & 31 != 0
        or (input_return_word >> 16) & 31 != 2
    ):
        raise Refuse(
            f"input mask at 0x{input_test:08X} does not loop on v0==0 with an immediate v0 return"
        )
    input_exit = input_branch + 8
    if natural_exit != input_exit:
        raise Refuse(
            f"movie exits diverge: natural -> 0x{natural_exit:08X}, input -> 0x{input_exit:08X}"
        )

    # Find all callers across the entire overlay. There is exactly one. On return, its very next
    # instruction is another jal: no instruction reads or branches on v0. The following fixed SDK
    # SetDispMask(1) call and menu-init call establish that this is the title transition chain.
    wanted = jal_word(play)
    callers = [
        pc
        for pc in range(title.lo, title.hi - 4, 4)
        if title.r32(pc) == wanted
    ]
    caller_scanned = (title.hi - title.lo) // 4
    if len(callers) != 1:
        shown = ", ".join(f"0x{pc:08X}" for pc in callers[:8]) or "none"
        raise Refuse(
            f"TITLE playback callers: scanned {caller_scanned} words, matched {len(callers)} "
            f"({shown}); return ownership is ambiguous"
        )
    call = callers[0]
    if title.r32(call + 4) != 0:
        raise Refuse(f"playback call delay slot at 0x{call + 4:08X} is not nop")
    init_screen = jal_target(call + 8, title.r32(call + 8))
    if title.r32(call + 12) != 0:
        raise Refuse(f"title-screen initialization delay slot at 0x{call + 12:08X} is not nop")
    if jal_target(call + 16, title.r32(call + 16)) != SET_DISP_MASK:
        raise Refuse(f"shared transition at 0x{call:08X} does not call SetDispMask")
    if title.r32(call + 20) != 0x24040001:
        raise Refuse(f"shared transition does not call SetDispMask(1)")
    init_menu = jal_target(call + 24, title.r32(call + 24))

    return {
        "play_owner": play,
        "natural_test": natural_test,
        "natural_ticks": title.r32(natural_test) & 0xFFFF,
        "natural_return": 0,
        "input_test": input_test,
        "input_mask": title.r32(input_test) & 0xFFFF,
        "input_return": s16(input_return_word & 0xFFFF),
        "common_epilogue": natural_exit,
        "caller": call,
        "init_screen": init_screen,
        "init_menu": init_menu,
        "natural_scanned": natural_scanned,
        "input_scanned": input_scanned,
        "caller_scanned": caller_scanned,
    }


def selftest(title, measured):
    print("== re_title_natural selftest ==")
    checks = 0
    original = title.data

    # A measuring instrument must show the other answer, not merely reject all unfamiliar input.
    mutable = bytearray(original)
    offset = title.off(measured["natural_test"])
    changed_ticks = measured["natural_ticks"] + 1
    mutable[offset : offset + 4] = struct.pack("<I", 0x2C420000 | changed_ticks)
    title.data = bytes(mutable)
    changed = measure(title, verify_identity=False)
    if changed["natural_ticks"] != changed_ticks:
        raise AssertionError("changed natural threshold did not change the measured answer")
    print(
        f"  [ ok ] changed timer produced the other answer: "
        f"{measured['natural_ticks']} -> {changed['natural_ticks']} ticks"
    )
    checks += 1
    title.data = original

    mutable = bytearray(original)
    offset = title.off(measured["caller"] + 8)
    mutable[offset : offset + 4] = struct.pack("<I", 0)
    title.data = bytes(mutable)
    try:
        measure(title, verify_identity=False)
        raise AssertionError("destroyed shared title continuation was accepted")
    except Refuse as error:
        if "expected jal" not in str(error):
            raise AssertionError(f"continuation negative did not name destroyed jal: {error}")
        print(f"  [ ok ] destroyed common continuation refused: {error}")
        checks += 1
    finally:
        title.data = original

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

    print(f"== re_title_natural selftest PASS ({checks}/3) ==")


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    do_selftest = "--selftest" in args
    args = [arg for arg in args if arg != "--selftest"]
    if len(args) > 1:
        print("usage: re_title_natural.py [--selftest] [TITLE.PRG]", file=sys.stderr)
        return 2
    try:
        title = Overlay(args[0] if args else DEFAULT_TITLE, TITLE_BASE, TITLE_SHA1)
        measured = measure(title)
        print("== Vagrant TITLE natural/skip transition ==")
        print(
            f"  playback owner 0x{measured['play_owner']:08X}: natural >= "
            f"{measured['natural_ticks']} VSync ticks returns {measured['natural_return']}; "
            f"input mask 0x{measured['input_mask']:X} returns {measured['input_return']}"
        )
        print(
            f"  both exits enter epilogue 0x{measured['common_epilogue']:08X}; sole caller "
            f"0x{measured['caller']:08X} ignores v0"
        )
        print(
            f"  common continuation: init title screen 0x{measured['init_screen']:08X}, "
            f"SetDispMask(1), init menu 0x{measured['init_menu']:08X}"
        )
        print(
            f"  denominators: natural {measured['natural_scanned']} words, input "
            f"{measured['input_scanned']} words, callers {measured['caller_scanned']} words"
        )
        if do_selftest:
            selftest(title, measured)
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_title_natural REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

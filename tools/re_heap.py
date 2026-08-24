#!/usr/bin/env python3
"""Measure Vagrant Story's own heap initialiser and its free-list control blocks.

RE-07's supply instrument: the first native body seeded from the matching decomp
(external/rood-reverse, CC0 — `vs_main_initHeap`) is gated here against OUR bytes. Nothing may be
imported merely because the reference names it, so this tool derives every shipped constant from the
owned executable: it finds the unique arena-argument call site by its immediate shape, decodes the
callee's store sequence to locate the two free-list heads, and diffs game/core/game_heap.{h,cpp}
back to that measurement. rood-reverse's symbol names are printed only as corroboration.
"""

import os
import re
import struct
import sys

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAP_HDR = os.path.join(ROOT, "game", "core", "game_heap.h")
HEAP_SRC = os.path.join(ROOT, "game", "core", "game_heap.cpp")
ROOD_SYMBOLS = os.path.join(
    ROOT, "external", "rood-reverse", "config", "SLUS_010.40", "symbol_addrs.txt"
)

# The unique caller materialises (a0=0x8010C000, a1=0xF2000) in three lui/ori pairs around the jal.
ARENA_HI = 0x8010
ARENA_LO = 0xC000
SIZE_HI = 0x000F
SIZE_LO = 0x2000


def words(img):
    for va in range(img.lo, img.hi, 4):
        yield va, img.r32(va)


def jal_target(pc, word):
    if word >> 26 != 3:
        raise Refuse(f"expected jal at 0x{pc:08X}, found raw word 0x{word:08X}")
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def find_call_sequence(img):
    """Find `lui a0,hi / ori a0,a0,lo / lui a1,sizeHi / jal X / ori a1,a1,sizeLo` by immediates."""
    matches = []
    scanned = 0
    for va, w in words(img):
        if va + 16 >= img.hi:
            break
        scanned += 1
        if w != (0x0F << 26) | (4 << 16) | ARENA_HI:  # lui a0, arena_hi
            continue
        if img.r32(va + 4) != (0x0D << 26) | (4 << 21) | (4 << 16) | ARENA_LO:  # ori a0, a0, lo
            continue
        if img.r32(va + 8) != (0x0F << 26) | (5 << 16) | SIZE_HI:  # lui a1, size_hi
            continue
        if img.r32(va + 12) >> 26 != 3:  # jal (delay slot carries the size low bits)
            continue
        if img.r32(va + 16) != (0x0D << 26) | (5 << 21) | (5 << 16) | SIZE_LO:
            continue
        matches.append(va)
    if len(matches) != 1:
        shown = ", ".join(f"0x{x:08X}" for x in matches[:8]) or "none"
        raise Refuse(
            f"heap call sequence: scanned {scanned} word-aligned candidates, matched {len(matches)} "
            f"({shown}); cannot identify a unique arena-argument call"
        )
    return matches[0], scanned


def sw_word(rt, off, base):
    return (0x2B << 26) | (base << 21) | (rt << 16) | (off & 0xFFFF)


def measure(img, verify_identity=True):
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(
            f"{img.path}: sha1 {img.sha1()} != SLUS_010.40 {FIXTURE_SHA1}; nothing was measured"
        )

    sequence, scanned = find_call_sequence(img)
    call_site = sequence + 12
    init_heap = jal_target(call_site, img.r32(call_site))
    arena_base = (ARENA_HI << 16) | ARENA_LO
    arena_size = (SIZE_HI << 16) | SIZE_LO

    # The callee must open with `lui v0,seg` + `sw a0,offA(v0)`; its own stores then name both
    # free-list heads. Every offset below is DERIVED, never assumed.
    prologue = img.r32(init_heap)
    if prologue >> 26 != 0x0F or ((prologue >> 16) & 0x1F) != 2:
        raise Refuse(
            f"heap init 0x{init_heap:08X}: expected `lui v0,seg` first, found 0x{prologue:08X}"
        )
    seg = (prologue & 0xFFFF) << 16
    store_a = img.r32(init_heap + 4)
    if store_a & 0xFFFF0000 != sw_word(4, 0, 2) & 0xFFFF0000 or (store_a & 0xFFFF) < 0x100:
        raise Refuse(
            f"heap init 0x{init_heap:08X}: expected `sw a0,off(v0)` second, found 0x{store_a:08X}"
        )
    control_a = seg + (store_a & 0xFFFF)

    # Capacity encoding value/16-1 immediately after the link store pair.
    if img.r32(init_heap + 0xC) != 0x00052902:  # srl a1, a1, 4
        raise Refuse(
            f"heap init 0x{init_heap:08X}: expected `srl a1,a1,4` at +0xC, "
            f"found 0x{img.r32(init_heap + 0xC):08X}"
        )
    if img.r32(init_heap + 0x10) != (0x09 << 26) | (5 << 21) | (5 << 16) | 0xFFFF:  # addiu a1,-1
        raise Refuse(
            f"heap init 0x{init_heap:08X}: expected `addiu a1,a1,-1` at +0x10, "
            f"found 0x{img.r32(init_heap + 0x10):08X}"
        )

    # `lui v1,seg` then the head-B derivation from `addiu v0,v1,offB`.
    lui_v1 = img.r32(init_heap + 0x14)
    if lui_v1 >> 26 != 0x0F or ((lui_v1 >> 16) & 0x1F) != 3 or (lui_v1 & 0xFFFF) << 16 != seg:
        raise Refuse(
            f"heap init 0x{init_heap:08X}: expected `lui v1,{seg >> 16:#x}` at +0x14, "
            f"found 0x{lui_v1:08X}"
        )
    addiu_b = img.r32(init_heap + 0x28)
    if (
        addiu_b >> 26 != 0x09
        or ((addiu_b >> 21) & 0x1F) != 3
        or ((addiu_b >> 16) & 0x1F) != 2
    ):
        raise Refuse(
            f"heap init 0x{init_heap:08X}: expected `addiu v0,v1,offB` at +0x28, "
            f"found 0x{addiu_b:08X}"
        )
    control_b = seg + (addiu_b & 0xFFFF)

    # The remaining stores of the measured body, in order: head-A next/blockSz, node links,
    # node capacity, head-B self-links. The compiler returns through `jr` with the FINAL store
    # (head B.blockSz = 0) in the delay slot.
    expected = [
        (init_heap + 0x18, sw_word(4, 4, 2)),   # sw a0,4(v0)      head A.next = node
        (init_heap + 0x1C, sw_word(0, 8, 2)),   # sw zero,8(v0)    head A.blockSz = 0
        (init_heap + 0x20, sw_word(2, 0, 4)),   # sw v0,0(a0)      node.prev = head A
        (init_heap + 0x24, sw_word(2, 4, 4)),   # sw v0,4(a0)      node.next = head A
        (init_heap + 0x2C, sw_word(5, 8, 4)),   # sw a1,8(a0)      node.blockSz
        (init_heap + 0x30, sw_word(2, addiu_b & 0xFFFF, 3)),  # sw v0,offB(v1)
        (init_heap + 0x34, sw_word(2, 4, 2)),   # sw v0,4(v0)      head B.next
        (init_heap + 0x38, 0x03E00008),         # jr ra            (store below is in its slot)
        (init_heap + 0x3C, sw_word(0, 8, 2)),   # sw zero,8(v0)    head B.blockSz = 0
    ]
    for addr, want in expected:
        got = img.r32(addr)
        if got != want:
            raise Refuse(
                f"heap init 0x{init_heap:08X}: store-sequence mismatch at 0x{addr:08X}: "
                f"0x{got:08X} != expected 0x{want:08X}"
            )

    # Exactly one caller: no other code enters the allocator initialiser.
    jal = (3 << 26) | (((init_heap >> 2) - (0x80000000 >> 2)) & 0x03FFFFFF)
    callers = [va for va, w in words(img) if w == jal]
    if len(callers) != 1 or callers[0] != call_site:
        shown = ", ".join(f"0x{x:08X}" for x in callers[:8]) or "none"
        raise Refuse(
            f"callers of 0x{init_heap:08X}: scanned the full text, found {len(callers)} ({shown}); "
            "expected exactly the one measured call site"
        )

    return {
        "sequence": sequence,
        "call_site": call_site,
        "init_heap": init_heap,
        "control_a": control_a,
        "control_b": control_b,
        "segment": seg,
        "arena_base": arena_base,
        "arena_size": arena_size,
        "scanned": scanned,
    }


def rood_corroboration(measured):
    """Print rood-reverse's independent labels where they agree. Labels, never evidence."""
    if not os.path.isfile(ROOD_SYMBOLS):
        print("  [info] rood-reverse symbol_addrs.txt not present; no corroboration printed")
        return
    wanted = {
        "vs_main_initHeap": measured["init_heap"],
        "heapA": measured["control_a"],
        "heapB": measured["control_b"],
    }
    seen = {}
    with open(ROOD_SYMBOLS) as symbols:
        for line in symbols:
            m = re.match(r"^(\w+)\s*=\s*(0x[0-9A-Fa-f]+)", line)
            if m and m.group(1) in wanted:
                seen[m.group(1)] = int(m.group(2), 16)
    for name, ours in wanted.items():
        theirs = seen.get(name)
        if theirs is None:
            print(f"  [info] rood has no label for {name}")
        elif theirs == ours:
            print(f"  [info] rood label {name} = 0x{theirs:08X} agrees with the measurement")
        else:
            print(
                f"  [WARN] rood label {name} = 0x{theirs:08X} DISAGREES with the measurement "
                f"0x{ours:08X}; the measurement stands"
            )


def parse_constant(text, path, name):
    m = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+|[0-9]+)u?", text)
    if not m:
        raise Refuse(f"{path}: did not find {name}; cannot compare shipping heap facts")
    return int(m.group(1), 0)


def read_sources():
    return "\n".join(open(path).read() for path in (HEAP_HDR, HEAP_SRC))


def check_source(measured, text):
    fields = {
        "kInitHeap": "init_heap",
        "kControlA": "control_a",
        "kControlB": "control_b",
        "kArenaBase": "arena_base",
        "kArenaSize": "arena_size",
    }
    failures = []
    for constant, key in fields.items():
        got, want = parse_constant(text, HEAP_HDR, constant), measured[key]
        ok = got == want
        print(f"  [{'ok' if ok else 'FAIL':>4}] {constant} shipped=0x{got:08X} measured=0x{want:08X}")
        if not ok:
            failures.append(constant)
    if "overrides::install(kInitHeap" not in text:
        failures.append("registry install at kInitHeap")
    if "gen_func_80043F74" not in text:
        failures.append("substrate gen pairing")
    if failures:
        raise Refuse("shipping mismatch: " + ", ".join(failures))


def selftest(img, measured):
    print("== re_heap selftest ==")
    checks = 0
    check_source(measured, read_sources())
    checks += 1

    original = img.data

    mutable = bytearray(original)
    mutable[img.off(measured["sequence"])] = 0  # destroy `lui a0,arena_hi` -> nop
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError("destroyed arena call-site shape was accepted")
    except Refuse as e:
        if "scanned" not in str(e) or "matched 0" not in str(e):
            raise AssertionError(f"negative lacked denominator: {e}")
        print(f"  [ ok ] destroyed call site refused: {e}")
        checks += 1
    finally:
        img.data = original

    mutable = bytearray(original)
    off = img.off(measured["init_heap"] + 0xC)  # destroy the capacity encoding srl a1,a1,4
    mutable[off : off + 4] = struct.pack("<I", 0)
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError("destroyed capacity shift was accepted")
    except Refuse as e:
        if "+0xC" not in str(e):
            raise AssertionError(f"shift negative did not name +0xC: {e}")
        print(f"  [ ok ] destroyed capacity shift refused: {e}")
        checks += 1
    finally:
        img.data = original

    mutable = bytearray(original)
    jal_word = img.r32(measured["call_site"])
    off = img.off(img.hi) - 4  # the census's last-scanned word; step back if it already matches
    while struct.unpack_from("<I", mutable, off)[0] == jal_word:
        off -= 4
    mutable[off : off + 4] = struct.pack("<I", jal_word)
    if struct.unpack_from("<I", mutable, off)[0] != jal_word:
        raise AssertionError("caller-duplication mutation did not land")
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError("duplicated caller was accepted")
    except Refuse as e:
        if "callers of" not in str(e):
            raise AssertionError(f"caller negative did not name the census: {e}")
        print(f"  [ ok ] duplicated caller refused: {e}")
        checks += 1
    finally:
        img.data = original

    text = read_sources()
    changed = text.replace(
        f"kControlA = 0x{measured['control_a']:08X}",
        f"kControlA = 0x{measured['control_a'] + 4:08X}",
        1,
    )
    if changed == text:
        raise AssertionError("shipping mutation anchor did not fire")
    try:
        check_source(measured, changed)
        raise AssertionError("+4 shipping control block was accepted")
    except Refuse as e:
        if "kControlA" not in str(e):
            raise AssertionError(f"shipping negative did not name kControlA: {e}")
        print(f"  [ ok ] +4 shipping control block refused: {e}")
        checks += 1

    print(f"re_heap selftest: {checks}/5 PASS")


def main(argv):
    args = list(argv)
    do_check = "--check-source" in args
    do_selftest = "--selftest" in args
    args = [a for a in args if a not in ("--check-source", "--selftest")]
    if len(args) > 1:
        print(
            "usage: re_heap.py [--check-source] [--selftest] [SLUS_010.40]",
            file=sys.stderr,
        )
        return 2
    try:
        img = Image(args[0] if args else DEFAULT_EXE)
        m = measure(img)
        print("== Vagrant own-allocator seam (RE-07) ==")
        print(
            f"  arena-argument sequence 0x{m['sequence']:08X}; jal call site "
            f"0x{m['call_site']:08X} -> vs_main_initHeap 0x{m['init_heap']:08X} "
            f"({m['scanned']} candidates scanned)"
        )
        print(
            f"  free-list heads 0x{m['control_a']:08X}, 0x{m['control_b']:08X} "
            f"(segment 0x{m['segment']:08X})"
        )
        print(f"  arena 0x{m['arena_base']:08X}+0x{m['arena_size']:X} handed at the sole caller")
        print(
            "  boundary: ownership covers this initialiser alone; alloc/free callers stay on the "
            "substrate until their own RE step"
        )
        rood_corroboration(m)
        if do_check:
            check_source(m, read_sources())
        if do_selftest:
            selftest(img, m)
        return 0
    except (Refuse, OSError, AssertionError) as e:
        print(f"re_heap REFUSED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

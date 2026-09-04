#!/usr/bin/env python3
"""Measure Vagrant's synchronous libds/platform-CD ownership seam from the owned PS-EXE.

The retained native handler owns DsControlB's semantic control-command boundary. Ordinary guest
execution, including CD_sync, belongs to the future dynarec adapter. Async commands, callbacks,
query results, reads, and XA remain guest-owned.

Negative-first contract: a missing/wrong image, a non-unique ABI shape, a broken live call chain,
or a shipped address that differs from the measurement is a named refusal.  Silence is impossible.
"""

import os
import re
import struct
import sys
from pathlib import Path

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = os.path.join(ROOT, "game", "cd", "ds_control.cpp")
FACTS = os.path.join(ROOT, "game", "cd", "cd_facts.h")


def words(img):
    for va in range(img.lo, img.hi, 4):
        yield va, img.r32(va)


def unique_shape(img, name, shape):
    matches = []
    scanned = 0
    for va, _ in words(img):
        if va + max(shape) + 4 > img.hi:
            break
        scanned += 1
        if all(img.r32(va + off) == word for off, word in shape.items()):
            matches.append(va)
    if len(matches) != 1:
        shown = ", ".join(f"0x{x:08X}" for x in matches[:8]) or "none"
        raise Refuse(
            f"{name}: scanned {scanned} word-aligned candidates, matched {len(matches)} "
            f"({shown}); cannot identify a unique {name} ABI shape"
        )
    return matches[0], scanned


def jal_target(pc, word):
    if word >> 26 != 3:
        raise Refuse(f"expected jal at 0x{pc:08X}, found raw word 0x{word:08X}")
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def measure(img, verify_identity=True):
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(
            f"{img.path}: sha1 {img.sha1()} != SLUS_010.40 {FIXTURE_SHA1}; "
            "nothing was measured"
        )

    # _diskReset is found by its two blocking commands (Pause=9, Setmode=14) calling the same
    # wrapper.  The address is not an input to the search.
    disk_reset, disk_scanned = unique_shape(
        img,
        "_diskReset",
        {
            0x0C: 0x24040009,
            0x10: 0x00002821,
            0x18: 0x00A03021,
            0x1C: 0x1040FFFC,
            0x20: 0x24040009,
            0x54: 0x2404000E,
            0x60: 0x00003021,
            0x64: 0x1040FFFC,
            0x68: 0x2404000E,
        },
    )
    ds_control_b = jal_target(disk_reset + 0x14, img.r32(disk_reset + 0x14))
    if jal_target(disk_reset + 0x5C, img.r32(disk_reset + 0x5C)) != ds_control_b:
        raise Refuse(
            "_diskReset: Pause and Setmode do not call the same blocking control wrapper"
        )

    # DsControlB itself proves the public libds contract: enqueue via DsCommand, poll DsSync,
    # return true exactly for DslComplete (2).  These offsets are verified raw instructions.
    expected = {
        0x0C: 0x308400FF,
        0x10: 0x00003021,
        0x14: 0x00003821,
        0x28: 0x16000003,
        0x40: 0x304200FF,
        0x44: 0x1040FFFC,
        0x4C: 0x38420002,
        0x50: 0x2C420001,
    }
    bad = [
        (off, img.r32(ds_control_b + off), want)
        for off, want in expected.items()
        if img.r32(ds_control_b + off) != want
    ]
    if bad:
        off, got, want = bad[0]
        raise Refuse(
            f"DsControlB 0x{ds_control_b:08X}: contract mismatch at +0x{off:X}: "
            f"0x{got:08X} != 0x{want:08X}"
        )
    ds_command = jal_target(ds_control_b + 0x1C, img.r32(ds_control_b + 0x1C))
    ds_sync = jal_target(ds_control_b + 0x38, img.r32(ds_control_b + 0x38))

    # CD_cw is the unique low-level command ABI in this image: it preserves a1/a2/a3/a0 as
    # s0/s6/s2/s1 and indexes command tables by the low command byte.  This is exactly the ABI of
    # psxport's generic cd_command handler.
    cd_command, command_scanned = unique_shape(
        img,
        "CD_cw(com,param,result,mode)",
        {
            0x10: 0x00A08021,
            0x18: 0x00C0B021,
            0x20: 0x00E09021,
            0x28: 0x00808821,
            0x44: 0x322200FF,
            0x48: 0x00021080,
        },
    )

    # CD_sync uniquely preserves a0/a1 in s6/s7 and is the primitive reached by the helper called
    # at DsSync+0x20.  The helper relation prevents a merely similar two-argument function passing.
    cd_sync, sync_scanned = unique_shape(
        img,
        "CD_sync(mode,result)",
        {
            0x00: 0x27BDFFC0,
            0x04: 0xAFB60030,
            0x08: 0x0080B021,
            0x0C: 0xAFB70034,
            0x10: 0x00A0B821,
        },
    )
    sync_helper = jal_target(ds_sync + 0x1C, img.r32(ds_sync + 0x1C))
    helper_calls = [
        jal_target(sync_helper + off, img.r32(sync_helper + off))
        for off in range(0, 0x30, 4)
        if img.r32(sync_helper + off) >> 26 == 3
    ]
    if cd_sync not in helper_calls:
        shown = ", ".join(f"0x{x:08X}" for x in helper_calls) or "none"
        raise Refuse(
            f"DsSync helper 0x{sync_helper:08X}: scanned 12 instructions; calls {shown}, "
            f"not measured CD_sync 0x{cd_sync:08X}"
        )

    return {
        "diskReset": disk_reset,
        "DsControlB": ds_control_b,
        "DsCommand": ds_command,
        "DsSync": ds_sync,
        "CD_cw": cd_command,
        "CD_sync": cd_sync,
        "disk_scanned": disk_scanned,
        "command_scanned": command_scanned,
        "sync_scanned": sync_scanned,
    }


def check_source(measured, sources=None):
    if sources is None:
        sources = {
            path: Path(path).read_text(encoding="utf-8")
            for path in (OWNER, FACTS)
        }
    owner, facts = (sources[path] for path in (OWNER, FACTS))
    m = re.search(r"kDsControlB\s*=\s*(0x[0-9A-Fa-f]+)", facts)
    if not m:
        raise Refuse(
            f"{FACTS}: did not find kDsControlB; cannot compare shipping owner"
        )
    got, want = int(m.group(1), 0), measured["DsControlB"]
    ok = got == want
    print(
        f"  [{'ok' if ok else 'FAIL':>4}] DsControlB shipped=0x{got:08X} measured=0x{want:08X}"
    )
    if not ok:
        raise Refuse("shipping mismatch: DsControlB")
    m = re.search(r"kCdSync\s*=\s*(0x[0-9A-Fa-f]+)", facts)
    if not m:
        raise Refuse(f"{FACTS}: did not find kCdSync; cannot compare shipping HLE leaf")
    got, want = int(m.group(1), 0), measured["CD_sync"]
    ok = got == want
    print(
        f"  [{'ok' if ok else 'FAIL':>4}] CD_sync shipped=0x{got:08X} measured=0x{want:08X}"
    )
    if not ok:
        raise Refuse("shipping mismatch: CD_sync")
    m = re.search(r"kCdCommand\s*=\s*(0x[0-9A-Fa-f]+)", facts)
    if not m:
        raise Refuse(
            f"{FACTS}: did not find kCdCommand; cannot compare shipping HLE leaf"
        )
    got, want = int(m.group(1), 0), measured["CD_cw"]
    ok = got == want
    print(
        f"  [{'ok' if ok else 'FAIL':>4}] CD_cw shipped=0x{got:08X} measured=0x{want:08X}"
    )
    if not ok:
        raise Refuse("shipping mismatch: CD_cw")
    if re.search(r"void\s+vagrant::cd::handleDsControlB\s*\(\s*Core\s*&core\s*\)", owner) is None:
        raise Refuse(f"{OWNER}: retained semantic handler is absent")
    print("  [ ok ] retained DsControlB semantic handler")


def selftest(img, measured):
    checks = 0
    print("== re_cd selftest ==")
    check_source(measured)
    checks += 1

    # Negative 1: mutate the unique command ABI in the corpus. The shipping measurement must refuse
    # and print its denominator, not return an empty answer.
    original = img.data
    mutable = bytearray(original)
    off = img.off(measured["CD_cw"] + 0x10)
    mutable[off : off + 4] = struct.pack("<I", 0)
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError("destroyed CD_cw ABI was accepted")
    except Refuse as e:
        if "scanned" not in str(e) or "matched 0" not in str(e):
            raise AssertionError(f"negative lacked denominator: {e}")
        print(f"  [ ok ] destroyed CD_cw ABI refused: {e}")
        checks += 1
    finally:
        img.data = original

    # Negative 2: a plausible +4 hand-edit of the shipping field must be named.
    sources = {
        path: Path(path).read_text(encoding="utf-8") for path in (OWNER, FACTS)
    }
    changed = sources[FACTS].replace(
        f"kDsControlB = 0x{measured['DsControlB']:08X}",
        f"kDsControlB = 0x{measured['DsControlB'] + 4:08X}",
        1,
    )
    if changed == sources[FACTS]:
        raise AssertionError("owner mutation anchor did not fire")
    sources[FACTS] = changed
    try:
        check_source(measured, sources)
        raise AssertionError("+4 shipping address was accepted")
    except Refuse as e:
        if "DsControlB" not in str(e):
            raise AssertionError(f"shipping negative did not name DsControlB: {e}")
        print(f"  [ ok ] +4 shipping DsControlB refused: {e}")
        checks += 1
    print(f"re_cd selftest: {checks}/3 PASS")


def main(argv):
    args = list(argv)
    do_check = "--check-source" in args
    do_selftest = "--selftest" in args
    args = [a for a in args if a not in ("--check-source", "--selftest")]
    if len(args) > 1:
        print(
            "usage: re_cd.py [--check-source] [--selftest] [SLUS_010.40]",
            file=sys.stderr,
        )
        return 2
    try:
        img = Image(args[0] if args else DEFAULT_EXE)
        m = measure(img)
        print("== Vagrant synchronous libds ownership seam ==")
        print(
            f"  _diskReset 0x{m['diskReset']:08X} -> DsControlB 0x{m['DsControlB']:08X}"
        )
        print(
            f"  DsControlB -> DsCommand 0x{m['DsCommand']:08X} + DsSync 0x{m['DsSync']:08X}"
        )
        print(
            f"  measured CD_cw  0x{m['CD_cw']:08X} ({m['command_scanned']} candidates scanned)"
        )
        print(
            f"  measured CD_sync 0x{m['CD_sync']:08X} ({m['sync_scanned']} candidates scanned)"
        )
        print(
            "  boundary: libds queue/IDs/callbacks/results remain guest-owned; reads/XA are NOT owned here"
        )
        if do_check:
            check_source(m)
        if do_selftest:
            selftest(img, m)
        return 0
    except (Refuse, OSError, AssertionError) as e:
        print(f"re_cd REFUSED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

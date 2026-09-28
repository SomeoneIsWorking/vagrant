#!/usr/bin/env python3
"""CENSUS every `jal VSync` in SLUS_010.40 and the FIELD COUNT its argument register holds.

  python3 tools/re_vsync_sites.py                  # the census
  python3 tools/re_vsync_sites.py --selftest       # every check fed a case that MUST answer the other way

WHY THIS IS ITS OWN TOOL, and not a section of `re_viewport.py`. The two ask different questions of
the same image. `re_viewport.py` asks what ONE publication does — who calls the projection leaf, what
it stores, and which words are its own extent. This one asks what EVERY call site passes to one
library routine. A claim table and a call-site census have different evidence shapes (settled
instruction words versus resolved register values), different failure modes (a wrong address versus a
propagation that cannot cross a branch), and different readers; keeping them in one file had put it
over the structure verifier's 1200-line cap, and the cap is there because a file holding two
responsibilities is a file whose two halves stop agreeing.

THE SHARED PRIMITIVES ARE re_viewport's, and are imported rather than copied: the MIPS-I field
extractor, the SHA-bound `Image`/`ExeSet` and the overlay loader are one implementation, and a second
copy of an ISA decoder is a second set of answers about the same words.

WHAT IT DOES NOT ANSWER, AND SAYS SO ON EVERY RUN.
  * A field count is not a frame rate. A rate needs how many of these calls lie on ONE control-flow
    path per frame, and a call-site census cannot recover a path.
  * An unresolved argument is reported as `unresolved` with its count, never as a value, and never
    omitted. A short answer has to say how many it served and how many it was asked for.
  * A missing overlay is a refusal for the claims that would have come from it, printed as NOT
    CHECKED — never as a zero.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from re_viewport import (  # noqa: E402  — the shared MIPS-field primitives, imported once
    DEFAULT_EXE,
    DEFAULT_OVERLAY_DIR,
    EXE_SHA1,
    REG_NAMES,
    ExeSet,
    Image,
    Refuse,
    load_overlays,
    sym,
    target_of,
)

VSYNC = 0x8001F6C4

def _a0_backward(img, site, window=40):
    """The value $a0 holds at a call site, by backward constant propagation, or None.

    THE RULE, and it is one rule: walk backward and answer from the NEAREST definition of $a0. Any
    earlier definition is irrelevant, because it executed before that one. Two things follow that an
    earlier revision of this file got wrong, and both produced confident wrong answers rather than
    absent ones:

      * A SPECIAL instruction's destination is `rd`, not `rt`. Reading `rt` as the destination made
        every `move $sX, $a0` erase the value the scan had just established two instructions later,
        and 43 of 57 sites came back UNRESOLVED while a handful came back wrong.
      * The walk must NOT keep going after it has the answer, and must NOT discard an answer because
        an earlier instruction overwrote the register. The call's own delay slot executes BEFORE the
        callee, so it is the nearest definition and it wins; two of this title's sites put the
        argument there.

    A word this decoder does not cover counts as a definition of both candidate destination
    registers, because skipping it would let a value survive a write the tool could not see.
    """
    env = {}
    order = [site + 4] + [site - 4 * i for i in range(1, window + 1)]
    for a in order:
        w = img.word(a)
        if w is None:
            return None
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        rd = (w >> 11) & 0x1F
        sa = (w >> 6) & 0x1F
        funct = w & 0x3F
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm

        if op in (0x02, 0x03, 0x04, 0x05, 0x06, 0x07) or (op == 0x00 and funct in (8, 9)):
            return env.get("$a0")            # the straight-line segment ends here
        if w == 0:
            continue

        if op == 0x00:
            if funct in (0, 2, 3) and sa:
                v = env.get(REG_NAMES[rt])
                env[REG_NAMES[rd]] = None if v is None else (
                    (v << sa) if funct == 0 else (v >> sa))
            elif funct in (0x21, 0x23, 0x25, 0x24, 0x26, 0x27):
                lv, rv = env.get(REG_NAMES[rs]), env.get(REG_NAMES[rt])
                if rs == 0:
                    env[REG_NAMES[rd]] = rv
                elif rt == 0:
                    env[REG_NAMES[rd]] = lv
                else:
                    env[REG_NAMES[rd]] = None
            else:
                env[REG_NAMES[rd]] = None
            if REG_NAMES[rd] == "$a0":
                return env["$a0"]
            continue

        if op in (0x2B, 0x28, 0x29, 0x2A, 0x2E, 0x2F):        # a store writes no register
            continue
        if op in (0x09, 0x0D):
            env[REG_NAMES[rt]] = simm if op == 0x09 else imm if rs == 0 else None
        elif op in (0x23, 0x24, 0x25, 0x21, 0x20, 0x1C, 0x26):
            env[REG_NAMES[rt]] = None
        else:
            env[REG_NAMES[rt]] = None
            env[REG_NAMES[rd]] = None
        if REG_NAMES[rt] == "$a0":
            return env["$a0"]
    return env.get("$a0")


def vsync_census(modules):
    """Every `jal VSync(0x8001F6C4)` site and the field count its argument register holds."""
    rows = []
    scanned = 0
    for name, img, lo, hi in modules:
        n = 0
        for va, w in img.words(lo, hi):
            n += 1
            if target_of(w, va) == VSYNC:
                rows.append((name, va, _a0_backward(img, va)))
        scanned += n
    return {"rows": rows, "scanned": scanned}


def report(census, out=print):
    out("VSync(n) ARGUMENT CENSUS  —  a FIELD COUNT, and a field count is not a frame rate")
    out("=" * 100)
    rows = census["rows"]
    hist = {}
    per = {}
    for name, va, val in rows:
        key = val if val is not None else "unresolved"
        hist[key] = hist.get(key, 0) + 1
        per.setdefault(name, {})
        per[name][key] = per[name].get(key, 0) + 1
    unresolved = sum(1 for _n, _v, val in rows if val is None)

    out("  modules scanned, and how much of each: %s"
        % ", ".join("%s %d words" % (n, c) for n, c in census.get("modules", [])))
    out("  VSync(0x%08X) call sites:            %d" % (VSYNC, len(rows)))
    out("  instruction words scanned:          %d" % census["scanned"])
    out("  argument resolved by propagation:    %d" % (len(rows) - unresolved))
    out("  UNRESOLVED (argument from memory or a register): %d — listed below, not hidden"
        % unresolved)
    out("")
    out("  argument -> site count, ALL modules")
    for k in sorted(hist, key=lambda x: (x == "unresolved", x)):
        out("    a0 = %-12s %d" % (k, hist[k]))
    out("")
    out("  per module")
    for name in sorted(per):
        out("    %-12s %s" % (name, ", ".join(
            "a0=%s x%d" % (k, v) for k, v in sorted(per[name].items(),
                                                   key=lambda x: (x[0] == "unresolved", x[0])))))
    out("")
    out("  sites that are NOT a no-op field count (a0 >= 2), with their addresses")
    waiting = [(n, v, a) for n, a, v in rows if v is not None and v >= 2]
    for name, val, va in waiting:
        out("    %-12s %s  a0 = %d" % (name, sym(va), val))
    if not waiting:
        out("    none")
    out("")
    out("  unresolved sites")
    for name, va, val in rows:
        if val is None:
            out("    %-12s %s" % (name, sym(va)))
    out("")
    out("  WHAT THIS SUPPORTS, AND WHAT IT DOES NOT.")
    out("  The VSync body at 0x%08X is read from the bytes: it spins on the vsync counter, then" % VSYNC)
    out("  branches — `beq $a0, 1` returns with no wait at 0x8001F824, `blez $a0` returns the current")
    out("  count at 0x8001F760, and only a0 >= 2 falls through to the field-count wait. So an")
    out("  argument of 0 or 1 consumes NO field and an argument of -1 is the query mode, exactly as")
    out("  the workspace method states.")
    out("")
    out("  IT DOES NOT YIELD A FRAME RATE, and the reason is structural rather than a gap in effort:")
    out("  a rate is how many fields elapse per wall-clock second, so it needs the number of these")
    out("  calls on ONE control-flow path per frame, and a call-site census cannot recover a path.")
    out("  What the census does establish is the per-module field-count profile above, and the")
    out("  BATTLE.PRG line is the one that matters for a gameplay frame: %s"
        % (", ".join("a0=%s x%d" % (k, v) for k, v in sorted(per.get("BATTLE.PRG", {}).items()))
           or "no BATTLE.PRG was scanned"))
    # The sentence about BATTLE waiting for a field count is DERIVED, not asserted. A previous
    # revision of this report printed it as a fixed claim, so a BATTLE line that had gained a
    # waiting call would have left the text contradicting the table printed directly above it.
    # The histogram keys are the argument VALUES, with the single string "unresolved" for the rest —
    # so a comparison against "0" or "1" here would silently count every NON-waiting site as a
    # waiting one, which is the failure this derivation exists to prevent. (It did, on the first
    # run of it: `a0=1 x2` was reported as "2 of them waiting".)
    battle = per.get("BATTLE.PRG", {})
    battle_sites = sum(battle.values())
    battle_unresolved = battle.get("unresolved", 0)
    battle_waiting = sum(v for k, v in battle.items() if k != "unresolved" and k not in (0, 1))
    if battle_sites == 0:
        out("  BATTLE.PRG was NOT SCANNED, so nothing is claimed about what it does through VSync.")
    elif battle_waiting == 0 and battle_unresolved == 0:
        out("  %d BATTLE.PRG site(s), none of them waiting and none unresolved: the BATTLE module"
            % battle_sites)
        out("  never waits a field count through VSync. The frame pacing therefore lives in the")
        out("  resident exe and in the title, not in BATTLE.PRG — which is where a rate search has")
        out("  to look next.")
    else:
        out("  %d BATTLE.PRG site(s), %d of them waiting for a field count and %d unresolved: the"
            % (battle_sites, battle_waiting, battle_unresolved))
        out("  conclusion about where the pacing lives is NOT drawn, because this line contradicts it.")


def modules_for(exe, overlays):
    """Every module this census scans, with the extent of each, in the order it reports."""
    mods = [("SLUS_010.40", exe.image, exe.t_addr, exe.t_addr + exe.t_size)]
    for key in ("BATTLE.PRG", "TITLE.PRG", "INITBTL.PRG"):
        img = overlays.get(key)
        if img is not None:
            mods.append((key, img, img.base, img.base + img.file_end))
    return mods


def measure(exe, overlays):
    """The census over every provisioned module, with the scanned extent of each."""
    mods = modules_for(exe, overlays)
    census = vsync_census(mods)
    census["modules"] = [(m[0], m[3] - m[2]) for m in mods]
    return census


def selftest(out=print):
    """Every check this tool makes, fed an input whose answer is known WITHOUT this tool.

    Each case must come out the OTHER way, and the subject of each case is named, because a check
    whose subject is not the thing being measured passes vacuously.
    """
    out("== re_vsync_sites.py --selftest: 3 checks, each a case that MUST come out the other way " + "=")
    for line in (
            "1. a caller census pointed at an address with no caller reports ZERO, not the real count",
            "2. the VSync census on a module with its `jal` encodings zeroed reports 0 sites, and says it",
            "3. the `$a0` resolver returns None for an argument this tool cannot resolve, and a value"
            " for at least one real site",
    ):
        out("   " + line)
    out("")
    fails = []
    try:
        exe = ExeSet()
        overlays = load_overlays()
    except Refuse as exc:
        out("  [1] FAIL %s" % exc)
        return [1, 2, 3]
    battle = overlays.get("BATTLE.PRG")
    if battle is None:
        out("  [1] FAIL BATTLE.PRG absent; the census would have one fewer module and say so")
        return [1, 2, 3]
    lo = battle.base + battle.code[0]
    hi = battle.base + battle.code[1]
    extent = len(battle.data)
    fake = VSYNC + 4
    n_fake = len([va for va, w in battle.words(lo, hi) if target_of(w, va) == fake])
    n_real = len([va for va, w in battle.words(lo, hi) if target_of(w, va) == VSYNC])
    out("  [1] %s caller census over BATTLE.PRG's declared code extent: %d for 0x%08X, %d for "
        "0x%08X (must differ, and the second must be 0)"
        % ("PASS" if (n_real > 0 and n_fake == 0) else "FAIL", n_real, VSYNC, n_fake, fake))
    if not (n_real > 0 and n_fake == 0):
        fails.append(1)

    blank = Image("blank", bytes(extent), battle.base, 0, extent)
    c0 = vsync_census([("BATTLE.PRG", blank, blank.base, lo)])
    c1 = vsync_census([("BATTLE.PRG", battle, lo, hi)])
    out("  [2] %s a zeroed BATTLE.PRG yields %d VSync site(s) over %d scanned words (real: %d over "
        "%d) — a zero here is a MEASURED zero"
        % ("PASS" if (not c0["rows"] and c1["rows"]) else "FAIL", len(c0["rows"]), c0["scanned"],
           len(c1["rows"]), c1["scanned"]))
    if c0["rows"] or not c1["rows"]:
        fails.append(2)

    unknown = _a0_backward(battle, battle.base)
    known = next(((va, val) for _n, va, val in c1["rows"] if val is not None), None)
    out("  [3] %s resolver returns None for a synthetic site (%s) and a value for at least one real "
        "site (%s)" % ("PASS" if (unknown is None and known is not None) else "FAIL", unknown,
                       ("%s a0=%s" % (sym(known[0]), known[1])) if known else None))
    if not (unknown is None and known is not None):
        fails.append(3)

    out("")
    out("  selftest: %d of %d checks FAILED %s" % (len(fails), 3, fails or ""))
    return fails


def main(argv):
    args = [a for a in argv if a != "--selftest"]
    if args and args[0] not in ("--exe", "--overlays"):
        print("usage: re_vsync_sites.py [--exe PATH] [--overlays DIR] [--selftest]", file=sys.stderr)
        return 2
    exe_path = args[args.index("--exe") + 1] if "--exe" in args else DEFAULT_EXE
    ov_dir = args[args.index("--overlays") + 1] if "--overlays" in args else DEFAULT_OVERLAY_DIR
    try:
        if "--selftest" in argv:
            return 1 if selftest() else 0
        exe = ExeSet(exe_path)
        overlays = load_overlays(ov_dir)
    except Refuse as exc:
        print("[re_vsync_sites] REFUSING: %s" % exc, file=sys.stderr)
        return 2
    covered = sum(1 for v in overlays.values() if v is not None)
    print("loaded: SLUS_010.40 (sha1 %s…), overlays %d of 3 (%s)"
          % (EXE_SHA1[:12], covered,
             ", ".join(k for k, v in sorted(overlays.items()) if v is not None)))
    print("A missing overlay is a REFUSAL for the sites that would have come from it, and the scan")
    print("count below says how much of each module was read. It is never a zero.")
    print("")
    report(measure(exe, overlays))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

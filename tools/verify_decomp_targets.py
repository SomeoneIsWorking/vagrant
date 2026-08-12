#!/usr/bin/env python3
"""verify_decomp_targets.py — does the rood-reverse decomp target OUR disc's bytes, module by module?

  python3 tools/verify_decomp_targets.py [/path/to/disc.chd]
  python3 tools/verify_decomp_targets.py --selftest        # proves this tool can print a MISMATCH

Why this exists. rood-reverse (CC0) is a MATCHING decompilation: its source compiles to bytes
identical to its target files. That makes it a pre-verified supply of native bodies for psxport's
override registry — but ONLY for the exact images it targets. Every splat config in that repo states
the SHA-1 it decompiles against, so the question "are those our bytes?" is a measurement, not a
belief. Run it whenever the submodule pin moves.

WHAT A NEGATIVE PRINTS. Every run prints its denominator: configs discovered, modules extracted,
matched, mismatched, extraction failures, and the disc files NOT covered by any config. A module that
mismatches is named with both hashes. The tool REFUSES (exit 2) when the submodule is absent or when
it discovers ZERO configs — a search of a corpus that is not there must never look like a clean pass.

Exit: 0 all matched · 1 something mismatched or failed to extract · 2 the tool could not look.
"""
import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discdump  # noqa: E402
from resolve_disc import resolve  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "external", "rood-reverse")
CONFIG = os.path.join(REF, "config")
OUT = os.path.join(ROOT, "scratch", "raw", "decomp-targets")


def discover():
    """[(module_path_on_disc, expected_sha1, config_file)] from every splat.yaml in the decomp."""
    if not os.path.isdir(CONFIG):
        print(f"[verify] {CONFIG} does not exist — the rood-reverse submodule is not checked out. "
              "This run compared NOTHING. `git submodule update --init external/rood-reverse`.",
              file=sys.stderr)
        raise SystemExit(2)
    found = []
    for dirpath, _dirs, files in os.walk(CONFIG):
        if "splat.yaml" not in files:
            continue
        cfg = os.path.join(dirpath, "splat.yaml")
        sha = None
        for line in open(cfg, encoding="utf-8"):
            if line.startswith("sha1:"):
                sha = line.split(":", 1)[1].strip()
                break
        # The module's path on the disc is its config directory relative to config/ — 'SLUS_010.40',
        # 'BATTLE/BATTLE.PRG', 'MENU/MENU0.PRG'. Verified against `discdump list` output.
        rel = os.path.relpath(dirpath, CONFIG)
        if sha:
            found.append((rel, sha, cfg))
        else:
            print(f"[verify] {cfg} states no sha1 — SKIPPED (it cannot be checked)", file=sys.stderr)
    if not found:
        print(f"[verify] discovered ZERO splat configs under {CONFIG}. Refusing to report a pass "
              "over nothing.", file=sys.stderr)
        raise SystemExit(2)
    return sorted(found)


def run(disc, corrupt_first=False):
    targets = discover()
    dd = discdump.find()
    on_disc = {p for p, _lba, _sz in discdump.listing(disc, dd)}
    matched = mismatched = failed = 0
    for i, (mod, want, cfg) in enumerate(targets):
        if corrupt_first and i == 0:
            want = "0" * 40          # --selftest: a hash that CANNOT match, to prove the negative fires
        dest = discdump.get(disc, mod, OUT, dd)
        if not dest:
            print(f"  {mod:<24} EXTRACT-FAIL  (not on this disc?)")
            failed += 1
            continue
        got = hashlib.sha1(open(dest, "rb").read()).hexdigest()
        if got == want:
            print(f"  {mod:<24} MATCH     {got}")
            matched += 1
        else:
            print(f"  {mod:<24} MISMATCH  disc={got} decomp={want}   ({cfg})")
            mismatched += 1

    covered = {m for m, _s, _c in targets}
    code_on_disc = {p for p in on_disc if p.endswith(".PRG") or p == "SLUS_010.40"}
    uncovered = sorted(code_on_disc - covered)
    print(f"\n[verify] disc: {disc}")
    print(f"[verify] decomp configs discovered: {len(targets)} · matched {matched} · "
          f"mismatched {mismatched} · extract-failed {failed}")
    print(f"[verify] code images on the disc: {len(code_on_disc)} · covered by a config "
          f"{len(code_on_disc & covered)} · NOT covered: {uncovered or 'none'}")
    print("[verify] BLIND SPOTS: a SHA-1 match proves the decomp targets these bytes; it says "
          "nothing about how much of them is decompiled (see docs/references.md), and nothing about "
          "any file that is data rather than code.")
    return 0 if (mismatched == 0 and failed == 0) else 1


def selftest(disc):
    """Feed a case that MUST produce a MISMATCH. A checker nobody has seen fail is not a checker."""
    print("[selftest] running with the FIRST target's expected hash replaced by 40 zeros; "
          "the run must report exactly one MISMATCH and exit 1.")
    rc = run(disc, corrupt_first=True)
    ok = rc == 1
    print(f"[selftest] {'PASS' if ok else 'FAIL'}: exit {rc} (expected 1)")
    return 0 if ok else 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("disc", nargs="?")
    ap.add_argument("--selftest", action="store_true",
                    help="prove the comparator can report a mismatch (uses the real disc)")
    a = ap.parse_args()
    d = resolve(a.disc, verbose=True)
    sys.exit(selftest(d) if a.selftest else run(d))

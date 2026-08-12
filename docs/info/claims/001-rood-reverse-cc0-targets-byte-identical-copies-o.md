---
id: C001
kind: claim
status: holds
created: 2026-08-12
tags: references,decomp
depends: tools/verify_decomp_targets.py
---

## Claim

rood-reverse (CC0) targets byte-identical copies of all 21 code images on our Vagrant Story disc — SLUS_010.40 sha1 fababcfd4325d42f350d95b3472874affeb0e48c plus 20 .PRG modules

## Evidence

tools/verify_decomp_targets.py against the retail USA disc image (resolved via $PSXPORT_VAGRANT_DISC; the path is machine-specific and deliberately not recorded here), 2026-08-12: 21 configs discovered, 21 matched, 0 mismatched, 0 extract-failed; 22 code images on disc, 21 covered, the uncovered one is the 0-byte MENU/MENUA.PRG. Negative control: --selftest replaces one expected hash with 40 zeros and the run reports exactly 1 MISMATCH and exits 1 (PASS).

## What would falsify it

a different disc dump (region/revision) yielding a different SLUS_010.40 sha1, or the submodule pin moving to a commit whose splat configs state other hashes — re-run tools/verify_decomp_targets.py

---
id: 7
title: [recomp-MISS] names an already-generated resident function during first Vagrant boot
status: resolved
symptom: Resident-only Vagrant boot reported [recomp-MISS] 0x80026864 although generated rec_func_index contained that entry
tags: recompiler,routing,re-02,vagrant
created: 2026-08-14
updated: 2026-08-14
---

## Cause

`GameConfig::recMainLo` and `recMainHi` were both zero. `overlay_router` masks the target to a
physical address and only calls `main_dispatch` inside that configured range, so it fell through to
`rec_dispatch_miss` without consulting the generated index.

## Resolution

Set the measured PS-EXE physical text range `[0x00010000,0x00062000)`, with a compile-time assertion
against generated `REC_MAIN_LO/HI` when the substrate exists. Remove the proposed `0x80026864` seed:
it was already among the emitter's 743 functions.

## Evidence

`scratch/logs/re02-first-run.log` shows the false miss; the reproducible emitter output indexes the
entry; `scratch/logs/re02-third-run.log` handles InitHeap and reaches guest main, then stops at the
distinct BIOS `A0:0x2F` fatal. `python3 tools/re_crt0.py --selftest` feeds zero `kRecMainLo` through
the shipping configuration gate and requires the named header mismatch.

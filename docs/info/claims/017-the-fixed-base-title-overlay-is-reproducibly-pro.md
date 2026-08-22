---
id: C017
kind: claim
status: holds
created: 2026-08-22
tags: overlay,title,runtime
depends: tools/extract_overlays.py#provision, tools/ensure_recomp.py#generated_complete
---

## Claim

The fixed-base TITLE overlay is reproducibly provisioned, emitted, registered, and live-routed into vs_title_exec at 0x80071334.

## Evidence

Owned TITLE/TITLE.PRG SHA-1 f74a76e6215edebf607d0c2af56481050edb139a matches its exact rood-reverse target; generated table owns [0x80068800,0x800EFE48); live scratch/logs/title-overlay-first-run.log contains ov_title_func_80071334 and no old recomp-MISS; tests/test_overlay_inputs.py rejects hash mismatch, unowned input, and a generated dispatcher missing that entry.

## What would falsify it

if the owned TITLE hash changes, the generated table/entry is absent, or a fresh headless run again misses 0x80071334

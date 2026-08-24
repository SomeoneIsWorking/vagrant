---
id: C026
kind: claim
status: holds
created: 2026-08-25
tags: runtime,overlay,battle,initbtl,re-15
depends: tools/extract_overlays.py#OVERLAYS, tools/ensure_recomp.py#generated_complete
---

## Claim

The bounded Start replay executes BATTLE 0x800798A4 and INITBTL 0x800FA35C, removing the former
0x800798A4 miss and exposing the later BATTLE target 0x800E6EAC.

## Evidence

The one authorized run against psxport aa0b2067 used PID 199806 and the prepared Start replay.
Gitignored `scratch/logs/re15_battle_entry_aa0b2067.stdout.log` contains host write-watch backtraces
through `ov_battle_func_800798A4`, `ov_battle_gen_800798A4`, and
`ov_initbtl_gen_800FA35C`. The paired runtime log has no miss at 0x800798A4 and next reports
`recomp-MISS 0x800E6EAC`, caller return address 0x800FA4A8, with BATTLE resident in the slot.

## What would falsify it

A bounded run with the same SHA-bound inputs restores the 0x800798A4 miss, no longer executes either
named generated function, reports a resident image other than BATTLE at the next boundary, or fails
to reach 0x800E6EAC before any earlier guest failure.

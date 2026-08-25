---
id: 22
title: Cross-overlay call target demoted to a local label
status: resolved
symptom: After BATTLE and INITBTL begin executing, INITBTL's direct call to BATTLE 0x800E6EAC fails even though BATTLE contains that callable entry
tags: runtime,overlay,recompiler,battle,re-15
created: 2026-08-25
updated: 2026-08-25
---

## Root cause

The emitter discovers direct call targets and protects internal call targets from entry demotion only
within each overlay image. INITBTL directly calls BATTLE `0x800E6EAC`, but that cross-overlay target
is not propagated into BATTLE's hard seed set. BATTLE also branches to the same address from a
preceding body, so `demote_internal_entries` retains only `L_800E6EAC` as a local label and discards
the separate callable entry.

This is not a missing game seed. The SHA-bound BATTLE word at `0x800E6EAC` is `0x03E00008`
(`jr ra`) followed by delay-slot word `0x3C08800F` (`lui t0,0x800F`); rood-reverse independently
labels the address `func_800E6EAC`. The generated INITBTL body contains a direct
`rec_dispatch(c, 0x800E6EACu)`, while the generated BATTLE dispatcher has no corresponding
`ov_battle_func_800E6EAC` case.

## Evidence

The one authorized bounded run against psxport `aa0b2067` first entered
`ov_battle_gen_800798A4` and `ov_initbtl_gen_800FA35C`, then reported
`recomp-MISS 0x800E6EAC`, caller return address `0x800FA4A8`, with BATTLE resident in slot 0.
The exact evidence is in gitignored
`scratch/logs/re15_battle_entry_aa0b2067.{log,stdout.log}`.

## Required resolution and falsifier

The framework emitter must preserve a destination-overlay callable entry for a valid direct
cross-overlay call target while still allowing a preceding body to use the same address as its local
label. A regression must reproduce that dual role across two modules. Static generation is green
only when BATTLE dispatch contains `ov_battle_func_800E6EAC` and the predecessor still contains
`L_800E6EAC`; the next separately authorized bounded run must remove this miss and advance to a later
concrete guest boundary. Adding this one address to Vagrant's seed file would hide the generic defect
and is not a resolution.

### Resolution (2026-08-25)
Fixed generically in psxport 0339b459 (cross_overlay_call_targets: disjoint-range + callable-entry proofs, same-slot siblings rejected) plus the case-label/pointer-sink emitter work in 073d7a62. Runtime falsifier met: bounded Start replay scratch/logs/re15-battle-entry-0339b459-jtfix.log no longer reports recomp-MISS 0x800E6EAC and advances deep into BATTLE (next boundary is issue #23). Static gates: BATTLE dispatch contains ov_battle_func_800E6EAC while the predecessor body reaches the same address as a callable entry; INITBTL's direct rec_dispatch(c, 0x800E6EACu) routes to it.

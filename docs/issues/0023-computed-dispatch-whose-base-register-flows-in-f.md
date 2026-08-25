---
id: 23
title: Computed dispatch whose base register flows in from a preceding jr-ra fragment fail-fasts (BATTLE 0x800B182C)
status: open
symptom: After the mask-stride/case-label emitter fixes, the bounded Start replay advances deep into BATTLE and fails with [recomp-MISS 0x800B182C] from caller ra=0x800B2AE4 while executing pc=0x800B16F4
tags: recompiler,computed-jump,re-15,battle,fragments
created: 2026-08-25
updated: 2026-08-25
---

## Symptom

Bounded Start replay against psxport 073d7a62 substrate: `[recomp-MISS 0] no recompiled fn for 0x800B182C (caller ra=0x800B2AE4, a0=0x1F8003E0, c->pc=0x800B16F4)`. Evidence: scratch/logs/re15-battle-entry-0339b459-jtfix.log.

## Root cause (measured)

The Sony hand-written GTE macro chain is a run of blocks separated by `jr ra` + delay. Each block ends by dispatching to its successor through a register whose BASE was materialised in an EARLIER block:

    800B1818: lui t9,0x800B ; addiu t9,t9,0x180C   <- base built in block N
    ...
    800B16FC: addiu t9,t9,32                        <- consumed in block N+k
    800B1704: jr t9                                  -> 0x800B182C, a mid-run case

Per-function reaching-constant analysis structurally cannot see across the jr-ra boundaries, so the hop emits as runtime register dispatch and fail-fasts on the first case block that is neither an entry nor a label. Linear image-wide propagation does not help: intervening DATA regions decode as unknown instructions and clear the map (measured - t9 is already unknown at 0x800B16FC).

## Class census (scratch/re15_residual_class.py)

RESIDENT 113 / TITLE 360 / BATTLE 177 non-ra jr sites; every site whose constants are recoverable TODAY recovers. The residual set needing cross-fragment flow is small but nonzero (this chain family in resident + BATTLE).

## Required resolution and falsifier

Path-sensitive constant propagation ALONG each chain: seed at the lui/addiu construction, follow the chain through its jr-ra fragments (not linear image order), collect the reachable target set per jr, and either emit intra-run switches or seed those targets as entries. Soundness bar: additive-only (extra entries are safe); a wrong static target that silently replaces dispatch would corrupt execution.

Falsifier: the next bounded replay removes this miss and advances to a later concrete guest boundary; a regression must reproduce the register-carried-base shape across two modules hermetically.

---
id: C027
kind: claim
status: holds
created: 2026-08-25
tags: recompiler,re-15,battle
depends: external/psxport/tools/recomp/emit.py
---

## Claim

Vagrant's BATTLE/INITBTL execution advances past the former 0x800E6EAC and 0x80040FC8 fail-fasts: cross-overlay call targets, mask-stride dispatch recovery, iterative case-label pruning, and dispatch-base-vs-function-pointer classification are landed and runtime-proven

## Evidence

psxport 0339b459 + 073d7a62; bounded Start replay scratch/logs/re15-battle-entry-0339b459-jtfix.log reaches deep BATTLE and stops only at issue #23's 0x800B182C; static gates: generated/ov_battle_disp.c contains ov_battle_func_800E6EAC (case 0x000E6EACu), resident GTE chain emitted as switches over L_80040FA8..L_800411E4 labels in generated/shard_7.c; emitter suites 64/64 + framework ctest 104/104 + vagrant ctest 7/7

## What would falsify it

any bounded replay against psxport >= 073d7a62 reporting recomp-MISS 0x800E6EAC or 0x80040FC8 again, or a framework ctest/emitter-suite regression on those commits

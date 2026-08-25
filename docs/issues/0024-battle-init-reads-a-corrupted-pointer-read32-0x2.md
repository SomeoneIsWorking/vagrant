---
id: 24
title: BATTLE init reads a corrupted pointer (read32 @0x2414003B, last-fn 0x800417C8, ra 0x8008A058)
status: open
symptom: After cross-fragment dispatch completion, the bounded Start replay passes all former fail-fasts and dies with [mem:error] FATAL: UNMAPPED RAM read32 @ 0x2414003B (phys 0x0414003B); v0=0x2413FFFF just before the fault; caller context is BATTLE initialization via ov_battle_gen_80089DC0
tags: battle,re-15,memory-corruption,next-boundary
created: 2026-08-25
updated: 2026-08-25
---

## Symptom

psxport cab5d077 substrate. Evidence: scratch/logs/re15-flow5.log (guest register dump incl. v0=0x2413FFFF immediately before the wild read).

## Meaning

This is the NEW concrete boundary after cross-fragment completion landed. Either an upstream initialization produced garbage our execution path now exposes (blocks newly reachable via seeded entries run for the first time), or a mistranslation exists in one of the newly split/added fragments. Both are testable: SBS-diff a seeded fragment against its guest semantics, and trace who wrote the pointer at its source.

## Falsifier

A replay that passes this read (or proves the pointer value correct against real-hardware expectations) advances BATTLE init to its next boundary.

---
id: 24
title: BATTLE init reads a corrupted pointer (read32 @0x2414003B, last-fn 0x800417C8, ra 0x8008A058)
status: resolved
symptom: After cross-fragment dispatch completion, the bounded Start replay passes all former fail-fasts and dies with [mem:error] FATAL: UNMAPPED RAM read32 @ 0x2414003B (phys 0x0414003B); v0=0x2413FFFF just before the fault; caller context is BATTLE initialization via ov_battle_gen_80089DC0
tags: battle,re-15,memory-corruption,next-boundary
created: 2026-08-25
updated: 2026-08-26
---

## Update 2026-08-26

After issue #25's fix (psxport f9b5db8f) a truly HEADLESS run reaches this boundary by itself
(scratch/logs/i25-cdc-trace.log, .log fix10/unattended: all 'headless sink', zero input channels
active): same read32 @0x2414003B, ra 0x8008A058, last-fn ov_battle_gen_80089DC0. Trace shows the
automatic post-intro flow: movie sectors end -> CdlPause -> Setmode 0xA0 (data mode) -> file loads
at LBA ~7254 -> ov_battle dispatch -> abort. Whether this is the attract DEMO or another automatic
title transition is NOT yet determined — do not cite the WINDOWED smoke runs for this claim: one of
them had the operator playing (input-driven reachability proves nothing about the unattended path).

---

## Symptom

psxport cab5d077 substrate. Evidence: scratch/logs/re15-flow5.log (guest register dump incl. v0=0x2413FFFF immediately before the wild read).

## Meaning

This is the NEW concrete boundary after cross-fragment completion landed. Either an upstream initialization produced garbage our execution path now exposes (blocks newly reachable via seeded entries run for the first time), or a mistranslation exists in one of the newly split/added fragments. Both are testable: SBS-diff a seeded fragment against its guest semantics, and trace who wrote the pointer at its source.

## Falsifier

A replay that passes this read (or proves the pointer value correct against real-hardware expectations) advances BATTLE init to its next boundary.

## Resolution (2026-08-26, psxport 54af32cb)

The pointer was never corrupted in memory — a CALLEE-SAVED REGISTER was. Root cause chain,
all measured:

1. BATTLE func_80089DC0 sets $s0=0x800F0000 then calls func_80089114 -> ... -> func_800E6F9C.
2. func_800E6F9C ends in GCC's shared-epilogue tail idiom (lui $ra,0x800d; bgez $zero,0x800DC638;
   ori $ra,$ra,0xb888 — verified against the SHA-bound retail image with tools/disasm.py). The
   callee returns to the epilogue block at 0x800DB888, which restores $s0-$s5/$ra/$sp for BOTH
   frames. The emitter's call+return translation skipped that epilogue entirely.
3. Back in func_80089DC0, `lw $t0,0x19FC($s0)` therefore read garbage (gdb at the three call
   returns showed $s0 already broken after the FIRST callee), and the follow-up
   `lw +0x3C` dereferenced 0x2413FFFF -> fault at 0x2414003B.

Fix: emit.py ra_branch_continuations() — per-site, static, conservative; call then dispatch to $ra.
11 sites substrate-wide (1 resident + 10 BATTLE). RECOMP_VERSION 2026-08-26.14.

Falsifier MET: unattended run passes this read and continues; 240s headless / 150s windowed with
zero faults (scratch/logs/i24-fix2.log, i24-windowed.log). One follow-on defect found and fixed on
the historical guest-loop route: presenter capture grew unbounded past title products because no
field fence committed it. The current owner is VagrantFrameDriver's single commit.

---
id: C007
kind: claim
status: holds
created: 2026-08-14
tags: re-02,recompiler
depends: game/recomp_seeds.json, game/core/game_config.cpp, game/core/recomp_register.cpp, external/psxport
reconfirmed: 2026-08-14 12:36:31
verified_at: 2026-08-14 12:36:31
---

## Claim

Vagrant's minimum resident substrate needs no explicit executable seed: emit.py roots at PS-EXE entry 0x8001F544 and emits the reached InitHeap thunk and guest main among 743 functions

## Evidence

The documented emitter command reports `260 seeds -> 743` in `scratch/logs/re02-emit-corrected.log`.
The resulting binary handles the generated `0x80026864` InitHeap thunk and enters generated guest
main `0x80042C38` before fatal BIOS `A0:0x2F` in `scratch/logs/re02-third-run.log`. Re-running the
same command from the SHA-verified executable reproduces the gitignored generated index.

## What would falsify it

A run against the same SHA-verified executable reports a genuine recomp-MISS before the current BIOS A0:0x2F boundary, or emitter entry-root semantics change

## Re-confirmed 2026-08-14 12:36:31

Commit 10cedc3: clean-pin 4a20ca51 build passes; live resident run reaches guest main then exact A0:2F boundary with no recomp-MISS.

---
id: C007
kind: claim
status: holds
created: 2026-08-14
tags: re-02,recompiler
depends: game/recomp_seeds.json, game/core/game_config.cpp, game/core/recomp_register.cpp, external/psxport
reconfirmed: 2026-08-21 02:22:25
verified_at: 2026-08-21 02:22:25
---

## Claim

Vagrant's minimum resident substrate needs no explicit executable seed: emit.py roots at PS-EXE entry 0x8001F544 and emits the reached InitHeap thunk and guest main among 743 functions

## Evidence

The documented emitter command reports `260 seeds -> 743` in `scratch/logs/re02-emit-corrected.log`.
The resulting binary handles the generated `0x80026864` InitHeap thunk and enters generated guest
main `0x80042C38`. The earlier `scratch/logs/re02-third-run.log` A0:0x2F fatal was resolved as a
generic framework rand gap in psxport `be03593f`: the integration trace records exactly one srand and
97 rand calls, then reaches the no-frame watchdog with no recompilation miss or unimplemented-BIOS
fatal. The sampled stack is in `Core::mem_w32` beneath generated `0x8002411C` and callers; it does not
classify the stall. Re-running the same command from the SHA-verified
executable reproduces the gitignored generated index.

## What would falsify it

A run against the same SHA-verified executable reports a genuine recomp-MISS before the current
no-frame boundary, the emitter entry-root semantics change, or the generated index no longer
contains the reached resident functions named above

## Re-confirmed 2026-08-14 12:36:31

Commit 10cedc3: clean-pin 4a20ca51 build passes; live resident run reaches guest main then exact A0:2F boundary with no recomp-MISS.

## Re-confirmed 2026-08-14 12:57:01

Psxport be03593f resolves the historical rand HLE boundary without changing Vagrant seeds or generated code. The BIOS trace records 1 srand and 97 rand calls; the bounded run reaches a later no-frame watchdog with no recomp-MISS or unimplemented-BIOS fatal. Its sampled Core::mem_w32 stack does not yet classify the stall. No gameplay or overlay execution is claimed.

## Re-confirmed 2026-08-14 13:33:18

Reconfirmed on the RE-04 bounded run using the framework content landed as psxport 2306a7c5: the same 743-function resident substrate reaches generated DsControlB and advances beyond _diskReset after the native blocking-control owner, with no recomp-MISS. Seed/root contract unchanged.

## Re-confirmed 2026-08-21 01:04:32

2026-08-21: the full vagrant_port rebuilt with Clang against the current shared framework; direct headless execution loaded the same generated 743-function substrate, entered guest main, and reached the known 0x8001355C no-frame watchdog with no recomp-MISS or BIOS fatal.

## Re-confirmed 2026-08-21 02:09:08

After recording landed psxport `eb2465b2`, the hash gate kept the unchanged 743-function substrate, the exact Clang rebuild passed, and plain `./run.sh` entered guest crt0/main and reached generated `0x8001355C` with no recomp-MISS or BIOS fatal.

## Re-confirmed 2026-08-21 02:22:25

Final recorded psxport `be381503` preserves the same hash-current 743-function substrate and plain-launch route through guest crt0/main to generated `0x8001355C`, with no recomp-MISS or BIOS fatal.

---
id: C008
kind: claim
status: holds
created: 2026-08-14
tags: re-04,cd
depends: game/core/game_hooks.cpp, game/cd/ds_control.cpp#ds_control_b, game/cd/ds_control_contract.h#ownedControl, cmake/vagrant_port.cmake, external/psxport
reconfirmed: 2026-08-14 13:48:12
verified_at: 2026-08-14 13:48:12
---

## Claim

Vagrant's blocking libds control wrapper is DsControlB at 0x80025BE4 and can be owned synchronously without replacing the async command/read paths

## Evidence

tools/re_cd.py uniquely derives the call chain and ABI shapes from the SHA-verified PS-EXE; 3/3 selftest passes. The standalone `vagrant_cd_contract_test` compiles the shipping classifier, accepts all 9 owned IDs, and refuses query, read, and unknown examples. scratch/logs/re04-owner-run.log records Pause and Setmode through the owner backed by pinned psxport 2306a7c5 and advances beyond _diskReset to 0x8001355C with no recomp-MISS or BIOS fatal.

## What would falsify it

the same verified image yields a different unique DsControlB address, an unsupported command reaches the owner, or a bounded run no longer advances beyond _diskReset

## Re-confirmed 2026-08-14 13:33:25

Reconfirmed after formatter and final combined build: re_cd 3/3, DsControlB owner logs Pause/Setmode and advances beyond _diskReset, no recomp-MISS or BIOS fatal.

## Re-confirmed 2026-08-14 13:48:12

Reconfirmed after the shared GAME_SRC and classifier gate landed in the dirty tree: no-generated vagrant_seam compiles ds_control.cpp; vagrant_cd_contract_test accepts 9/9 allowed and refuses 3/3 query/read/unknown cases; the rebuilt live port records Pause and Setmode then reaches the same later 0x8001355C watchdog with zero recomp-MISS, BIOS fatal, or DsControlB refusal.

---
id: C008
kind: claim
status: holds
created: 2026-08-14
tags: re-04,cd
depends: game/core/vagrant_runtime.cpp#VagrantRuntime::registerOverrides, game/cd/ds_control.cpp#ds_control_b, game/cd/ds_control_contract.h#ownedControl, cmake/vagrant_port.cmake
reconfirmed: 2026-08-22 18:14:39
verified_at: 2026-08-22 18:14:39
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

## Re-confirmed 2026-08-21 01:04:32

2026-08-21: re_cd shipping gate/selftest passed 3/3; the Clang-built vagrant_cd_contract_test passed; direct headless vagrant_port execution advanced beyond disk reset to the same 0x8001355C boundary without a recomp-MISS, BIOS fatal, or unsupported-control refusal.

## Re-confirmed 2026-08-21 02:09:08

Against recorded psxport `eb2465b2`, re_cd again passed 3/3, the shipping classifier CTest passed, and plain `./run.sh` advanced beyond disk reset to generated `0x8001355C` without recomp-MISS, BIOS fatal, or unsupported-control refusal.

## Re-confirmed 2026-08-21 02:22:25

After the then-recorded psxport `be381503` Clang rebuild and classifier CTest, plain `./run.sh` again advanced beyond disk reset to generated `0x8001355C` without recomp-MISS, BIOS fatal, or unsupported-control refusal.

## Re-confirmed 2026-08-21 02:47:31

2026-08-21: re_cd check-config/selftest 3/3, shipping contract test, and real default launcher remain green after RE-09 integration.

## Re-confirmed 2026-08-21 02:59:16

2026-08-21: against landed psxport 2b5ef7b5, CD contract CTest passed and the default launcher advanced beyond disk reset and SPU DMA without unsupported-control refusal.

## Re-confirmed 2026-08-21 03:34:14

Post-landing CTest 3/3 passed, including vagrant_cd_contract_test; the added VBlank registration leaves measured DsControlB ownership intact.

## Re-confirmed 2026-08-21 03:35:32

Post-comment landing: hook composition changed comments only; post-RE10 CTest 3/3 still passed the DsControlB shipping contract and full Clang policy.

## Re-confirmed 2026-08-22 14:13:25

2026-08-22: Clang rebuilt the shipping owner under VagrantRuntime; vagrant_cd_contract_test and full CTest passed, and the bounded real run reached TITLE work through DsControlB with the same boundary.

## Re-confirmed 2026-08-22 17:51:58

2026-08-22 re_cd.py --check-config --selftest passed 3/3; vagrant_cd_contract_test and full CTest passed after VagrantRuntime override composition changed

## Re-confirmed 2026-08-22 18:14:39

2026-08-22 against psxport ad5cf802: re_cd 3/3, re_async_cd 3/3, CD contract CTest, Clang build, and default-disc boot all pass

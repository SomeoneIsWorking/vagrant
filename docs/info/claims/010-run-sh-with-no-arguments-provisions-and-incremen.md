---
id: C010
kind: claim
status: holds
created: 2026-08-21
tags: launcher,substrate
depends: tools/run.py#launch, tests/test_launcher.py, psxport.pin, external/psxport
reconfirmed: 2026-08-21
verified_at: 2026-08-21 13:14:25
---

## Claim

./run.sh with no arguments provisions and incrementally builds the verified resident substrate, then executes scratch/bin/vagrant_port; its honest current runtime boundary is the no-frame watchdog in Sony VSync after measured SPU DMA completion, not gameplay.

## Evidence

2026-08-21: vagrant_launcher_test positive/refusal cases passed; real ./run.sh runs resolved the configured USA CHD, matched SHA-1 fababcfd..., built with Clang, loaded all 4 RmlUi assets, and reached the watchdog with no recomp miss or BIOS fatal. Repeated runs reported recomp up to date and rebuilt no generated TU. After RE-09, the real route dispatches DMA4 callback 0x8001DE94 from measured slot 0x80032138, advances beyond generated 0x8001355C, and samples the next watchdog in VSync 0x8001F6C4/0x8001F83C.

## What would falsify it

if no-argument ./run.sh selects another executable, rewrites unchanged generated sources, omits framework assets, or reaches a runtime boundary other than the documented watchdog without the claim being refreshed

## Re-confirmed 2026-08-21 02:44:52

After RE-09, launcher tests pass and the real no-argument route remains incremental, Clang-built, and headless; it dispatches measured DMA4 callback 0x8001DE94 and reaches the documented VSync watchdog instead of the retired 0x8001355C boundary.

## Re-confirmed 2026-08-21 02:59:16

2026-08-21: against landed psxport 2b5ef7b5, launcher CTest passed and real no-argument run provisioned/built/launched the intended target, dispatched DMA4, and reached the documented VSync watchdog.

## Re-confirmed 2026-08-21 03:31:41

Launcher CTest passed and real no-argument ./run.sh provisioned, incrementally Clang-built, launched vagrant_port, printed the current no-present boundary, and reached it after resident VBlank/GPU setup

## Re-confirmed 2026-08-21 03:34:14

Post-landing launcher selftest passed inside CTest 3/3; the final pre-landing no-argument run used the same launcher logic and reached the no-present watchdog after 179 VBlank transitions.

## Re-confirmed 2026-08-21

Post-landing plain no-argument launcher used pinned psxport 9f1bb927, retained the current substrate, and reached the documented async-CD boundary.

## Re-confirmed 2026-08-21 13:13:23

Against recorded psxport pin ce2c83ad, plain ./run.sh selected the shared framework at that exact commit, verified the retail executable identity, configured/build with Clang, printed the current TITLE.PRG/0x80071334 boundary, and reached that fail-fast target without an argument or hidden mode flag.

## Re-confirmed 2026-08-21

Post-landing zero-argument launcher resolved psxport ce2c83ad, built the current product, completed five asynchronous reads, and reached the documented TITLE overlay miss 0x80071334.

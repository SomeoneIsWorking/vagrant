---
id: C010
kind: claim
status: falsified
created: 2026-08-21
tags: launcher,substrate
depends: tools/run.py#launch, tests/test_launcher.py, psxport.pin, external/psxport
reconfirmed: 2026-08-21
verified_at: 2026-08-21 14:16:30
falsified_on: 2026-08-22
---

## Claim

./run.sh with no arguments provisions and incrementally builds the verified resident substrate, then executes scratch/bin/vagrant_port; its honest current runtime boundary is the first direct un-emitted TITLE function at 0x80071334 after five complete asynchronous reads, not gameplay.

## Evidence

2026-08-21: `vagrant_launcher_test` positive/refusal cases passed; real `./run.sh` runs resolved the configured USA CHD, matched SHA-1 fababcfd..., built with Clang, and reached the documented fail-fast target without an argument or hidden mode flag. Repeated runs reported the recompilation up to date and rebuilt no generated translation unit. The live route dispatches the measured DMA4 and VBlank callbacks, completes four WAVE reads and the 271-sector TITLE.PRG read, then reports the missing generated owner for 0x80071334.

## What would falsify it

if no-argument ./run.sh selects another executable, rewrites unchanged generated sources, omits framework assets, or reaches a runtime boundary other than the documented TITLE-overlay fail-fast without the claim being refreshed

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

## Re-confirmed 2026-08-21 14:13:38

Against recorded psxport pin 3418a79b, a scoped-clean plain ./run.sh generated the consumer-owned SDL_GPU shader header, built with verified Clang, launched the current product, completed all five asynchronous reads, and reached the documented TITLE overlay miss 0x80071334. A second unchanged no-argument run reported the recompilation up to date, compiled no C/C++ translation unit, and reached the same boundary.

## Re-confirmed 2026-08-21

Post-landing zero-argument launcher regenerated the consumer-owned shader header with Clang, then an unchanged second run compiled no C/C++ translation units and reached the same 0x80071334 boundary on psxport 3418a79b.

## FALSIFIED 2026-08-22

RE-11 intentionally changed the default product: ./run.sh now provisions TITLE.BIN and routes beyond the retired 0x80071334 overlay miss, so C010's stated current boundary is false.

> Anything that cited this claim as proof must be re-checked. Grep the repo for it.

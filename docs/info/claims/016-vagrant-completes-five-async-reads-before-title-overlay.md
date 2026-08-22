---
id: C016
kind: claim
status: falsified
created: 2026-08-21
tags: cd,overlay,re-04,re-05
depends: tools/re_async_cd.py#measure, tools/run.py#launch, psxport.pin, external/psxport
reconfirmed: 2026-08-21
verified_at: 2026-08-21 14:16:30
falsified_on: 2026-08-22
---

## Claim

Against pinned psxport 3418a79b, Vagrant completes four asynchronous WAVE reads and all 271 TITLE.PRG sectors before the first direct TITLE call fails fast at un-emitted overlay target 0x80071334.

## Evidence

tools/re_async_cd.py derives and mutation-tests the resident callback/status/VBlank/Pause contract; `scratch/logs/re18-3418a79b-direct-runtime.log` shows exact +225792 guest-cycle deadlines, 384 sectors in five measured ranges, status 0x22, queue dispatch, and Pause completion 0x02; `scratch/logs/re18-3418a79b-default-launcher.log` independently reaches the same target through ordinary ./run.sh.

## What would falsify it

if ordinary ./run.sh no longer reaches 0x80071334, any of the five sector ranges or libds status transitions differ, or TITLE is emitted and the call advances

## Re-confirmed 2026-08-21 14:13:39

Against recorded psxport pin 3418a79b, scratch/logs/re18-3418a79b-direct-runtime.log records 389 exact +225792-cycle events, five contiguous ranges totaling 384 sectors, all queued Pause transitions, status 0x22/0x02, no STUCK, and the sole 0x80071334 miss; ordinary ./run.sh independently reaches the same boundary.

## Re-confirmed 2026-08-21

Post-landing direct trace completed five reads totaling 384 contiguous sectors with all 389 intervals at 225792 ticks, correct Pause/status arbitration, no STUCK, and sole next miss 0x80071334.

## FALSIFIED 2026-08-22

Its explicit falsifier occurred: TITLE is emitted and the 0x80071334 call now advances into ov_title_func_80071334. The five-read evidence remains historical CD evidence but no longer describes the current terminal boundary.

> Anything that cited this claim as proof must be re-checked. Grep the repo for it.

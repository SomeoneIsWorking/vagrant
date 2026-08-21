---
id: C016
kind: claim
status: holds
created: 2026-08-21
tags: cd,overlay,re-04,re-05
depends: tools/re_async_cd.py#measure, tools/run.py#launch, psxport.pin, external/psxport
---

## Claim

Against pinned psxport ce2c83ad, Vagrant completes four asynchronous WAVE reads and all 271 TITLE.PRG sectors before the first direct TITLE call fails fast at un-emitted overlay target 0x80071334.

## Evidence

tools/re_async_cd.py derives and mutation-tests the resident callback/status/VBlank/Pause contract; the reproducible diagnostic command in issue #16 shows exact +225792 guest-cycle deadlines, 384 sectors in five measured ranges, status 0x22, queue dispatch, and Pause completion 0x02; ordinary ./run.sh independently reaches the same target.

## What would falsify it

if ordinary ./run.sh no longer reaches 0x80071334, any of the five sector ranges or libds status transitions differ, or TITLE is emitted and the call advances

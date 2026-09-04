---
id: C014
kind: claim
status: falsified
created: 2026-08-21
tags: boot,cd,re-04
depends: docs/issues/0014-vagrant-vsync-waits-forever-because-resident-vbl.md, tools/re_vblank.py#measure, tools/re_async_cd.py#measure, external/psxport
falsified_on: 2026-08-21
---

## Claim

The current Vagrant no-present watchdog is reached from the first asynchronous sound-data read, not from a failed VBlank or reached frame loop.

## Evidence

2026-08-21: against pinned psxport 9f1bb927, scratch/logs/re05-pinned-final-irq-dma.log records the real HookEntryInt custom-exit route, repeated armed DMA4 callbacks, and guest VBlank counter 0x80032114 advancing 0 through 173. The watchdog stack is then _loadMenuSound 0x800468FC -> vs_main_diskLoadFile 0x8004493C -> vs_main_gametimeUpdate 0x8004261C -> VSync 0x8001F6C4. Matching retail source and resident call addresses identify the loop as the async CD-state poll.

2026-08-21: the narrower data-completion hypothesis was falsified. `tools/re_async_cd.py --selftest`
derives and mutation-tests the resident guest contract (3/3). `scratch/logs/re11-shared-cdc.log` and
`scratch/logs/re11-paced-fntrace.log` show all 17 LBA 63000..63016 sectors entering the guest callback;
the last callback stores disk state idle and queues Pause. `scratch/logs/re11-paced-libds-state-range.log`
shows that libds instead remains ReadN command state `0x11`, system Busy, response status `0x02`, and
queue length one. The watchdog is therefore downstream of completed sector delivery but still inside
the first asynchronous sound-load transaction.

## What would falsify it

if the default run completes the async read, reaches an overlay presenter, or the watchdog stack no longer contains this call chain

## FALSIFIED 2026-08-21

Pinned psxport ce2c83ad default ./run.sh completes four WAVE reads and the TITLE.PRG read, then fails fast at the un-emitted TITLE target 0x80071334; the old async-poll watchdog stack is no longer the current boundary.

> Anything that cited this claim as proof must be re-checked. Grep the repo for it.

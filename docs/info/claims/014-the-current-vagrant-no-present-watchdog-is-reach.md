---
id: C014
kind: claim
status: holds
created: 2026-08-21
tags: boot,cd,re-04
depends: game/sync/vblank.cpp#vagrant_vblank_turn, game/recomp_seeds.json#main_reentry, tools/run.py#launch, external/psxport
---

## Claim

The current Vagrant no-present watchdog is reached from the first asynchronous sound-data read, not from a failed VBlank or reached frame loop.

## Evidence

2026-08-21: against pinned psxport 9f1bb927, scratch/logs/re05-pinned-final-irq-dma.log records the real HookEntryInt custom-exit route, repeated armed DMA4 callbacks, and guest VBlank counter 0x80032114 advancing 0 through 173. The watchdog stack is then _loadMenuSound 0x800468FC -> vs_main_diskLoadFile 0x8004493C -> vs_main_gametimeUpdate 0x8004261C -> VSync 0x8001F6C4. Matching retail source and resident call addresses identify the loop as the async CD-state poll.

## What would falsify it

if the default run completes the async read, reaches an overlay presenter, or the watchdog stack no longer contains this call chain

---
id: 14
title: Vagrant VSync waits forever because resident VBlank delivery is absent
status: resolved
symptom: watchdog reaches Sony VSync helper 0x8001F83C while guest counter 0x80032114 stays below its target
tags: boot,vsync,vblank,callback,re-10
created: 2026-08-21
updated: 2026-08-27
---

## Root cause

`startIntrVSync` at `0x8001FF94` clears the counter and callback table, then installs guest handler
`0x8001FFEC`. That handler is the only measured owner that increments `0x80032114`, and it also
dispatches all eight callbacks from `0x800320F4`. The static runtime supplied no display-field event,
so the intact guest handler never ran and Sony's wait helper could never observe its target.

## What was tried / dead ends

An HLE read window is the wrong mechanism: the waiter polls ordinary guest RAM, not an I/O register.
A native host-tick increment would make the symptom disappear while bypassing the guest callback
contract, so it was rejected.

## Resolution

Historical resolution, 2026-08-21: `game/sync/vblank.cpp` super-called `startIntrVSync` at the measured arming
boundary, then registers psxport's video-standard field clock to dispatch the intact guest handler.
The complete Sony route also restores setjmp buffer `0x80031084` to mid-function PC `0x8001FAD0`
through `HookEntryInt`; that address is now a measured `main_reentry` rather than a guessed function
seed. `tools/re_vblank.py` passes its 4/4 both-answer checks. The missing-seed negative fails exactly at
`0x8001FAD0`; the positive IRQ trace against pinned psxport `9f1bb927` reaches it, preserves armed
DMA4 callbacks, and advances the guest counter `0 -> 173` during the bounded run.

## Superseded product ownership

The historical route remains valid evidence for how the retail executable clears VSync waits, but it
is no longer a shipping solution. On 2026-08-27 the native-loop migration removed
`game/sync/vblank.*`, its host turn, guest handler dispatch, and the `0x8001FAD0` re-entry seed. The
product now binds measured VSync `0x8001F6C4` to the framework's mandatory fatal trap and gives field
ownership to `VagrantFrameDriver`. Issue 0028 owns the resulting honest gap: finite `_sysInit` and
TITLE/BATTLE phase work must be ported before the native path regains the old visible reach.

The first bounded native-loop launch turned that trap into a useful falsifier: it aborted at
`DsInit 0x800238C4 -> DS_init -> CD_init -> CD_cw -> CD_sync 0x80020F28 -> VSync(-1)` rather than
timing out. A second launch with that nested leaf owned then aborted at `CD_cw`'s own direct
VSync(-1), proving the outer `CD_cw 0x80021470` command is the correct synchronous boundary. Issue
0030 owns it; this issue remains resolved because no guest VSync path is permitted to resume or
silently succeed.

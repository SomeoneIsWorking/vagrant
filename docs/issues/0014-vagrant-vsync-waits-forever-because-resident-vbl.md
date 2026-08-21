---
id: 14
title: Vagrant VSync waits forever because resident VBlank delivery is absent
status: resolved
symptom: watchdog reaches Sony VSync helper 0x8001F83C while guest counter 0x80032114 stays below its target
tags: boot,vsync,vblank,callback,re-10
created: 2026-08-21
updated: 2026-08-21
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

Resolved 2026-08-21. `game/sync/vblank.cpp` super-calls `startIntrVSync` at the measured arming
boundary, then registers psxport's video-standard field clock to dispatch the intact guest handler.
`tools/re_vblank.py` passes its 3/3 both-answer checks; `scratch/logs/re10-final-default.log` shows counter
`0 -> 179` and progress into GPU/DMA work.

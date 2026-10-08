---
id: 14
title: Vagrant VSync waited forever because resident VBlank delivery was absent
status: resolved
symptom: the watchdog reached the Sony VSync helper 0x8001F83C while the guest counter 0x80032114 stayed below its target
tags: boot,vsync,vblank,callback,re-10
created: 2026-08-21
updated: 2026-08-27
---

`startIntrVSync 0x8001FF94` clears the counter and callback table, then installs guest handler
`0x8001FFEC` — the only measured owner that increments `0x80032114` and dispatches all eight callbacks
from `0x800320F4`. Without a display-field event the waiter could never observe its target. The
historical fix dispatched the intact guest handler from the platform field clock and restored setjmp
buffer `0x80031084` to `0x8001FAD0` through `HookEntryInt`.

**Dead ends:** an HLE read window (the waiter polls ordinary guest RAM, not an I/O register), and a
native host-tick increment (it hides the symptom while bypassing the guest callback contract).

That historical route is no longer the product: the native-loop migration removed it, VSync
`0x8001F6C4` is bound to the framework's mandatory fatal trap, and field ownership belongs to
`VagrantFrameDriver`. The bytes remain the evidence for how retail clears a VSync wait.

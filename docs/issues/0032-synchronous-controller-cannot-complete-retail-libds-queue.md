---
id: 32
title: Synchronous controller cannot complete retail asynchronous libds queue
status: resolved
symptom: Resident menu loads remain queued in ReadInit/Busy after synchronous CD commands return, so no file callback makes progress.
tags: S003,cd,libds,native-ownership,re-22
created: 2026-08-27
updated: 2026-08-27
---

## Root cause

Retail libds advances queued ReadN work from controller interrupts and command/data callbacks. The
current psxport CD contract completes operations inline and explicitly models no controller IRQ.
Calling the executable's finite status tick can retry commands, but cannot manufacture the missing
callback transition. Keeping the guest asynchronous queue under this contract therefore has no event
that can make its wait condition true.

## Resolution

`NativeFile` owns only executable-measured finite resident/TITLE extents. It reads the actual CHD's
2048-byte sectors, copies exactly the requested extent into guest RAM, and records overlay identity
after a complete slot load. `ResidentPhase` gives each completed copy an explicit host field before
applying the measured consumer. A serialized USA-CHD run copied all four menu-sound extents and
TITLE.PRG, then routed into TITLE `0x80071334`; no guest callback result is fabricated.

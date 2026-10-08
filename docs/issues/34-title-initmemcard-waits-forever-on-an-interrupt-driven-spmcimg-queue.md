---
id: 34
title: TITLE _initMemcard waited forever on the interrupt-driven SPMCIMG queue
status: resolved
symptom: 1000/1000 fields with no guest-VSync violation, but every capture from field 749 on was black and the save-check completion log was absent
tags: save,memcard,cd,re-23
created: 2026-08-24
updated: 2026-08-27
---

`_initMemcard` enqueues SPMCIMG.BIN and MCDATA.BIN+MCMAN.BIN through the retail asynchronous libds
queue; psxport completes CD commands synchronously and models no controller IRQ, so the callback that
marks those slots Loaded cannot run. The wait is BEFORE `_memcardEventHandler`, so it is not a
card-event bug.

**Dead ends:** faking queue completion and weakening guest VSync. The fix native-owns `_initMemcard` as
finite staged reads of the exact extents `(85144,0x1C000)` and `(85200,0x2000)` while preserving heap
allocation, the overlay pointer graph, the SPMCIMG upload, reset policy and the eight-event lifecycle.

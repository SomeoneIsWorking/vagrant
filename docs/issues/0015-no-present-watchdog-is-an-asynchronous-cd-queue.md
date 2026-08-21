---
id: 15
title: No-present watchdog is an asynchronous CD queue stall
status: investigating
symptom: Vagrant reaches the watchdog in VSync after resident VBlank works
tags: boot,cd,frame,watchdog,re-04,re-05
created: 2026-08-21
updated: 2026-08-21
---

Measured from scratch/logs/re05-pinned-final-irq-dma.log against pinned psxport `9f1bb927` after correct HookEntryInt unwind and the measured `0x8001FAD0` reentry: DMA4 callbacks remain armed and dispatch, counter 0x80032114 advances through 173 fields during the bounded run, and the live stack is _loadMenuSound 0x800468FC -> vs_main_diskLoadFile 0x8004493C -> vs_main_gametimeUpdate 0x8004261C -> VSync 0x8001F6C4. VBlank is not stuck. The read polling loop waits for the unowned asynchronous DsPacket/read-ready callback path. tools/re_frame.py separately proves the later TITLE/BATTLE overlay presenters and dynamic heap-backed buffers, but neither overlay is reached. Do not add a VBlank presenter now: it would suppress the watchdog while leaving the guest in an infinite CD poll. Proper next work is RE-04 async read plus true guest completion, then a reached presenter gate.

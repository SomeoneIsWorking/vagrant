---
id: 31
title: TITLE ClearImage reaches libgpu timeout-arm VSync query
status: resolved
symptom: Combined CHD launch aborts at VSync 0x8001F6C4 with return 0x8002AB94 from libgpu timeout arm 0x8002AB84 during TITLE reinitialisation.
tags: S003,frame-loop,vsync,gpu,title,native-ownership,re-21
created: 2026-08-27
updated: 2026-08-27
---

## Root cause

`ClearImage 0x800287D4` dispatches through the active libgpu command-queue owner `0x8002A3E8`, which calls timeout arm `0x8002AB84`. That arm queries VSync(-1) only to store a deadline 240 fields later at `0x80033580` and clear flag `0x80033584`. The host GPU executes the command synchronously, so the timeout clock must be platform-owned without dispatching guest VSync.

## Current work

`game/render/gpu_sync_facts.h` records the executable-derived leaf/globals. Vagrant uses psxport’s existing synchronous GPU-timeout owner in the fourth exact one-instruction HLE window. The production runtime test invokes the installed handler, proves the deadline/flag stores, and rejects the exact high endpoint. `tools/re_resident.py` uniquely derives the arm and globals and passes 6/6 controls. Clang product/runtime builds and full 7/7 CTest pass.

## Resolution

A serialized real-disc run crossed the exact arm without reaching adjacent timeout check
`0x8002ABB8`, continued through `_diskReset`, and copied all four menu-sound files. The next boundary
was libds file-completion ownership, not another GPU wait. The window remains deliberately exact.

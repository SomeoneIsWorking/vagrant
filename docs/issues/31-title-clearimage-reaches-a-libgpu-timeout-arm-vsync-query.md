---
id: 31
title: TITLE ClearImage reaches a libgpu timeout-arm VSync query
status: resolved
symptom: ClearImage dispatched through the libgpu command-queue owner into a timeout arm that queried VSync(-1)
tags: render,gpu,vsync,re-21
created: 2026-08-24
updated: 2026-08-24
---

`ClearImage 0x800287D4` dispatches through the active libgpu command-queue owner `0x8002A3E8`, which
calls timeout arm `0x8002AB84`. That arm queries VSync(-1) only to store a deadline 240 fields later at
`0x80033580` and clear flag `0x80033584`. The host GPU executes the command synchronously, so the clock
must be platform-owned without dispatching guest VSync.

**Dead end:** letting the guest wait on that VSync query — the host has already completed the command,
so the wait can only become a hang. The window stays deliberately exact (one instruction).

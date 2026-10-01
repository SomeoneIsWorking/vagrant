---
id: 3
title: crt0_setup never sets a1, so the BIOS InitHeap HLE builds a ZERO-SIZE heap
status: fixed
symptom: a guest whose crt0 initialises the heap through BIOS A0:0x39 InitHeap gets an arena of size 0 and Hle::heapAlloc returns 0 for every request
tags: framework,boot,heap,hle,re-01
created: 2026-08-12
updated: 2026-08-12
---

Fixed upstream in psxport: the boot group became a pure `crt0_plan` and `crt0_apply` sets `a1` beside
`a0`. **Do not work around it game-side** — a game-side heap fixup is exactly the "magic that makes
boot line up" this port must not accumulate.

Measured for this title: nothing in `SLUS_010.40` can call BIOS malloc. The only heap-related A0 thunk
in the image is `InitHeap` at `0x80026864`, called only by crt0 at `0x8001F5CC`, and there is no
`malloc`/`free`/`calloc`/`realloc` thunk anywhere. The game allocates from its own
`vs_main_initHeap` (`0x80043F74`) over an arena at `0x8010C000 + 0xF2000`, above the image's
`0x80062000` end, so the defect is inert here and this title cannot demonstrate the fix.

Verify after any framework change: `PSXPORT_DEBUG=bios` must show `A0:0x39(0x800401AC, 0x001BBE50, ...)`.

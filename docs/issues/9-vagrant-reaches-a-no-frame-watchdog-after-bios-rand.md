---
id: 9
title: Vagrant reaches a no-frame watchdog after BIOS rand
status: resolved
symptom: a bounded resident run reaches main and completes srand/rand, then the watchdog samples a store inside the polling path with no first frame
tags: boot,stall,sync,re-08
created: 2026-08-14
updated: 2026-08-14
---

The watchdog sampled a store inside the awaited condition, not the condition: the chain
`0x80044A60 -> 0x80025BE4 -> 0x8002411C -> 0x80020F28` is `_diskReset -> DsControlB -> DsSync ->
CD_sync`, and `_diskReset` waits for asynchronous `DslPause` completion.

**Dead ends:** treating the `Core::mem_w32` stack sample as a memory-store defect, and an HLE read
window for the waiter (it polls ordinary guest RAM, not an I/O register). A framework `fntrace` attempt
produced no trace because `fntrace_init` is not wired into the current boot path; the bytes and the
SHA-matching CC0 reference supplied the classification instead.

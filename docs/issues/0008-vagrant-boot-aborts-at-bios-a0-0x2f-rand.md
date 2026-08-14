---
id: 8
title: Vagrant boot aborts at BIOS A0:0x2F rand
status: resolved
symptom: After reaching guest main, Vagrant aborts at unimplemented BIOS A0:0x2F from caller 0x80042778
tags: framework,hle,libc,rand,boot
created: 2026-08-14
updated: 2026-08-14
---

## Root cause

The generic framework BIOS dispatcher implemented several libc leaves but not Sony libc `rand` and
`srand` (`A0:0x2F` and `A0:0x30`). Vagrant's `_initRand` at `0x8004274C` calls `srand(1)`, then calls
`rand()` exactly 97 times to fill `randArr[97]`; its linked stubs are `rand=0x80026EC4` and
`srand=0x80026ED4`. The fail-fast was therefore a missing generic HLE contract, not a Vagrant seed,
overlay, or generated-code defect.

## What was tried / dead ends

No Vagrant-specific override or host `rand()` was used. Host RNG state is process-global and its
sequence is implementation-defined, so it would couple two `Game` instances and break deterministic
SBS runs. The state belongs to each framework `Hle` instance.

## Resolution

Psxport commit `be03593f` implements the exact Sony libc LCG with unsigned 32-bit wrap:
`state = state*0x41C64E6D + 0x3039`, returning `(state>>16)&0x7FFF`; `srand` replaces that per-Game
state. A hermetic test reaches the shipping `Hle::dispatchBios` seam and checks the exact seed-1
sequence, restart, per-Game isolation, wrong-table refusal, and neighboring `A0:0x31` refusal.

Focused evidence: 3/3 cases, 21 checks; full psxport suite: 54/54. A Vagrant BIOS trace against that
framework records exactly one `A0:0x30` and 97 `A0:0x2F` calls, with no unimplemented-rand fatal. Boot
then advances to a no-frame watchdog; its sampled stack is in `Core::mem_w32` beneath generated
`0x8002411C` and callers. That later stall is not classified by this issue.

---
id: 8
title: Vagrant boot aborts at BIOS A0:0x2F rand
status: resolved
symptom: after reaching guest main, Vagrant aborted at unimplemented BIOS A0:0x2F from caller 0x80042778
tags: framework,hle,libc,rand,boot
created: 2026-08-14
updated: 2026-08-14
---

A missing generic HLE contract, not a Vagrant defect: `_initRand 0x8004274C` calls `srand(1)` then
`rand()` 97 times, and the framework implemented neither leaf. Fixed upstream by the exact Sony LCG
(`state = state*0x41C64E6D + 0x3039`, return `(state>>16)&0x7FFF`) in per-`Hle` state.

**Dead end:** a Vagrant-specific override or the host `rand()` was rejected — host RNG state is
process-global and implementation-defined, so it couples two `Game` instances and breaks deterministic
runs. The state belongs to each framework `Hle` instance.

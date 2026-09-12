---
id: 28
title: Native frame loop lacks call-coherent resident-to-TITLE guest continuation
status: investigating
symptom: Finite resident work loads authenticated TITLE, but the product has no call-coherent guest continuation from vs_main_exec through TITLE
tags: boot,frame-loop,vsync,title,battle,native-ownership
state_items: S003, S004, S006, S013
created: 2026-08-27
updated: 2026-09-12
---

## Root cause

Retail `vs_main_exec 0x80042C38` owns a non-returning chain: `__main`, `_sysInit`, TITLE, then
BATTLE. Those phase bodies contain Sony VSync waits and their own outer loops. Dispatching the whole
owner from `bootInit` therefore prevents the framework shell from iterating and makes guest VBlank
the effective field owner. The retired `vagrant_vblank_turn` hid that ownership inversion by
injecting the intact guest handler from a host turn.

## Current bounded slice

`VagrantRuntime::bootInit` still returns before the resident owner, and no process adapter connects
`ResidentPhase` to `VagrantFrameDriver`. The finite phase can acquire all 271 native TITLE sectors and
authenticate before publishing executable RAM; it then manually begins the splash after one host
field. Its leaf dispatch services inherit r31 rather than reproducing each retail JAL's callsite PC
and return address. The separate `enterTitle` synthetic contract checks the direct JAL and live image
generations, but the finite phase does not call it. No product TITLE guest reach is established.

The authenticated resident at `SLUS_010.40` SHA-1 `fababcfd4325d42f350d95b3472874affeb0e48c`
shows `vs_main_exec 0x80042C38` holding a 0x18-byte frame across `__main`, `_sysInit`, and the call to
`vs_main_execTitle` at `0x80042C5C` (return `0x80042C64`). The latter holds its own 0x18-byte frame,
sets s0 to `0x8005DFD0`, calls `OverlayGetSp(s0)`, `_sysReinit`, `_loadTitlePrg`, then JALs to TITLE
`0x80071334` from `0x80042BD8` (return `0x80042BE0`). The finite phase currently omits those two
outer frames and the second `OverlayGetSp`; adding only those stack effects would leave the guest
return path wrong. `tools/re_resident.py --check-source --selftest` now follows the shipping
`readAndLoadTitle` boundary and refuses a broken TITLE publication path.

## Next proof

Recover the measured callsite PC, return address, saved-register, and live-frame contract across
each finite guest leaf from `vs_main_exec` through `vs_main_execTitle`; compose it with the direct
TITLE JAL and a finite native field yield. The synthetic shipping-path test must traverse that
sequence with valid resident/TITLE generations and refuse a wrong return PC or stale identity. Only
then connect the process adapter and use a real run to discriminate the next guest-owned wait. Do
not dispatch a non-returning TITLE/VSync owner or substitute stack-only state for continuation.

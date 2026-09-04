---
id: 28
title: Native frame loop stops before finite resident/TITLE phase work exists
status: investigating
symptom: The native product owns finite fields and rejects guest VSync, but boot returns at vs_main_exec before _sysInit or TITLE work advances
tags: boot,frame-loop,vsync,title,battle,native-ownership
state_items: S003, S004, S006, S013
created: 2026-08-27
updated: 2026-08-27
---

## Root cause

Retail `vs_main_exec 0x80042C38` owns a non-returning chain: `__main`, `_sysInit`, TITLE, then
BATTLE. Those phase bodies contain Sony VSync waits and their own outer loops. Dispatching the whole
owner from `bootInit` therefore prevents the framework shell from iterating and makes guest VBlank
the effective field owner. The retired `vagrant_vblank_turn` hid that ownership inversion by
injecting the intact guest handler from a host turn.

## Current bounded slice

`VagrantRuntime::bootInit` now returns at the measured `vs_main_exec` boundary instead of dispatching
it. `VagrantFrameDriver` owns one finite field in the existing framework shell: host frame index,
measured pad delivery, SPU/audio service, resident/TITLE/BATTLE completed-producer arbitration,
exactly one presentation commit, and one field pace. Sony VSync `0x8001F6C4` is bound to psxport's
mandatory fatal handler through a one-instruction measured HLE window. The guest VBlank override,
host-turn registration, handler dispatch, and obsolete `0x8001FAD0` re-entry seed are removed.

This slice compiles with Clang and its hermetic runtime contract plus `tools/re_vblank.py` 5/5
controlled negatives pass. It was not launched. It intentionally does not claim TITLE or BATTLE
reach: the native loop currently presents the resident fallback field because no finite guest phase
work has run to publish a completed producer.

## Next proof

Port `_sysInit` as finite native-owned operations in exact retail order, replacing every internal
VSync dependency with the enclosing host field boundary rather than skipping side effects. Then
extract the first TITLE outer iteration so one `stepFrame` performs bounded game work and returns.
The first product run must show either a completed TITLE producer and one commit in the same field or
a precise fatal at the next guest VSync/coupled phase boundary. It must not restore a guest handler,
fabricate counter `0x80032114`, or dispatch a non-returning outer owner.

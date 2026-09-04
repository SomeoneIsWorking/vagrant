---
id: 33
title: TITLE post-splash field reaches guest gametimeUpdate VSync(2)
status: resolved
symptom: After both 364-field publisher/developer loops complete, the exact native product aborts at guest VSync 0x8001F6C4 with a0=2 and ra=0x80042634.
tags: S003,S004,S006,S013,title,frame-loop,vsync,native-ownership,re-22,next-boundary
created: 2026-08-27
updated: 2026-08-27
---

## Live evidence

Exact psxport `3c342ec3` Clang product PID 3180949 completed 728 native TITLE sprite fields and
seven visual captures. It then hit the mandatory guest-VSync fatal trap. The backtrace is TITLE owner
`0x8006E988 -> gametimeUpdate 0x8004261C -> VSync(2) 0x8001F6C4`, return `0x80042634`. Log:
`scratch/logs/vagrant-3c342ec3-live.log`.

## Root cause

The publisher/developer splash ownership is complete. The next TITLE continuation still calls the
resident `gametimeUpdate` owner, whose retail body waits two display fields through guest VSync. This
is an unowned top-down field boundary, not a framework ABI crash.

## Proper fix

Measure the exact TITLE caller continuation and finite `gametimeUpdate` work, then extend the
title/resident phase owner so those two fields are serviced by `VagrantFrameDriver`. Keep VSync
fatal; do not no-op or widen the primitive binding.

### Resolution (2026-08-27)
Exact 3c342ec3 Clang product PID 3213121 completed 1000/1000 native fields with no guest-VSync violation; the former 0x8004261C boundary is removed. The run exposed distinct issue 0034 inside _initMemcard.

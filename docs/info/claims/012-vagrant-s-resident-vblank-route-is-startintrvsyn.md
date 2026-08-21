---
id: C012
kind: claim
status: holds
created: 2026-08-21
tags: re-10,vsync,vblank,boot
depends: tools/re_vblank.py#measure, game/sync/vblank.cpp#vagrant_start_intr_vsync
reconfirmed: 2026-08-21 03:31:41
verified_at: 2026-08-21 03:31:41
---

## Claim

Vagrant's resident VBlank route is startIntrVSync 0x8001FF94 -> guest handler 0x8001FFEC -> counter 0x80032114 and eight callbacks at 0x800320F4; delivering display fields through that intact handler clears Sony VSync waits without host-owned counter semantics

## Evidence

tools/re_vblank.py uniquely derives and gates the route from SHA-verified SLUS_010.40 with a 3/3 both-answer selftest; scratch/logs/re10-final-default.log records guest counter 0 -> 179, GP1 video-standard setup, and later DMA work

## What would falsify it

if the same SHA-bound executable's measured handler does not increment 0x80032114/dispatch 0x800320F4, or a real run with fields delivered through 0x8001FFEC leaves the VSync target uncleared

## Re-confirmed 2026-08-21 03:31:41

Final tools/re_vblank.py --check-source --selftest passed 3/3; real no-argument scratch/logs/re10-final-default.log records 179 intact guest-handler counter transitions, GP1 setup, DMA work, and no recompilation miss/BIOS fatal

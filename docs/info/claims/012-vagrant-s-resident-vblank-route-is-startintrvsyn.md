---
id: C012
kind: claim
status: holds
created: 2026-08-21
tags: re-10,vsync,vblank,boot
depends: tools/re_vblank.py#measure, game/sync/vblank.cpp#vagrant_start_intr_vsync, game/recomp_seeds.json#main_reentry, external/psxport
reconfirmed: 2026-08-21
verified_at: 2026-08-21 11:17:52
---

## Claim

Vagrant's resident VBlank route is startIntrVSync 0x8001FF94 -> guest handler 0x8001FFEC -> counter 0x80032114 and eight callbacks at 0x800320F4; delivering display fields through that intact handler clears Sony VSync waits without host-owned counter semantics

## Evidence

tools/re_vblank.py uniquely derives and gates the route from SHA-verified SLUS_010.40 with a 4/4 both-answer selftest, including setjmp buffer 0x80031084 -> restored PC 0x8001FAD0 and HookEntryInt 0x80026954; against pinned psxport 9f1bb927, scratch/logs/re05-pinned-final-irq-dma.log records the restored entry, armed DMA4 callbacks, guest counter 0 -> 173, and the downstream asynchronous-CD stack

## What would falsify it

if the same SHA-bound executable's measured handler does not increment 0x80032114/dispatch 0x800320F4, or a real run with fields delivered through 0x8001FFEC leaves the VSync target uncleared

## Re-confirmed 2026-08-21 03:31:41

Final tools/re_vblank.py --check-source --selftest passed 3/3; real no-argument scratch/logs/re10-final-default.log records 179 intact guest-handler counter transitions, GP1 setup, DMA work, and no recompilation miss/BIOS fatal

## Re-confirmed 2026-08-21 03:34:12

Final expanded tools/re_vblank.py derives and cross-checks callback wrapper 0x8001F904 against VSyncCallback's vector, and its --check-source --selftest remains 3/3; scratch/logs/re10-final-default.log records 179 intact guest-handler transitions and later GPU/DMA work

## Re-confirmed 2026-08-21 03:34:14

Post-landing tools/re_vblank.py --check-source --selftest passed 3/3; constants and shipping handler/super-call/field-rate wiring all match the SHA-bound executable.

## Re-confirmed 2026-08-21 03:34:49

Post-landing 3/3 executable-backed VBlank gate also proved startIntrVSync callback wrapper 0x8001F904 uses the same callback vector as public VSyncCallback.

## Re-confirmed 2026-08-21

Correct HookEntryInt delivery exposed the saved setjmp PC as a genuine mid-function recompilation entry. tools/re_vblank.py now derives buffer 0x80031084, PC 0x8001FAD0, and HookEntryInt 0x80026954 and rejects the missing seed (4/4). The forced negative scratch/logs/re05-reentry.log fails exactly at 0x8001FAD0; with the emitter's main_reentry discovery fixed and pinned at psxport 9f1bb927, scratch/logs/re05-pinned-final-irq-dma.log reaches that entry and advances the intact VBlank counter through 173 without a recompilation miss.

## Re-confirmed 2026-08-21

Post-landing re_vblank passed 4/4; pinned runtime restored 0x8001FAD0, kept DMA4 callbacks armed, and advanced guest VBlank 0 through 173.

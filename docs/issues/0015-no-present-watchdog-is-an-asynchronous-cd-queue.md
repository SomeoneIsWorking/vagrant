---
id: 15
title: No-present watchdog is an asynchronous CD queue stall
status: resolved
symptom: Vagrant reaches the watchdog in VSync after resident VBlank works
tags: boot,cd,frame,watchdog,re-04,re-05
created: 2026-08-21
updated: 2026-08-21
---

Measured from `scratch/logs/re05-pinned-final-irq-dma.log` against pinned psxport `9f1bb927` after
correct HookEntryInt unwind and the measured `0x8001FAD0` reentry: DMA4 callbacks remain armed and
dispatch, counter `0x80032114` advances through 173 fields during the bounded run, and the live stack
is `_loadMenuSound 0x800468FC -> vs_main_diskLoadFile 0x8004493C ->
vs_main_gametimeUpdate 0x8004261C -> VSync 0x8001F6C4`. VBlank is not stuck.

The original diagnosis that the asynchronous data completion never arrives was too broad.
`tools/re_async_cd.py --selftest` derives the executable's complete resident contract and rejects
three independent mutations with searched denominators. Runtime traces then establish this order:

1. `scratch/logs/re11-shared-cdc.log` consumes exactly 17 data sectors, LBA 63000 through 63016,
   through the guest's three-header-word plus 512-word DMA3 path.
2. `scratch/logs/re11-paced-fntrace.log` enters `_diskReadCallback 0x80043FB4` for all 17 sectors.
   The final callback stores the resident disk state `0x80055D10` idle, calls
   `DsEndReadySystem 0x800262E8`, and queues `DsCommand(Pause=9)` before the next
   `vs_main_diskLoadFile` request begins.
3. `scratch/logs/re11-paced-libds-state-range.log` shows the active ReadN command state
   `0x800326A0=0x11` and system state `0x8003269C=Busy(2)` never leave those values; queue length
   `0x80039DB8` becomes one. `scratch/logs/re11-paced-libds-trace.log` never enters queue dispatcher
   `0x800235A4`, so no post-read controller Pause command is issued.
4. INT1 handler `0x8002559C` calls status decoder `0x80025630`, which maps raw status bit `0x20`
   (libcd's `CdlStatRead`) into decoded byte `0x800326B2`. The resident VBlank callback at
   `0x80024BDC` checks that byte when system state is Busy and command state is ReadN `0x11`; only a
   true value changes system state to idle and command state to `0x0B`. The live controller returns
   raw status `0x80032694=0x02`, so decoded read-active remains false. A real reading drive reports
   `0x22` (`CdlStatRead | CdlStatStandby`), allowing that transition and subsequent Pause dispatch.

The isolated drive-pacing candidate was an explicit falsifier, not a fix:
`scratch/logs/re11-paced-cdc-runtime.log` delays the following INT1 until after the final data
callback, but that stale ready event still arrives while ReadN remains active. The same `0x11` /
Busy / queued-Pause state and repeated Getstat loop follow. Timing the event alone is insufficient;
the shared controller must reproduce the ReadN status transition that allows libds to finish
ReadN and dispatch Pause.

This evidence ruled out adding a VBlank presenter, synthesizing file completion, forcing libds idle,
or weakening the watchdog: each would have concealed the failed CD arbitration while leaving guest
state wrong. The resolution below fixes the shared controller instead and moves the live boundary to
the separately recorded TITLE overlay-emission gap.

### Resolution (2026-08-21)
Resolved and reconfirmed against pinned psxport 3418a79b. Deterministic guest-cycle drive deadlines plus active-read INT1 status 0x22 let the intact guest VBlank callback set libds idle and dispatch queued Pause; the pinned default run completes four WAVE reads and all 271 TITLE.PRG sectors, then reaches the separate overlay-emission miss 0x80071334 recorded as issue #16.

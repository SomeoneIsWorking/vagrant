---
id: 15
title: No-present watchdog is an asynchronous CD queue stall
status: resolved
symptom: Vagrant reached the watchdog in VSync after resident VBlank worked
tags: boot,cd,frame,watchdog,re-04,re-05
created: 2026-08-21
updated: 2026-08-21
---

VBlank was NOT stuck: DMA4 callbacks stayed armed, the counter advanced through 173 fields, and the
live stack was `_loadMenuSound -> vs_main_diskLoadFile -> vs_main_gametimeUpdate -> VSync`. The stall
is libds: after the last data callback the ReadN command state `0x800326A0=0x11` and system state
`0x8003269C=Busy(2)` never leave those values, and the queue dispatcher `0x800235A4` is never entered,
so the post-read controller Pause is never issued. The resident VBlank callback at `0x80024BDC` only
clears that state when the decoded read-active byte `0x800326B2` is true, and the live controller
returns raw status `0x02` where a real drive returns `0x22` (`CdlStatRead | CdlStatStandby`).

**Dead ends:** the original "asynchronous data completion never arrives" diagnosis was too broad
(sectors are delivered through DMA3 for all 17 reads), and delaying INT1 until after the final data
callback did not help — the stale ready event still arrived while ReadN remained active.

---
id: 19
title: TITLE menu DrawPrim queue had no completed-pass presentation fence
status: resolved
symptom: after Start skipped the intro, TITLE repeatedly submitted menu primitives until RenderQueue reached 65,536 items and no menu was presented
tags: title,render,re-14
created: 2026-08-22
updated: 2026-08-22
---

`_drawTitleMenu 0x8007093C` renders two display-buffer passes through `_drawTitleMenuItems
0x800705AC`; no producer owned that pass, so VBlank never flushed it and the queue accumulated to the
fail-fast bound. `TitleMenuProducer` super-calls the measured leaf, marks the guest pass complete, and
commits through the neutral presenter at the next intact guest VBlank — it creates no menu pixels.
The proof shape is the disabled-producer control: same transition, same super-call, exact 65,536-item
fail-fast with the same-index present absent.

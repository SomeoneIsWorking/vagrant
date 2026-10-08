---
id: 18
title: Decoded TITLE intro frames never reach native presentation
status: resolved
symptom: TITLE completed MDEC DMA1 callbacks and uploaded RGB24 slices to guest VRAM, but the run presented nothing after the splashes
tags: render,title,mdec,fmv,re-13,native-producer
created: 2026-08-22
updated: 2026-08-22
---

The guest libpress path decoded and uploaded every slice correctly; only the host present was missing,
so `MovieData::frameComplete` could become true with no host present request. The owner retains the
callback super-call, latches the measured frame-complete boundary, and presents the live
guest-selected VRAM scanout — it never re-decodes the STR.

**Dead ends:** treating the 24-bit transition as a present trigger (it describes display mode, not
frame ownership, and would expose incomplete slices), and supplying a canned frame (the intact guest
MDEC path already owns those pixels).

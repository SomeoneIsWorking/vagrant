---
id: 17
title: TITLE executes but no title picture is presented
status: resolved
symptom: after TITLE overlay routing succeeded, a headless boot captured only the initial black present and then spent 15-30 s in TITLE image-upload/intro-stream work without another present
tags: render,title,overlay,performance,native-producer
created: 2026-08-22
updated: 2026-08-22
---

TITLE's first publisher/developer picture is submitted through immediate sprite leaf `0x8006A778`
(static packet `0x800DED28`, owner `0x8006F54C`), and native mode had no producer translating that
guest operation. Overlay execution and VRAM uploads alone cannot produce a native frame.

**Dead ends:** longer 15- and 30-second runs still captured only the initial black present, so raising
or disabling the watchdog was falsified as a rendering fix, and successful guest overlay execution is
not evidence of direct native production. The real fix was a semantic producer plus a presenter at the
guest-owned VBlank boundary, with a disabled-producer control that yields a uniformly black frame.

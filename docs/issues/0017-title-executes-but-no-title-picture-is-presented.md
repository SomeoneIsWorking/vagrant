---
id: 17
title: TITLE executes but no title picture is presented
status: resolved
symptom: after TITLE overlay routing succeeds, headless boot captures only the initial black present and then spends 15-30 seconds in title image-upload/intro-stream GPU/CD work without another presented frame
tags: render,title,overlay,performance,native-producer
created: 2026-08-22
updated: 2026-08-22
---

## Root cause

TITLE's first publisher/developer picture is submitted through immediate sprite leaf `0x8006A778`,
but native mode had no producer translating that guest semantic operation and no presenter at the
guest-owned VBlank boundary. Overlay execution and VRAM uploads alone cannot produce a native frame.

## What was tried / dead ends

Longer 15- and 30-second runs advanced through TITLE GPU/CD work but still captured only the initial
black framework present. Raising or disabling the watchdog was therefore falsified as a rendering
fix; successful guest overlay execution is not evidence of direct native production.

## Resolution

`tools/re_title_startup.py` SHA-derives the leaf, static packet `0x800DED28`, owner `0x8006F54C`,
and its two live calls. `VagrantRuntime` installs an override that super-calls the intact generated
body, decodes its ABI into a per-Core `TitleStartupProducer`, and presents the live guest VRAM texture
at VBlank. Owned-disc capture `scratch/screenshots/re12/positive_present_8.ppm` is
29,499/691,200 non-black (4.27%) and legibly says “Published by Square Electronic Arts L.L.C.” A
separately compiled test-only disabled-producer control retains the super-call but produces uniformly
black `scratch/screenshots/re12/negative_present_1.ppm` and no second present.

This resolves first-picture absence only. After the two splash loops, GP1 switches to 24-bit and the
next boundary is TITLE's intro/MDEC/FMV path, which watchdogs without a further present (RE-13).

---
id: 19
title: TITLE menu DrawPrim queue has no completed-pass presentation fence
status: resolved
symptom: After Start skips the intro and _initTitleScreen switches to 15-bit, TITLE repeatedly submits menu primitives until RenderQueue reaches 65536 items; no title menu is presented.
tags: title,render,re-14
created: 2026-08-22
updated: 2026-08-22
---

## Root cause

TITLE `_drawTitleMenu` (`0x8007093C`) renders two display-buffer passes with immediate `DrawPrim` calls through `_drawTitleMenuItems` (`0x800705AC`). The runtime had semantic producers only for the startup sprite and MDEC movie callback. Neither owned the menu pass, so VBlank never flushed or committed these guest-generated primitives; repeated menu passes accumulated until the fail-fast 65,536-item queue bound.

## Fix

`TitleMenuProducer` retains and super-calls the measured `_drawTitleMenuItems` leaf, marks that guest pass complete, then flushes the existing queue and commits it through the neutral presenter at the next intact guest VBlank. It does not create menu pixels or replace DrawPrim. `tools/re_title_menu.py` uniquely derives the owner/callee from SHA-bound TITLE.PRG and passes 3/3 destructive controls.

## Evidence

Against psxport d2266f4b and the owned SLUS_010.40 disc, shipping `scratch/logs/re14_menu_positive_d2266f4b.log` switches 24-bit -> 15-bit 512x224, repeatedly reports completed menu passes, and `scratch/screenshots/re14/positive_d2266f4b_menu_present_64.ppm` is readable at 241,809/691,200 nonblack pixels. The test-only `VAGRANT_TEST_DISABLE_TITLE_MENU_PRODUCER` build retains the generated super-call and same transition but reaches the exact 65,536-item fail-fast with same-index present 64 absent (`scratch/logs/re14_menu_producer_disabled_d2266f4b.log`).

## Next boundary

The shipping run next fails honestly at missing TITLE function `0x800798A4` from caller `0x80042C14`; no later menu interaction or stream teardown is claimed.

---
id: 35
title: TITLE stops at _initIntroMovie boundary with partial lower-right texture
status: investigating
symptom: After finite save/memcard initialization completes, the exact product reaches _initIntroMovie but subsequent fields show a stable partial texture strip at the lower-right instead of a proper intro frame.
tags: S003,S004,S013,title,intro,movie,presentation,native-ownership,re-23
created: 2026-08-27
updated: 2026-08-27
---

## Live evidence

Exact psxport `3c342ec3` Clang product PID 3309285 copied SPMCIMG `(85144,0x1C000)` and contiguous MCDATA+MCMAN `(85200,0x2000)`, then logged `TITLE save-file check completed; next owner is _initIntroMovie`. The bounded run reconciled 1000/1000 fields with zero drops and no guest-VSync violation. Captures at fields 749, 750, 752, 760, 800, 900, and 950 are stable at 35,160/691,200 non-black pixels. Visual inspection of `scratch/screenshots/viewable/vagrant-memcard-resume-739-741-749.png` shows a small malformed/partial texture strip at the lower-right, not a valid intro frame.

## Root cause

The native resident phase deliberately stops at `TitleIntroBoundary`; `_initIntroMovie` and its first completed presentation boundary are not yet owned. `copyTitleBgData` executes before that stop and changes VRAM, but no semantic intro producer or finite movie initialization follows, so the partial texture is not evidence of a working intro.

## Proper fix

Measure `_initIntroMovie` top-down from the SHA-bound TITLE overlay, preserve every finite non-VSync state transition and restricted-byte load, then resume through host-owned fields into the existing retained-super movie producer. Keep guest VSync globally fatal and verify the first actual intro frame visually on the real disc.

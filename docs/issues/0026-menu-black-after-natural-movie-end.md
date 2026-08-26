---
id: 26
title: Menu renders black when the intro movie ends NATURALLY (skip path renders fine)
status: resolved
symptom: Saved captures were initially classified as black TITLE-menu frames after natural movie completion
tags: menu,render,misclassification,re-16
state_items: S005
created: 2026-08-26
updated: 2026-08-26
---

## Resolution

The saved black captures do not establish a black natural-end menu. They occur after the recorded
input has left the idle natural path and after the renderer has changed from TITLE to BATTLE:

- `scratch/vs-natural.pad` is idle through frame 5,899, then presses active-low Cross at
  5,900–5,911, 6,400–6,411, 6,900–6,911, and 7,400–7,411.
- `scratch/logs/rqhist.log` names that replay and records the 792–1,683-primitive TITLE batches before
  they switch to repeated 24-primitive batches.
- `scratch/logs/prims_f6600.csv`, previously called a menu frame, contains the small BATTLE/loading
  batch: black full-screen polygons, item sprites using BATTLE CLUT/page coordinates, and white
  semitransparent quads. It is not the 1,400-plus-sprite TITLE menu batch.
- The stored no-input `vs-idle.pad` black captures likewise use the later 320x224 BATTLE display,
  not TITLE's 512x224 display.
- Images at 4,000/4,300/6,600 that visibly show the menu came from `vs-skip.pad`/`vs-drive.pad`;
  `vs-drive.pad` presses Start at frame 1,800. They are valid skip controls, not natural controls.

The original issue combined a real natural-return question with a later BATTLE picture. The retail
control-flow result remains valid: `tools/re_title_natural.py` proves natural return `0` and
Start/right return `1` converge at `0x8006FC0C`, and the sole caller ignores `v0` before the common
title-screen/menu initialization chain. But no correctly-provenanced natural-end menu screenshot has
yet been captured, so this resolution does not claim one.

The actual visible frontier is tracked as issue #27: the replay reaches BATTLE/loading, whose native
world producer and live picture are not yet verified.

### Earlier dead end

The earlier theory that natural return selects a distinct caller/menu/fade branch remains ruled out.
SHA-bound `tools/re_title_natural.py` measures natural `v0=0` and Start/right `v0=1` converging at
epilogue `0x8006FC0C`; the sole caller `0x800713DC` ignores `v0` and enters the same
`initTitleScreen`/`SetDispMask(1)`/`initMenu` chain (C028, I020, RE-16).

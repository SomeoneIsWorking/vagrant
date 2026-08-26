---
id: 26
title: Menu renders black when the intro movie ends NATURALLY (skip path renders fine)
status: open
symptom: With the intro allowed to play to its natural end, the title menu's logic runs and presents (2200 "presented completed TITLE menu" fields) but every captured frame is black in BOTH sinks; with Start-skip the same menu renders perfectly on the SAME substrate
tags: menu,render,user-facing,next-boundary
created: 2026-08-26
updated: 2026-08-26
---

## Evidence matrix (all on psxport 54af32cb, RECOMP 2026-08-26.14, unless noted)

| generated | fallback commit | movie | menu picture |
|---|---|---|---|
| cab5d077-emitted | OFF | skip | RENDERS (bisect-cab2, scratch/screenshots/cell2_4000.png era) |
| cab5d077-emitted | ON | skip | RENDERS (cell2_4000.png) |
| 54af32cb-emitted | ON | skip | RENDERS (headskip_4000.png) |
| 54af32cb-emitted | ON/OFF | natural | BLACK (pad5/pad6/idle-shots, windowed win-shot.log) |

The emitter (54af32cb) and the vagrant fallback commit are BOTH innocent: the generated-code
diff cab5→HEAD is exactly the 11 BATTLE tail sites (resident/TITLE byte-identical,
scratch/generated-cab5 vs scratch/generated-head14), and cab5-generated renders the menu with
the fallback either way. The decisive variable is SKIP vs NATURAL movie end.

## Measured at the black menu (natural end)

* Menu LOGIC is alive: menu presents fire every completed pass; X input reaches New Game
  (pad2: zone-load Setloc [57 25 56] fired).
* RenderQueue has real content per field (rqhist: n=24 — 6 bg opaque + 17 hud + 1 semi).
* Prim CSV at f6600 (scratch/logs/prims_f6600.csv): 32 full-screen op=0x30 rgb=0 flat tris
  (opaque black) + 60 textured item quads (page 768,0; CLUTs 832/864,223) + 4 white semi quads.
* VRAM is FINE: PSXPORT_VRAMDUMP=6600 shows the logo, artwork, fonts, "NOW LOADING.." text;
  both CLUTs are populated gradient ramps (scratch/vram6600_view.png).
* The composite is black anyway, in headless AND windowed.

## Candidate causes (unranked)

1. The natural-end teardown leaves a full-screen opaque black layer (the movie fade-out?)
  permanently composited OVER the menu — on hardware the same layer is removed or semi.
2. The menu's own fade-in from black never advances when the movie ended naturally (its clock
  may be the movie player's, which was skipped/aborted differently).
3. Tonight's wall-locked CDC clock changed the natural-end timing path (only natural completion
  became POSSIBLE tonight — the movie froze pre-#25-fix, so this path was NEVER exercised
  before 2026-08-26; it may have been broken for a long time).

## Workaround (ships today)

Press Start during the intro (the authentic player behaviour anyway): the skip path renders the
menu correctly on the current substrate, and New Game/Continue work from there.

## Required resolution

A natural-end run's menu frame must match the skip run's menu frame byte-for-byte at the same
menu-state. Falsifier: PSXPORT_PAD_SHOT_AT on a natural-end replay shows the menu.

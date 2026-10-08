---
id: 37
title: Vagrant Story had no widescreen owner, and the projection distance is gameplay state
status: open
symptom: S010 (true widescreen) had no owner in this tree, and no adapter or disc image
tags: S010,S015,widescreen,projection,decomp
created: 2026-09-27
updated: 2026-09-27
---

## What was built

`vagrant::BattleProjectionOwner` (`game/render/battle_projection.{h,cpp}`), registered through the
per-Core `psx::cpu::NativeDispatcher` from `VagrantRuntime::loadResidentImage` — the only boundary at
which the resident image exists. `VagrantContext` holds the owner per Core.

It owns the four **resident** SDK leaves, not the overlay call site: BATTLE's presenter
`0x8007629C` re-states a literal `SetGeomOffset(160, 112)` every field, so an owner on the overlay's
call would be overwritten 60 times a second. The leaves are `SetGeomOffset 0x80041540`,
`SetGeomScreen 0x80041534`, `SetDefDrawEnv 0x8002B374`, `SetDefDispEnv 0x8002B434`.

It refuses rather than guesses, in five places, each with a positive test:

1. the GTE control register and the framework's record of the leaf's argument must agree;
2. the leaf's recorded value must equal its own argument register;
3. the guest's own viewport rectangle must agree with the width being published;
4. registration resolves every leaf against the image catalog before installing any, and refuses an
   identity this Core did not publish (BATTLE, TITLE and ENDING all reuse `0x80068800`);
5. `derive()` refuses an incomplete publication, a centre that is not the half of the stated width, a
   plan that widens the projection but not the clip, a clip past the widened width, and an off-centre
   frustum.

`derive()` is pure and its 4:3 arm is the identity by construction. A wide plan derives
214 / 428 / 427 from a measured 160 / 320 / 319.

## What the decompilation census established (bounded claim)

| word | writes | reads | the readers |
|---|---|---|---|
| `D_8005DFD6` (published width) | 2 | 1 | `func_800BB874`, a screen-space `LINE_F2` scanline effect — **not a cull** |
| `vs_main_projectionDistance` | 4 | 14 | camera transition, two threshold branches, zoom, fog, menus |
| `vs_main_nearClip` (`0x8005E0C8`) | 2 | 3 | camera transition only |

No screen-space horizontal cull was found in the decompiled part; the room renderer is largely
undecompiled, so this is a bounded claim, not an absence claim.

**The real hazard is gameplay.** `vs_main_projectionDistance` (`0x8005E248`, setter `0x8007CCF0`) is
branched on against 272 and scales the GTE fog. A widening that raised the global would flip a
gameplay decision, so this owner widens the *canvas* and never `H`, and the threshold is a shipped
constant rather than a comment.

## The boundary that stops a widening

A widening is the **pair** (centre, clip). The centre is derivable at a resident leaf; the clip is
published from a VRAM layout whose consequence had not been re-derived from bytes at the time this was
written (issue 0038 corrected that reason). `VagrantRuntime::guestWidescreenProjection()` therefore
stays deliberately not overridden: the framework resolves this title's guest projection at
`Standard4x3`, so a cropped frame cannot reach the screen under a wide claim.

## What remains

- **S010 is still `missing`.** This issue adds the owner, the derivation and the refusals. It does not
  widen a frame.
- Own the display-resolution and VRAM-layout publication, which is what widening would have to move.
- `func_800BB874`'s scanline effect would still span 320 px on a 428 px frame; owning it needs its
  undecompiled body.
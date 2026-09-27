---
id: 37
title: Vagrant Story had no widescreen owner, and the projection distance is gameplay state
status: open
symptom: `docs/project-state.md` records S010 (true widescreen) as `missing` and the workspace measurement of 2026-09-27 counted 0 widescreen owner files in this tree, with no dynarec adapter and no disc provisioned.
tags: S010,S015,RE-13,widescreen,projection,decomp
created: 2026-09-27
updated: 2026-09-27
---

## What was found, and how it was found

`tools/re_projection.py` is the new supply instrument. It reads the vendored CC0 `rood-reverse`
decompilation — so it runs with **no game image** — and reports, with a file/line citation and a
denominator, which decompiled sites write and which read the words that hold a horizontal extent or a
projection parameter. It also gates every address this repository ships against the decompilation's
own per-module symbol map.

It states on every run that it is reading a **reconstruction**, and that a zero means "no decompiled
site names this word", never "the guest has no such site". It prints the text-segment extent of the
modules it covers so the reader can see how much of BATTLE.PRG the answer is drawn from. Measured
coverage: 289 files, 102,677 lines, against a BATTLE.PRG text segment of 517,400 bytes and a
SLUS_010.40 text segment of 399,340 bytes — so the decompiled part is a minority of both.

### 1. The projection publication owner

**BATTLE.PRG's `func_800760CC`, guest address `0x800760CC` — in an OVERLAY, not the boot
executable.** BATTLE.PRG loads at `0x80068800`; 933,925 bytes of this title's code live in `.PRG`
overlays, and this is one of them.

It states the whole viewport in one call: `SetGeomOffset(arg0 / 2, …)`, `SetGeomScreen(arg2)`, both
draw areas, both display areas, both screen rectangles, and the resident viewport rectangle
`0x8005DFD4`. It is called as `(320, 240, vs_main_projectionDistance, 0, 0, 0)` from BATTLE.PRG and
from INITBTL.PRG.

Confidence: **high for the address, medium for the body.** `docs/battle-rendering.md` already records
`0x800760CC` as the viewport initializer measured from BATTLE.PRG bytes by `tools/re_frame.py`, and
the decompilation independently names the same address `func_800760CC`. Two independent sources, one
of which read the actual bytes. The *bodies* are the decompilation's reconstruction; no instruction
word of it was read here, and none could be — there is no image on this machine.

### 2. Is there a horizontal cull? No — but the projection distance is gameplay state

The census result, with the denominators:

| word | writes | reads | the readers |
|---|---|---|---|
| `D_8005DFD6` (the published width) | 2 | **1** | `func_800BB874` at `4A0A8.c:2741`, `var_s3->x1 = D_8005DFD6;` |
| `D_8005DFDA` (the published height) | 2 | **1** | `func_800BB874` at `4A0A8.c:2731`, a per-scanline loop bound |
| `vs_main_projectionDistance` | 4 | 14 | camera transition, two threshold branches, zoom, fog, menus |
| `vs_main_nearClip` | 2 | 3 | camera transition only |

**There is exactly ONE decompiled reader of the title's own horizontal extent, and it is not a cull.**
`func_800BB874` emits `LINE_F2` primitives from `x0 = 0` to `x1 = D_8005DFD6` on each of
`D_8005DFDA` scanlines — a screen-space effect. A widening that leaves that word at 320 leaves this
effect 320 px wide on a 428 px frame, which is a visible cosmetic gap, not a cull.

**No screen-space horizontal cull was found, and this is a bounded claim, not an absence claim.** No
GTE control-register reader of OFX/OFY/H appears anywhere in the decompilation, and no projected-X
comparison against a screen bound does either. But the room renderer is largely **not decompiled** —
`func_80098160`, the near-clip consumer, is *named in the module map and has no body*. So the honest
statement is: the horizontal-bound analogue of the Crash 1 near-plane finding **does not exist in the
decompiled part**, and the undecompiled part cannot be ruled out without bytes.

**The near plane is a separate word and is not horizontal.** `vs_main_nearClip` is `0x8005E0C8`;
`vs_main_projectionDistance` is `0x8005E248`. Both are resident BSS, both in the resident module, so
both survive a BATTLE load. `vs_battle_setNearClip` (`0x8007CCCC`) stores the first and forwards it
to `func_80098160` (`0x80098160`), whose body is not vendored. Widening `H` does not touch the near
plane — which is the opposite of Crash 1's situation, where the horizontal bound *was* the near
plane.

**The real hazard here is different, and it is a gameplay one.** `vs_main_projectionDistance` is
branched on by two BATTLE functions against the value **272** (`146C.c:4209` `< 272`,
`146C.c:4266` `> 272`), and it scales the GTE fog (`SetFogNear(768, vs_main_projectionDistance)` at
`MENU5.PRG/4D8.c:511`). Retail's resting value is `0x100` = 256, which is **below** the threshold, so
`func_80074744`'s branch does not fire at rest. **A widening that raised the global past 272 would flip
a gameplay decision.** That is why this owner widens the *canvas* and never `H`, and why
`kProjectionDistanceBranchThreshold` is a shipped constant rather than a comment.

### 3. Why the owner sits on resident SDK leaves, not the overlay call site

BATTLE's field presenter `func_8007629C` re-states a **literal** `SetGeomOffset(160, 112)` on every
field. An owner on the overlay's viewport call would be overwritten 60 times a second. The four
resident leaves — `SetGeomOffset` `0x80041540`, `SetGeomScreen` `0x80041534`, `SetDefDrawEnv`
`0x8002B374`, `SetDefDispEnv` `0x8002B434` — are one address in one image, every caller's value
passes through them, and the argument is the title's own value at that instant, so a widening would
be idempotent by construction.

All four addresses were compared against the decompilation's module map and **all four agree**, as do
the four other resident addresses `docs/battle-rendering.md` already measured. Nine declarations are
gated in `game/render/battle_projection_facts.h`; the census currently answers 9 agree, 0
contradicted.

## What was built

`vagrant::BattleProjectionOwner` (`game/render/battle_projection.{h,cpp}`), registered through the
per-Core `psx::cpu::NativeDispatcher` from `VagrantRuntime::loadResidentImage` — the only boundary at
which the resident image exists, since `registerOverrides` runs at boot before any image does.
`VagrantContext` holds the owner per Core, because the measurement is per Core: the title re-authors
its viewport every field, so nothing is remembered between calls.

**It refuses rather than guesses, in five places**, each with a positive test:

1. the GTE control register and the framework's record of what the leaf was handed must agree;
2. the leaf's recorded value must equal its own argument register, so an address that moved or a leaf
   that transforms its argument is a named failure;
3. the guest's own viewport rectangle must agree with the width the title is publishing — two
   independent statements of one horizontal extent;
4. registration resolves every leaf against the image catalog **before installing any of them**, so a
   run is never left half-registered, and refuses an identity this Core did not publish (BATTLE,
   TITLE and ENDING all reuse `0x80068800`);
5. `derive()` refuses an incomplete publication, a retail centre that is not the half of the width
   the publication itself states, a plan that widens the projection but not the clip, a clip right
   edge past the widened width, an off-centre widened frustum, and an unusable plan.

`derive()` is pure and its 4:3 arm is the identity **by construction** — the plan's margin is zero at
4:3, so the measured values pass through untouched. A wide plan that widens centre and clip together
derives 214 / 428 / 427 from a measured 160 / 320 / 319.

## The boundary that stops a widening, stated

A widening is the **pair** (centre, clip). Moving the centre alone slides the frustum right and crops
its left edge off the field, showing no new geometry — a translation published under a wide claim.
The centre is derivable at a resident leaf. **The clip is not**, and the reason is concrete rather
than procedural: the guest publishes its display areas from the overlay call with a side-by-side VRAM
layout, and the reconstruction reports the screen rectangle as **256** against a **320**-wide display
area — identically in BATTLE.PRG and, independently, in ENDING.PRG. Widening the display area means
moving the second framebuffer in VRAM, and the consequence of that 256 cannot be re-derived without
the bytes.

So `VagrantRuntime::guestWidescreenProjection()` is **deliberately not overridden**. The absence is
the enforcement: the framework resolves this title's guest projection at `Standard4x3`, so a cropped
frame cannot reach the screen under a wide claim. The test asserts that absence.

## What remains, stated as remaining

- **S010 is still `missing`.** This issue adds the owner, the derivation and the refusals. It does not
  widen a frame, and nothing here should be read as widescreen support.
- **Own the clip publication** and re-derive the VRAM layout and the screen rectangle from bytes.
  That is the last step, and it needs the image.
- **`func_800BB874`'s scanline effect** would still span 320 px on a 428 px frame. Owning it needs its
  body, which is in the undecompiled part of BATTLE.PRG.
- **The bodies are unverified.** The first run with an image will either corroborate the
  reconstruction or make one of the five refusals fire. That is the point of putting the read-back and
  the cross-checks in the owner rather than in a comment.
- **S015 is unchanged.** There is still no dynarec title adapter, so nothing runs. The owner is
  reachable without one, which is why it could be written at all.

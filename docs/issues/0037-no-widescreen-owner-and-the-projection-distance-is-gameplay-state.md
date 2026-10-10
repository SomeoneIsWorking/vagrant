---
id: 37
title: BATTLE widescreen draws on the record canvas; the projection distance is gameplay state
status: partial
symptom: S010 (true widescreen) needs the room geometry drawn into the canvas margins without moving the projection word
tags: S010,S015,widescreen,projection,decomp
created: 2026-09-27
updated: 2026-10-10
---

## What was built

`vagrant::BattleProjectionOwner` (`game/render/battle_projection.{h,cpp}`), registered through the
per-Core `psx::cpu::NativeDispatcher` from `VagrantRuntime::loadResidentImage` — the only boundary at
which the resident image exists. `VagrantContext` holds the owner per Core.

It owns the four **resident** SDK leaves, not the overlay call site: BATTLE's presenter
`0x8007629C` re-states a literal `SetGeomOffset(160, 112)` every field, so an owner on the overlay's
call would be overwritten 60 times a second. The leaves are `SetGeomOffset 0x80041540`,
`SetGeomScreen 0x80041534`, `SetDefDrawEnv 0x8002B374`, `SetDefDispEnv 0x8002B434`.

It refuses rather than guesses, in four places, each with a positive test:

1. the GTE control register and the framework's record of the leaf's argument must agree;
2. the leaf's recorded value must equal its own argument register;
3. the guest's own viewport rectangle must agree with the width being published;
4. registration resolves every leaf against the image catalog before installing any, and refuses an
   identity this Core did not publish (BATTLE, TITLE and ENDING all reuse `0x80068800`).

The earlier `derive()` arm (a pure wide-centre derivation) was removed: under the record canvas the guest keeps its
retail centre and draw width, so nothing derives a wide projection.

## How the widening works now

`VagrantRuntime` declares `RenderPath::Record` and a `GuestWidescreenProjection`; psxport's record canvas holds
`presentationHorizontalMargin` extra columns on each side of the displayed buffer and draws a primitive into them
when its draw area spans the buffer. The guest still projects with centre 160 and a 320 clip, so the only thing that
stops a margin quad is the guest's own screen reject. BATTLE's room draw is
`0x8008AC78` -> `0x8008B1FC` -> `0x8009723C` -> `0x80097388` (quad loop), and every screen test in it goes through
the register-convention routine `0x80098014`, which rejects a quad whose four projected vertices lie wholly outside
x [0,320) or y [0,224). `game/render/battle_cull.{h,cpp}` replaces that routine on the BATTLE generation with the same
test over a box grown by the canvas margin; rows stay retail. At 4:3 the margin is 0, so the box is the retail one.
The verdict only decides whether a packet is emitted; no actor, camera or projection word reads it.

Evidence (S013 route, field 5000): at 4:3 with the enhancement off recordcheck reports `mismatched=0` on all 4868
checked fields; at 16:9 both margins show the room (shots `m_wide/f05000`, `w6/f05000`); `0x8005E248` is `0xE0` in
both runs; over 98 aligned steps 66 are bit-identical in RAM outside the two packet buffers, timers and dead stack
slots, and the rest differ only in the 3-field phase blocks at `0x800F2458..0x800F2540` and `0x800F3DEC..0x800F3F8C`
because the two runs sample different fields of one game frame.

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

## What remains

- Not widened, so margins hold stale or black columns for them: the sky-dome inline reject (`0x8009820C` region),
  the literal-320 gradient in `0x8008EC48`, effect and UI culls (rain `0x8008F440`, particles, HUD) and the
  `func_800BB874` scanline effect, which spans 320 px.
- These culls are screen-space draw decisions; none was found to feed gameplay, but only the room quad reject is
  proven so here.

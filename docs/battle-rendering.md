# BATTLE rendering boundary

This document separates retail-byte facts, corroborating decomp leads, and unimplemented enhancement
design. The measured addresses come from the authenticated retail bytes; the CC0 `rood-reverse`
source is a Rosetta stone, not proof by itself.

## Retail-measured field and projection ownership

Against BATTLE.PRG SHA-1 `d53aaccc3b3a2fc057d05e0dcea92f7182bc72a9`:

- `0x8007629C` is the sole BATTLE presenter. It flips resident parity `0x8005E210`, restores GTE
  offset `(160,112)`, waits for the GPU, advances game time, installs the current display/draw
  environments, and calls `DrawOTag` on the caller's dynamic OT.
- `0x8008A3A0` selects one of the two heap-allocated OT blocks at resident pointer array
  `0x80055C80`, clears 0x800 entries, and passes the tail to the presenter. Packet pools are likewise
  heap results stored through `0x8005E0C0`; they are not fixed `GameConfig` regions.
- `0x800760CC` owns BATTLE viewport initialization. Its measured call sequence supplies 320x240;
  the function subtracts the 16-line convention and establishes a 320x224 area. It states OFX as
  `width/2` = 160 and OFY as `(height-16)/2 + 16` = **128**, calls `SetDefDrawEnv` twice and
  `SetDefDispEnv` twice, writes both DISPENV `screen` rects as the literals (0, 8, 256, 224), and
  writes the resident rect at `0x8005DFD4` as x=0, y=0, w=320, h=224. The two draw areas are
  the clip rectangles **(0, 0, 320, 224) and (320, 0, 320, 224)** at `0x8005E0D0` and
  `0x8005E12C`, so the drawing area is clipped to **640 x 224** — two 320-wide halves, the two
  frame buffers, not two halves of a picture. Every coordinate is a literal
  (`0x80076140`, `0x80076148`, `0x8007617C`, `0x80076184`, and the delay slots
  `0x80076150`/`0x8007618C` for the height), and the only RAM read on this path, `0x8008A27C`,
  is the projection distance. Its call site is `0x8008A288`, called as
  `(320, 240, vs_main_projectionDistance, 0, 0, 0)`; INITBTL.PRG calls it the same way at
  `0x800FA69C`.
- `0x8005E248` is the projection-distance word used by that call. Setter `0x8007CCF0` stores its
  argument there and calls `SetGeomScreen` — both confirmed from the words at `0x8007CCFC` and
  `0x8007CD00`. The word is **branched on at three thresholds** (272 twice, 768 in a zoom clamp) and
  no BATTLE.PRG instruction materialises 256 into it, so the resting value is not a byte-derived fact
  of these modules.

The retained `BattleFrameProducer` owns only the completed-field fence. Its historical native route
called the original `0x8007629C` presenter, then flushed the guest batch for
`VagrantFrameDriver`'s single commit. The current dynarec product adapter has not connected this
owner, and it does not recreate scene geometry semantically.

## Current adapter status

The framework has generic widescreen and `Fps60` machinery; Vagrant satisfies the widescreen inputs on the record
canvas and none of the `Fps60` ones:

- `VagrantRuntime` declares `RenderPath::Record` and a `GuestWidescreenProjection`, and widens the CANVAS: psxport's
  record canvas adds `presentationHorizontalMargin` columns on each side of the 320 x 224 buffer while the guest keeps
  its retail centre (160) and clip. `vagrant::BattleProjectionOwner` (`game/render/battle_projection.{h,cpp}`) only
  observes the four measured resident SDK leaves the viewport is stated through. The 256 in the display `screen`
  rect is NOT a horizontal clip: `+0x00..+0x06` of the DRAWENV is the clip, filled from the leaf's arguments, and
  the drawing area is two 320-wide halves (the two frame buffers) at `0x8005E0D0` and `0x8005E12C`. The display
  resolution `SetDefDispEnv` states is never moved.
- What stops a margin from drawing is the guest's screen-space reject. The room draw is `0x8008AC78` ->
  `0x8008B1FC` -> `0x8009723C` -> `0x80097388`, and its screen tests all go through `0x80098014`, a
  register-convention routine (projected vertices in `$t0-$t3`, answer in `$at`) that rejects a quad wholly outside
  x [0,320) or y [0,224). `game/render/battle_cull.{h,cpp}` replaces it with the same test over the box grown by
  the canvas margin. Actors have no screen cull. Still retail: the sky-dome inline reject near `0x8009820C`, the
  literal-320 gradient in `0x8008EC48`, rain (`0x8008F440`), particles, HUD and the `0x800BB874` scanline effect.
- The publication's own vertical centre is 128, not the presenter's 112, and both were read from
  BATTLE.PRG. The overlay computes `(height-16)/2 + 16`; the presenter re-states the literal (160,
  112) every field, so the presenter's is in force at the frame boundary. This is the concrete reason
  the owner sits on the resident leaf: an owner on the overlay's call site would be overwritten once
  per field by a value that is a literal in the instruction stream.
- The title adapter does not yet launch BATTLE, so the framework's aspect toggle has no verified
  Vagrant world pass to widen. BATTLE's presenter restores OFX=160 itself, every field — confirmed
  from the bytes at `0x800762E0`/`0x800762E4` — which is why the owner sits on the resident
  `SetGeomOffset` leaf rather than on the overlay's viewport call, and why generic 2D widening
  heuristics cannot stand in for a widened world projection.

Against BATTLE.PRG SHA-1 `d53aaccc3b3a2fc057d05e0dcea92f7182bc72a9`:
- `0x800760CC` is the viewport publication, and its call site inside BATTLE.PRG is `0x8008A288`
  (the previously recorded `0x8008B0A4` is a `and $t2,$t1,$t5` inside a CLUT loop). It is called as
  `(320, 240, vs_main_projectionDistance, 0, 0, 0)`, states OFX as `width/2` and OFY as
  `(height-16)/2 + 16`, and writes both `screen` rects as the literals (0, 8, 256, 224).
- The projection distance must NOT be raised. `vs_main_projectionDistance` (`0x8005E248`) is branched
  on by two BATTLE functions against 272 and scales the GTE fog. There are THREE thresholds and not
  two: `0x8007458C` `slti $v0,$v0,0x110` (`< 272`), `0x80074750` `slti $v0,$v0,0x111` (`> 272`,
  spelled `< 273`), and a zoom step at `0x80078578` that adds 64 and clamps at `0x300` = 768. A
  widening that "just nudged H" would have cleared 272 and hit 768. Widening the canvas instead
  leaves the word alone. Retail's resting value of 256 is not derivable from the provisioned modules
  and is not claimed here.
- `VagrantRuntime` currently declares direct rendering. Vagrant supplies no semantic BATTLE world
  producer or interpolation snapshots, so an `fps60=1` checkout preference is refused rather than
  evidence of interpolated fields. The frame rate behind that scope question is still unmeasured.
  The `VSync` argument census is complete for BATTLE.PRG and finds its two call sites are both
  `VSync(1)`, which wait for nothing — so this title's field pacing is NOT in BATTLE's `VSync`
  calls, and the search moves to the resident executable's five `a0 >= 2` sites and TITLE.PRG's five.
  That is a control-flow question and a call-site census cannot answer it.

Do not wire the existing decorator merely to make the toggle execute. With no Vagrant semantic world
pass, guest-produced world items would only replay as captured screen-space geometry. The proper
integration point is the same future world producer described below, exposed through a narrow direct
runtime-owned temporal product rather than new legacy callbacks.

## Widescreen boundary

Widescreen is the canvas margin plus the widened room reject above; no SDK projection leaf is overridden and the
projection word `0x8005E248` is never written, because BATTLE branches on it. TITLE, menus and HUD keep their
literal 4:3 layouts and draw into the same canvas without the room's reject.

A true semantic widening (camera, object and material state before the GTE) remains a future BATTLE world producer
and is the only route to correct culling of the unhandled effects listed above.

## Interpolation boundary

The current `RenderQueue` contains already-projected screen vertices. Interpolating those vertices
would mix camera motion, object motion, clipping, depth ordering, and UI into one approximation; it
is not faithful frame interpolation.

Vagrant's future interpolation peer should record previous and current semantic simulation
snapshots, then ask the native world producer to render a presentation-time state. The first
snapshot needs camera position/look-at/roll, near/far clip, and
projection distance; per-object transforms join only as their semantic producers are ported. HUD and
menus render from the latest simulation state without world interpolation. Teleports, room changes,
camera cuts, and presentation-sync frames reset history instead of lerping across discontinuities.

The measured BATTLE presenter is a valid completed-field fence and therefore the nearest place to
publish a finished snapshot, but it is not by itself sufficient for interpolation: semantic camera
and object values must be captured before the next simulation tick overwrites scratch state, and the
world must be regenerable from the interpolated snapshot. Until that producer exists, the direct
rendering capability refuses temporal interpolation and cannot claim world-motion lerp.

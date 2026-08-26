# BATTLE rendering boundary

This document separates retail-byte facts, corroborating decomp leads, and unimplemented enhancement
design. `tools/re_frame.py` is the authority for the measured addresses; the CC0 `rood-reverse` source
is a Rosetta stone, not proof by itself.

## Retail-measured field and projection ownership

Against BATTLE.PRG SHA-1 `d53aaccc3b3a2fc057d05e0dcea92f7182bc72a9`:

- `0x8007629C` is the sole BATTLE presenter. It flips resident parity `0x8005E210`, restores GTE
  offset `(160,112)`, waits for the GPU, advances game time, installs the current display/draw
  environments, and calls `DrawOTag` on the caller's dynamic OT.
- `0x8008A3A0` selects one of the two heap-allocated OT blocks at resident pointer array
  `0x80055C80`, clears 0x800 entries, and passes the tail to the presenter. Packet pools are likewise
  heap results stored through `0x8005E0C0`; they are not fixed `GameConfig` regions.
- `0x800760CC` owns BATTLE viewport initialization. Its measured call sequence supplies 320x240;
  the function subtracts the 16-line convention and establishes a 320x224 draw/display area.
- `0x8005E248` is the projection-distance word used by that call. Setter `0x8007CCF0` stores its
  argument there and calls `SetGeomScreen`.

The shipping `BattleFrameProducer` owns only the completed-field fence. It retained-super-calls
`0x8007629C`, then lets the VBlank owner flush and commit the already-translated guest batch. It does
not yet recreate scene geometry semantically.

## What the current framework paths do for Vagrant

The framework has generic widescreen and `Fps60` machinery, but Vagrant does not currently satisfy
their game-owned inputs:

- `VagrantRuntime` does not publish a `GuestWidescreenProjection`. The generic guest-projection plan
  therefore has no Vagrant aspect policy, and that plan is GTE-path-only in any case.
- Native `gpu_vk_wide_engine` can see the user's aspect toggle, but its durable per-frame OFX recenter
  lives in the framework's native frame loop. Vagrant does not run that loop; its guest VBlank is the
  field authority, and BATTLE's presenter restores OFX=160 itself. Generic 2D widening heuristics are
  not a substitute for a widened BATTLE world projection.
- `VagrantRuntime` explicitly declares the `interpolatedNative` target profile, so native,
  widescreen, and temporal controls remain part of this title's intended product. Every current
  Vagrant producer still calls the neutral `FramePresenter::commit` without passing the temporal
  decorator, however, and Vagrant supplies no
  `fps60ReadSceneCam` or `fps60WorldPass` callback. Consequently `fps60=1` in the checkout-local
  settings file is not evidence that Vagrant fields are interpolated; the present path bypasses the
  temporal object.

Do not wire the existing decorator merely to make the toggle execute. With no Vagrant semantic world
pass, guest-produced world items would only replay as captured screen-space geometry. The proper
integration point is the same future world producer described below, exposed through a narrow direct
runtime-owned temporal product rather than new legacy callbacks.

## Widescreen boundary

Widescreen belongs to a future BATTLE world producer, at the camera/projection stage before vertices
become screen coordinates. It must not be a global `SetGeomOffset` or `SetGeomScreen` override:
TITLE, menus, loading layers, and HUD use those SDK calls for fixed 2D layouts, while the BATTLE
presenter deliberately restores `(160,112)` every field.

The world producer should therefore:

1. preserve BATTLE's vertical center and clipping convention;
2. compute a wide horizontal projection and center for world geometry only;
3. retain original 4:3 coordinates for HUD/menu/loading layers;
4. treat projection-distance changes as camera state, including transitions, rather than replacing
   `0x8005E248` with a constant.

The matching decomp corroborates the state that will need a binary-backed extractor: camera
position/look-at/angles/far clip live in the scratchpad camera structure, near clip is resident, and
camera transitions update projection distance through `vs_battle_setProjectionDistance`. Exact
camera snapshot addresses and a reached world draw owner remain unmeasured.

## Interpolation boundary

The current `RenderQueue` contains already-projected screen vertices. Interpolating those vertices
would mix camera motion, object motion, clipping, depth ordering, and UI into one approximation; it
is not faithful frame interpolation.

Following Dusklight's ownership pattern, Vagrant's future interpolation peer should record previous
and current semantic simulation snapshots, then ask the native world producer to render a
presentation-time state. The first snapshot needs camera position/look-at/roll, near/far clip, and
projection distance; per-object transforms join only as their semantic producers are ported. HUD and
menus render from the latest simulation state without world interpolation. Teleports, room changes,
camera cuts, and presentation-sync frames reset history instead of lerping across discontinuities.

The measured BATTLE presenter is a valid completed-field fence and therefore the nearest place to
publish a finished snapshot, but it is not by itself sufficient for interpolation: semantic camera
and object values must be captured before the next simulation tick overwrites scratch state, and the
world must be regenerable from the interpolated snapshot. Until that producer exists, the checkout's
`fps60` preference is inert for Vagrant's neutral commits and cannot honestly claim world-motion lerp.

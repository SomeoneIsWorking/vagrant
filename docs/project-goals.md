# Vagrant Story project goals

## G001 — Faithful, playable PC port

Deliver Vagrant Story from the USA `SLUS_010.40` executable and user-supplied disc content as a
portable PC application. The authenticated retail bytes, independent emulator, and retail-backed
instruments remain the falsifiers for native replacements; isolated compilation or reaching a menu
does not satisfy this goal.

Success requires the shipping product to boot, render, accept input, play audio, save, and progress
through the game without relying on copyrighted assets in the repository or maintainer-only RE tools.

## G002 — Readable game-owned native graphics

Move scene production from opaque guest graphics output into cohesive Vagrant-owned producers that
read named game camera, object, material, and animation state. The native picture must be traceable to
the game's pre-GTE inputs and must preserve the faithful 4:3 result before adding enhancements.

Post-projection OT/GP0 replay, GTE-output reconstruction, duplicate guest/native world rendering, and
a title-wide magic projection override are explicit non-goals.

## G003 — True widescreen

Render BATTLE world geometry at wider aspect ratios through the game-owned camera and projection
stage, showing additional correctly projected horizontal content while preserving vertical framing.
Fixed-layout TITLE, loading, menu, and HUD layers retain their intended coordinates unless each layer
gains an independently measured layout policy.

Stretching, cropping, or widening already-projected screen vertices does not satisfy this goal.

## G004 — Interpolated presentation

Present smooth in-between frames from previous/current semantic camera and object state while leaving
the retail simulation cadence and guest RAM untouched. Real and interpolated frames use one native
world builder; the only 60fps difference is insertion of the additional lerped presentation.

Camera cuts, room changes, teleports, and synchronization frames reset history. Interpolating the
post-projection render queue or exposing a 60fps switch before this semantic path exists is out of
scope.

## G005 — Loading removal

Remove storage latency and loading-only waits from every load the game performs, without changing
unrelated scripted timing or faking completion. Loading runs asynchronously and the product goes
straight to the next real presentation.

Success requires each measured load operation to deliver the same payload and terminal state as
retail while omitting its loading-only presentation. Logo screens accept Start/Cross through the
title's recovered cancellation route (or a purpose-built skip establishing the same lifecycle,
resource, and state invariants). Authored transition cutscenes are presentation, not loading, and
remain.

Faster simulation, bypassed lifecycle callbacks, written phase/timer/scene words, and presentation
tricks that hide a wait are not implementations of this goal. Loading removal is suppressed under
oracle comparison.

Contributing state: S017.

## Constraints

- The gameplay product executes guest instructions only through psxport's dynarec and contains no
  offline-generated guest code or interpreter fallback.
- Retail-derived addresses and behavior ship only with executable-backed measurements and gates.
- The matching CC0 rood-reverse decomp is a readable source supply, not independent proof.
- The zero-argument launcher must provision from user-owned assets and run the current product without
  Ghidra or other maintainer-only tooling.
- Goals record durable product intent only. Current capability coverage is in
  `docs/project-state.md`; atomic work is in `docs/issues/`.

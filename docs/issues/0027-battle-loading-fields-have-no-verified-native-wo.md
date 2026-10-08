---
id: 27
title: BATTLE/loading fields have no verified native world producer or picture
status: investigating
symptom: After TITLE transitions to BATTLE, stored 320x224 captures show loading or black fields while only small BATTLE primitive batches are present
tags: battle,render,native-renderer,widescreen,interpolation,next-boundary
state_items: S008, S009, S010, S011
created: 2026-08-26
updated: 2026-08-27
---

## Established boundary

Measured from BATTLE.PRG's own bytes: the sole presenter `0x8007629C`, the dynamic OT submit owner
`0x8008A3A0`, the viewport initializer `0x800760CC`, the 320x240 input / 320x224 draw area, the
per-field `SetGeomOffset(160,112)`, the projection-distance word `0x8005E248` and its setter
`0x8007CCF0`.

`game/render/battle_frame.{h,cpp}` installs a retained-super completion fence on the measured
presenter; the per-Core `BattleFrameProducer` flushes only after that presenter has translated its
dynamic OT, and `VagrantFrameDriver` owns the one field commit.

This is a render-ownership prerequisite, not a native world renderer and not a visual fix. A 240-second
product run reached the completion override 9,073 times, so the fence is live. The guest captures at
fields 6100, 6600, 7000 and 7500 are byte-identical all-black 320x224 images (SHA-256
`15428e41dc15a5f0c2adbd364f3fd7d1c2f4e602dbde9afd9b956be22aa556d8`), while a separate composition at
6600 still shows the readable title menu. **That falsifies any claim that fence reach or the current
neutral commits already produce a BATTLE world picture.**

## Next proof

1. one commit corresponds to one completed BATTLE presenter call;
2. the first intended room/world field contains the expected scene rather than only transition or
   loading primitives;
3. a producer-disabled control removes that same-index field or changes it detectably.

If the retained guest batch still renders black, compare the captured OT/primitive stream and guest VRAM
against the reference before implementing a semantic world producer. Do not infer that the field fence
itself fixes pixels.

## Running it

The recipe is a paced product run with the pad replay that reaches BATTLE around frame 6000, with
`PSXPORT_PAD_SHOT_AT=6100,6600,7000,7500`, a watchdog, and a **fresh log filename every attempt**
because `PSXPORT_LOG_FILE` appends. Exit 124 from the external time bound is expected, not a success
code: the title stays inside guest `main`, so a native-frames bound cannot end this path.

The checkout-local `fps60=1` preference is **not** interpolation evidence: the producers use neutral
commits and expose no semantic camera/world pass.
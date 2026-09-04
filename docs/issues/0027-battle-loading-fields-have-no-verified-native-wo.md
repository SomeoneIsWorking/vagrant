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

`tools/re_frame.py` now SHA-measures BATTLE's sole presenter `0x8007629C`, dynamic OT submit owner
`0x8008A3A0`, viewport initializer `0x800760CC`, 320x240 input/320x224 draw area, per-field
`SetGeomOffset(160,112)`, projection-distance word `0x8005E248`, and setter `0x8007CCF0`.

`game/render/battle_frame.{h,cpp}` installs a retained-super completion fence on the measured
presenter. The per-Core `BattleFrameProducer` flushes only after that guest presenter has translated
its dynamic OT; `VagrantFrameDriver` owns the one field commit. Clang builds the seam and full generated product; the runtime/context test,
clang-format/clang-tidy gate, and `re_frame.py` 6/6 controlled-mutation self-test pass.

This is a render-ownership prerequisite, not a native world renderer and not a visual fix. A serialized
240-second product run against pinned psxport `99a42aa3` reached the completion override 9,073 times,
so the measured fence is live. The four exact-index guest captures at fields 6100, 6600, 7000, and
7500 are byte-identical all-black 320x224 images (SHA-256
`15428e41dc15a5f0c2adbd364f3fd7d1c2f4e602dbde9afd9b956be22aa556d8`), while a separate diagnostic
composition at 6600 still shows the readable title menu. This falsifies any claim that fence reach or
the current neutral commits already produce a BATTLE world picture.
The checkout-local settings currently request `fps60=1`, but Vagrant's producers use neutral commits
and expose no semantic camera/world pass, so that preference is not interpolation evidence.

## Next proof

The 2026-08-27 serialized run proves override reach and falsifies the visible-world condition. The
remaining controlled comparison must require all of the following:

1. one commit corresponds to one completed BATTLE presenter call;
2. the first intended room/world field contains the expected scene rather than only transition/loading
   primitives;
3. a producer-disabled control removes that same-index field or changes it detectably.

If the retained guest batch still renders black, compare the captured OT/primitive stream and guest
VRAM against the reference before implementing a semantic world producer. Do not infer that the new
field fence itself fixes pixels.

## Serialized product gate

The historical operator-owned recipe used the former guest-loop product, at paced guest speed, against
the recording that reaches BATTLE around pad frame 6000:

```sh
timeout --signal=TERM --kill-after=5s 240s env \
  PSXPORT_PAD_REPLAY=scratch/vs-newgame.pad \
  PSXPORT_PAD_SHOT_AT=6100,6600,7000,7500 \
  PSXPORT_DEBUG=vagrant-battle \
  PSXPORT_LOG_FILE=scratch/logs/re17-battle-frame-live-99a42aa3.log \
  PSXPORT_WATCHDOG=15 \
  ./scratch/bin/vagrant_port
```

Use a fresh log filename for every attempt because `PSXPORT_LOG_FILE` appends. Exit 124 is the
expected external time bound, not a product success code: Vagrant remains inside guest `main`, so
`PSXPORT_NATIVE_FRAMES` cannot end this path and `atexit` hit counts are unavailable. The completed
run's log SHA-256 is
`87fe8f94d54fd2b373e6e1ab6bc0a3e270ac19c150866e91283ff3403627ca62`. `timeout` sent TERM, the
watchdog emitted its scoped interrupt report, and no game process remained. The run cannot prove one
completion per commit or the producer-disabled same-index control; those require explicit count
evidence and a controlled disabled-producer run before this issue can close.

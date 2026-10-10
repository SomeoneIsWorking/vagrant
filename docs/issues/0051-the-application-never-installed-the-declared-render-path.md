---
id: 0051
title: The product never installed its declared render path, so the PC rasterizer drew the speech bubbles with stray triangles
status: resolved
symptom: stray black triangle edges across the dialogue speech bubble (S013); no margin could ever draw at 16:9 (S010)
tags: S010,S013,render,record
created: 2026-10-10
updated: 2026-10-10
---

Observed: at field 6000 of the S013 route the "Have you found Sydney?" bubble showed black diagonal edges
across its fill (4:3, `PSXPORT_DEBUG` off). Expected: the guest's own quads, drawn flat as on hardware.

Cause: `game/boot/application.cpp:Application::run` never called `psx::Machine::installRenderPath`, so the Core kept
the framework default `RenderPath::Native` instead of `VagrantRuntime::renderCapabilities()`'s `Record`, and the PC
rasterizer drew the guest's packets (a probe in `present_record` read path 0 on every field).

Fix: `Application::run` installs the render path before `bootInit`, the order psxport's own boot spine uses. The run
now logs `render path = record`; the same scene at the same field draws the bubble clean (shots under
`scratch/vs-widescreen/`: `s3/f06000` before, `b1/f06100` after).

Test: no unit seam reaches `Application::run` without the disc; the evidence is the live run's `render path` line and
the recordcheck pass in `docs/issues/0037-no-widescreen-owner-and-the-projection-distance-is-gameplay-state.md`.

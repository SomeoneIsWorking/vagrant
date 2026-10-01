---
id: 16
title: Resident bootstrap reached a direct TITLE overlay call with no emitted overlay
status: resolved
symptom: after four WAVE reads and the TITLE image read completed, the runtime failed fast at 0x80071334 from resident jal at 0x80042BD8
tags: boot,overlay,re-03,re-04,routing
created: 2026-08-21
updated: 2026-08-22
---

Resident `0x80042BAC` has a direct `jal 0x80071334` at `0x80042BD8`; the target is inside the verified
TITLE overlay slot based at `0x80068800` (offset `0x8B34`), not inside the resident PS-EXE. The
emitter consumed only the resident image, so the target was a recomp-MISS.

**Dead end:** adding `0x80071334` as a resident seed decodes unrelated PS-EXE bytes at an overlay
address. The correct owner is the independently extracted TITLE image at its measured base — which is
what `game/core/overlay_images.cpp` and `game/core/title_entry.cpp` now do.

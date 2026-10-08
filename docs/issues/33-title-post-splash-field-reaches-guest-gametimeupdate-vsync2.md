---
id: 33
title: TITLE post-splash field reached guest gametimeUpdate VSync(2)
status: resolved
symptom: after 728 native TITLE sprite fields and seven captures, the run hit the mandatory guest-VSync fatal at TITLE 0x8006E988 -> gametimeUpdate 0x8004261C -> VSync(2) 0x8001F6C4
tags: title,vsync,frame-loop
created: 2026-08-24
updated: 2026-08-24
---

The publisher/developer splash ownership was complete; the next TITLE continuation calls the resident
`gametimeUpdate` owner, whose retail body waits two display fields through guest VSync. An unowned
top-down field boundary, not an ABI crash.

**Dead end:** no-op or widening the primitive binding to get past it. Keep VSync fatal; measure the
exact TITLE caller continuation and let `VagrantFrameDriver` service those two fields.

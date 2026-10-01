---
id: 24
title: BATTLE init reads a corrupted pointer
status: resolved
symptom: read32 at 0x2414003B with v0=0x2413FFFF immediately before the wild read, ra=0x8008A058
tags: battle,pointer,re-15
created: 2026-08-26
updated: 2026-08-26
---

A truly unattended headless run reaches this boundary by itself: movie sectors end, CdlPause, Setmode
`0xA0`, file loads around LBA 7254, BATTLE dispatch, abort. Whether that automatic transition is the
attract demo or another title transition was not determined.

**Dead end worth remembering:** do not cite windowed smoke runs for the unattended path — one of them
had the operator playing, and input-driven reachability proves nothing about the unattended route.

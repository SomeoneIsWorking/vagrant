---
id: 29
title: Finite TITLE reinitialisation stops inside menu-sound CD loads
status: resolved
symptom: Native frame path reaches the loading screen but cannot enter TITLE because _loadMenuSound blocks in diskLoadFile -> gametimeUpdate -> guest VSync.
tags: S003,frame-loop,vsync,title,cd,menu-sound,native-ownership,re-19
created: 2026-08-27
updated: 2026-08-27
---

## Root cause

Retail `_loadMenuSound 0x800468FC` performs four synchronous `vs_main_diskLoadFile 0x8004493C` calls. Each blocking poll calls `vs_main_gametimeUpdate 0x8004261C`, whose first operation is Sony VSync `0x8001F6C4`. Dispatching either outer routine whole violates the mandatory native-frame contract.

## Resolution

`ResidentPhase` reproduces `_diskReset 0x80044A60` and its three fields, then uses the real-disc
`NativeFile` owner for the four measured extents. A serialized CHD run copied all four into guest RAM,
applied their exact sound consumers, and reached TITLE reinitialisation completion without guest
VSync. It then copied TITLE.PRG and entered its generated overlay at `0x80071334`. The next fatal was
the distinct publisher splash VSync, now owned by `TitleSplashPhase`.

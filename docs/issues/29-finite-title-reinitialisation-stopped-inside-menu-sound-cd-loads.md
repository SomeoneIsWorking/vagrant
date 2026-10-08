---
id: 29
title: Finite TITLE reinitialisation stopped inside the menu-sound CD loads
status: resolved
symptom: after the four menu-sound loads, TITLE reinitialisation stopped
tags: resident,title,cd,re-19
created: 2026-08-24
updated: 2026-08-24
---

Retail `_loadMenuSound 0x800468FC` makes four synchronous `vs_main_diskLoadFile 0x8004493C` calls, and
each blocking poll calls `vs_main_gametimeUpdate 0x8004261C`, whose first operation is guest VSync
`0x8001F6C4`.

**Dead end:** dispatching either outer routine whole. It violates the mandatory native-frame contract;
the owner reproduces `_diskReset` and its three fields and then uses the real-disc `NativeFile` owner
for the four measured extents.

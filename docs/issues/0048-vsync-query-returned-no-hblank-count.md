---
id: 0048
title: VSync(1) returned a stale V0 so the guest spun at `while (VSync(1) < 0xF8)`
status: resolved
symptom: guest hung at 0x8006FE88
tags: S004,S006,S013,title,cd
created: 2026-10-09
updated: 2026-10-09
---

`psxport/runtime/psx/hle/platform_hle.cpp:PlatformHle::vsync`: the frame-boundary exit left V0 unset.

## Fix

V0 is a full field's HBlank count (`displayLinesPerField`) before the exit.

## Test

`tests/test_vsync_ownership.cpp` (`r[2] == 263`).

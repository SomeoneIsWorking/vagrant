---
id: 12
title: Frameless bootstrap launcher left renderer mode implicit
status: resolved
symptom: plain run.sh could watchdog in host Wayland/Vulkan presentation before entering Vagrant guest crt0
tags: launcher,watchdog,renderer,headless
created: 2026-08-21
updated: 2026-08-21
---

## Root cause

Vagrant currently has a verified resident bootstrap but no game-owned frame loop. The launcher inherited psxport renderer-mode defaults instead of declaring this target invariant. After the framework update, plain launch could enter host window/presentation setup; the no-frame watchdog then diagnosed that host path rather than the measured guest stall. Heavy concurrent GPU work amplified the host allocation delay but was not the tracked cause.

## Resolution

`tools/run.py::launch` explicitly sets `PSXPORT_VK_HEADLESS=1` for the current frameless bootstrap, and `tests/test_launcher.py` checks that environment immediately before the real port exec. After the competing GPU run ended, plain `./run.sh` against pinned psxport `eb2465b2` initialized the headless renderer, entered guest crt0/main, and sampled generated `0x8001355C` as documented.

## Falsifier

Run plain `./run.sh`; a watchdog stack in host surface/device setup before `[native_boot] entering native crt0`, or selection of a gameplay/window target without a measured frame loop, falsifies the resolution.

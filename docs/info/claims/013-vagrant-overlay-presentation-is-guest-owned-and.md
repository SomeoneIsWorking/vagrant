---
id: C013
kind: claim
status: holds
created: 2026-08-21
tags: frame,re-05
depends: tools/re_frame.py#measure, game/core/game_config.cpp#vagrant_game_config
---

## Claim

Vagrant overlay presentation is guest-owned, and BATTLE frame buffers are dynamic guest-heap allocations rather than fixed GameConfig regions.

## Evidence

2026-08-21: tools/re_frame.py measured the SHA-bound TITLE/BATTLE/INITBTL retail bytes. Unique presenters 0x80071A68 and 0x8007629C share parity 0x8005E210 and resident envs, then call DrawOTag. BATTLE submit owner 0x8008A3A0 uses pointer arrays 0x80055C80/0x8005E0C0 populated by two 0x2088 and two 0x20000 guest-heap allocations. --check-config --selftest passed 4/4 and rejects fixed bases.

## What would falsify it

if any owned overlay no longer matches its SHA, a live reached trace shows a different submit owner/layout, or a fixed region is proven to represent all guest allocations

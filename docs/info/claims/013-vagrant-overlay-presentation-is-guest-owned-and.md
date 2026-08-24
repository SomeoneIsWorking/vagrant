---
id: C013
kind: claim
status: holds
created: 2026-08-21
tags: frame,re-05
depends: tools/re_frame.py#measure, game/core/game_config.cpp
reconfirmed: 2026-08-24
verified_at: 2026-08-24 20:08:15
---

## Claim

Vagrant overlay presentation is guest-owned, and BATTLE frame buffers are dynamic guest-heap allocations rather than fixed GameConfig regions.

## Evidence

2026-08-21: tools/re_frame.py measured the SHA-bound TITLE/BATTLE/INITBTL retail bytes. Unique presenters 0x80071A68 and 0x8007629C share parity 0x8005E210 and resident envs, then call DrawOTag. BATTLE submit owner 0x8008A3A0 uses pointer arrays 0x80055C80/0x8005E0C0 populated by two 0x2088 and two 0x20000 guest-heap allocations. --check-config --selftest passed 4/4 and rejects fixed bases.

## What would falsify it

if any owned overlay no longer matches its SHA, a live reached trace shows a different submit owner/layout, or a fixed region is proven to represent all guest allocations

## Re-confirmed 2026-08-22 14:13:26

2026-08-22: tools/re_frame.py --check-config matched all 12 frame-policy facts and --selftest passed 4/4 after the measured table became private compatibility debt.

## Re-confirmed 2026-08-22 17:51:59

2026-08-22 re_frame.py --check-config --selftest passed 4/4 against SHA-bound overlays after the separate immediate-sprite producer landed

## Re-confirmed 2026-08-22 18:14:39

2026-08-22 against psxport ad5cf802: re_frame.py --check-config --selftest passes 4/4; dynamic frame facts and zero fixed regions remain gated

## Re-confirmed 2026-08-24

Post-landing re_crt0 and 7/7 CTest retain dynamic guest heap/frame ownership facts; legacy adapter continues the measured guest-VRAM picture policy on bc8c8897

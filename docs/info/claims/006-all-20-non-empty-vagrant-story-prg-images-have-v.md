---
id: C006
kind: claim
status: holds
created: 2026-08-14
tags: overlays,re-03
depends: tools/re_overlay.py#measure, game/core/game_config.cpp, game/recomp_seeds.json
reconfirmed: 2026-08-21 02:47:31
verified_at: 2026-08-21 02:47:31
---

## Claim

All 20 non-empty Vagrant Story .PRG images have verified load-base mappings into exactly three slots: BATTLE/TITLE/ENDING at 0x80068800; INITBTL/SCREFF2/MAINMENU at 0x800F9800; MENU0-5,7-9,B-F at 0x80102800. The twenty-first PRG, MENUA, is 0 bytes and has no base.

## Evidence

2026-08-14 tools/re_overlay.py on the owned disc: M2 derived all 20 bases from each image's own `jal` targets and entry offsets, zero undecided; M3 SHA-bound each owned image to its rood-reverse config and then found 20/20 `vram` agreements, zero missing/mismatch/extra; resident M1 saw all three values in four contiguous words at 0x80010000..0x8001000C; `--selftest` 7/7 PASS, 0 SKIP; `--check-config` 24/24.

## What would falsify it

Falsified if any owned non-empty PRG no longer matches its recorded SHA, M2 becomes undecided or yields a different base, the SHA-bound rood vram disagrees, a running loader writes one of these modules to another base, or the shipping gate fails.

## Re-confirmed 2026-08-14 12:36:37

Reverified after RE-02: overlay shipping check 24/24 and selftest 7/7 remain green; loader reachability remains explicitly unobserved.

## Re-confirmed 2026-08-21 01:04:32

2026-08-21: re_overlay --selftest --check-config passed 7/7 with 20 measured non-empty modules, zero skips, and both shipping slot/seed negative mutations detected.

## Re-confirmed 2026-08-21 02:47:31

2026-08-21: re_overlay check-config/selftest remains 7/7 over all non-empty PRGs after RE-09 GameConfig extension.

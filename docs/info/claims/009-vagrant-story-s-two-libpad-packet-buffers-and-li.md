---
id: C009
kind: claim
status: holds
created: 2026-08-20
tags: [input, re]
depends: tools/re_pad.py#measure, game/core/game_config.cpp
reconfirmed: 2026-08-22 18:14:39
verified_at: 2026-08-22 18:14:39
---

## Claim

Vagrant Story's two libpad packet buffers and live driver pointer table are byte-derived: slot0 0x8005DFF0, slot1 0x8005E012, table 0x8003FCF0, stride 240

## Evidence

tools/re_pad.py over the SHA-bound SLUS_010.40 found one _sysInit two-slot call in 83,948 candidates, decoded PadInitDirect's a0/a1 stores, passed --check-config, and passed 3/3 negatives

## What would falsify it

if the owned executable identity changes, the setup shape stops being unique, PadInitDirect no longer stores the two pointers at +0x30/+0x120, or a live trace shows the game reads pad packets elsewhere

## Re-confirmed 2026-08-21 01:04:32

2026-08-21: re_pad --check-config --selftest re-derived slot buffers 0x8005DFF0/0x8005E012 and pointer table 0x8003FCF0 stride 240 from the SHA-bound executable; the unique-shape and +4 shipping mutations both refused, 3/3.

## Re-confirmed 2026-08-21 02:47:31

2026-08-21: re_pad check-config/selftest 3/3 passed after RE-09 GameConfig extension.

## Re-confirmed 2026-08-21 03:31:41

RE-10 final tools/re_pad.py --check-config --selftest passed 3/3 including destroyed-call and shifted-shipping negatives

## Re-confirmed 2026-08-21

Post-landing re_pad passed 3/3 for both fixed buffers and the live driver pointer table.

## Re-confirmed 2026-08-22 14:13:26

2026-08-22: tools/re_pad.py --check-config matched all four shipped values and --selftest passed 3/3 after the compatibility-table refactor.

## Re-confirmed 2026-08-22 17:51:58

2026-08-22 re_pad.py --check-config --selftest passed 3/3 against owned executable

## Re-confirmed 2026-08-22 18:14:39

2026-08-22 against psxport ad5cf802: re_pad.py --check-config --selftest passes 3/3

---
id: C011
kind: claim
status: holds
created: 2026-08-21
tags: re-09,spu,dma,boot
depends: tools/re_spu_transfer.py#measure, game/core/game_config.cpp#kDmaCallbackTable
reconfirmed: 2026-08-22 18:14:39
verified_at: 2026-08-22 18:14:39
---

## Claim

Vagrant StartSound's DMA4 completion route uses libapi table 0x80032128; configuring that table dispatches guest callback 0x8001DE94 and advances beyond _waitTransferAvailable 0x8001355C

## Evidence

tools/re_spu_transfer.py derives the route from SHA-verified SLUS_010.40 and passes 3/3 both-answer selftest; scratch/logs/re09-spu-bounded-final.log records repeated owed DMA4 dispatches from slot 0x80032138 and the next watchdog under VSync 0x8001F6C4/0x8001F83C

## What would falsify it

if the same SHA-bound executable reaches 0x8001355C with slot 0x80032138 populated but callback 0x8001DE94 not dispatched, or if a run advances without the measured table

## Re-confirmed 2026-08-21 02:44:52

Reconfirmed after final instrument cleanup: 3/3 executable-backed selftest passed; Clang build and all 3 CTests passed; bounded default launcher dispatched DMA4 callback 0x8001DE94 from measured slot 0x80032138 and moved the watchdog to VSync 0x8001F6C4/0x8001F83C.

## Re-confirmed 2026-08-21 02:59:16

2026-08-21: against landed psxport 2b5ef7b5, RE-09 selftest passed 3/3 and real no-argument launcher dispatched callback 0x8001DE94 from slot 0x80032138 before the VSync watchdog.

## Re-confirmed 2026-08-21 03:31:41

RE-10 final tools/re_spu_transfer.py --check-config --selftest passed 3/3; real default launcher again dispatched measured DMA4 callbacks before GPU setup

## Re-confirmed 2026-08-22 18:14:39

2026-08-22 against psxport ad5cf802: re_spu_transfer.py --check-config --selftest passes 3/3 and real default boot advances through DMA/VBlank into TITLE

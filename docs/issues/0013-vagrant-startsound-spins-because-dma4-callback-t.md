---
id: 13
title: Vagrant StartSound spins because DMA4 callback table is unconfigured
status: resolved
symptom: watchdog stack ends in generated _waitTransferAvailable 0x8001355C while _isSpuTransfer remains one
tags: boot,spu,dma,callback,re-09
created: 2026-08-21
updated: 2026-08-21
---

## Root cause

Sony libspu registers its completion callback on DMA channel 4 through the active libapi table at `0x80032128`. Vagrant left `GameConfig::dmaCallbackTable` zero, so psxport completed the real DMA4 transfer but consumed it without dispatching the guest callback; `_spuWriteComplete` never cleared `_isSpuTransfer` at `0x800377F0`. An initial static pass selected `0x80031050`, a different indexed callback table. A live table watch falsified it: DMA4 was owed but slot `0x80031060` remained zero. Following the startup vector to its actual target `0x80020280` corrected the measurement.

## Resolution

`tools/re_spu_transfer.py` derives the complete StartSound/writer/waiter/completion chain, the SPU channel-4 adapter, and the callback-system startup vector from the SHA-verified executable. It gates `GameConfig::dmaCallbackTable = 0x80032128` and proves both refusal classes. The real default launcher then logs `owed ch4 -> callback 8001DE94 (slot 80032138)` and advances to a later watchdog in `VSync` (`0x8001F6C4` -> `0x8001F83C`) with no recompilation miss or BIOS fatal.

The new VSync boundary remains open; this resolution claims SPU transfer completion only.

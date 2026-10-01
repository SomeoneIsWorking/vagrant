---
id: 13
title: Vagrant StartSound spins because the DMA4 callback table is unconfigured
status: resolved
symptom: the watchdog stack ended in generated _waitTransferAvailable 0x8001355C while _isSpuTransfer stayed one
tags: boot,spu,dma,callback,re-09
created: 2026-08-21
updated: 2026-08-21
---

Sony libspu registers its completion callback on DMA channel 4 through the active libapi table at
`0x80032128`. Vagrant left `dmaCallbackTable` zero, so psxport completed the real DMA4 transfer and
consumed it without dispatching the guest callback, and `_spuWriteComplete` never cleared
`_isSpuTransfer` at `0x800377F0`.

**Dead end worth remembering:** a static pass selected `0x80031050`, a different indexed callback table.
A live table watch falsified it — DMA4 was owed while slot `0x80031060` stayed zero. Following the
startup vector to its real target `0x80020280` corrected the measurement. Fixing the table logged
`owed ch4 -> callback 8001DE94 (slot 80032138)`.

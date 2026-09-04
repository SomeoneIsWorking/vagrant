---
id: 25
title: Intro movie freezes: continuous XA/STR read delivers sectors but libcd completion never signals
status: resolved
symptom: Windowed play: splash plays, intro movie plays briefly then the picture FREEZES permanently; headless shows the guest spinning in resident 0x80022484 (libcd result-table poll, halfword==1) called from TITLE 0x8006F328 while [cdc] logs show LBA 263000+ sectors and DMA3 delivering continuously
tags: cd,xa,str,movie,re-04,user-facing,next-boundary
created: 2026-08-25
updated: 2026-08-26
---

## Symptom

Player-facing: ./run.sh opens the window, publisher splash presents, intro movie starts, then freezes mid-playback. Guest state: spin in resident 0x80022484 polling a 32-byte-slot result table (base 0x80039C48, index 0x80039C34) that libcd marks complete on INT2 delivery.

## Measured

PSXPORT_DEBUG=cdc,cdcmd,cd capture (scratch/logs/stall-cd2.log): sectors LBA 263055+ file=1 flowing, chan=0/1 alternating, submode 0x64 audio markers every 8th sector, DMA3 -> 0x8010C590 continuously up to SIGTERM. DATA IS DELIVERED; the guest-visible completion (INT2 -> libcd queue entry) is not. Boot log separately showed "[irq] pending I_STAT&I_MASK=0x004; no SysEnq element claimed it" — INT2 claiming is the suspect area.

## Required resolution

Drive the guest libcd completion path for CONTINUOUS streaming reads the way RE-04 did for file reads: the native CDC must raise the CD interrupt so the guest s own libcd handler marks the result slot, letting 0x80022484 return. Falsifier: no-input windowed play plays the intro without freezing (or reaches its natural end / teardown); headless run leaves the 0x80022484 poll within watchdog windows.

## Resolution (2026-08-26, psxport f9b5db8f)

The INT2 hypothesis was WRONG: the capture showed IRQ2 raising, the title verifier seeing it,
and the custom exception exit acking — per sector, continuously. Three defects sat downstream:

1. Setmode STRSND ignored -> XA audio sectors polluted the data FIFO (hardware never shows them
   to the guest); the demuxer aborted each pass after ~420 sectors and seek-restarted forever.
2. No XA->SPU decode path existed at all, so no audio cursor existed to sync to.
3. The drive clock ran on instruction costs (host speed during busy-poll) vs the field-paced SPU
   pull -> up to ~6% A/V drift.

Fixed in framework commit f9b5db8f (routing + push-mode ring + backpressure + wall-locked drive
clock + backlog servo). The historical proof advanced SPU from the retired VBlank host turn;
`VagrantFrameDriver` now owns that same once-per-field audio service. The new finite phase route has
not yet reached the intro, so this issue's live falsifier remains historical evidence rather than a
current product-run claim.

Falsifier MET: unattended windowed play streams the intro past LBA 262930 with live audio and no
freeze; headless leaves the old 0x80022484 retry loop entirely and now runs on to issue #24.

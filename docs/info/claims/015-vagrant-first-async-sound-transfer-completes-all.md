---
id: C015
kind: claim
status: falsified
created: 2026-08-21
tags: cd,re-04
depends: tools/re_async_cd.py#measure, external/psxport
falsified_on: 2026-08-21
---

## Claim

Vagrant first async sound transfer completes all 17 sector callbacks, then stalls because INT1 status 0x02 omits the read-active bit that lets libds leave ReadN 0x11/Busy and dispatch the final callback's queued Pause.

## Evidence

2026-08-21: tools/re_async_cd.py derives the callback-to-DsEndReadySystem-to-DsCommand(Pause=9) contract, response-status decoder, and VBlank ReadN-active transition from SHA-verified SLUS_010.40; its selftest is 3/3. scratch/logs/re11-shared-cdc.log and re11-paced-fntrace.log show LBA 63000..63016 and 17 guest callbacks including the final Pause enqueue. re11-paced-libds-state-range.log shows command 0x11, system Busy, raw status 0x02, and queue length one persist; re11-paced-libds-trace.log never enters queue dispatcher 0x800235A4. Static executable evidence shows status decoder 0x80025630 maps bit 0x20 into read-active byte 0x800326B2, then VBlank callback 0x80024BDC requires that byte before setting libds idle. The isolated paced framework candidate delays the next INT1 but retains the same failure, falsifying drive pacing alone.

## What would falsify it

if a default run does not deliver exactly these 17 callbacks before the stall, dispatches the queued post-read Pause, or live libds state/status no longer has this relation

## FALSIFIED 2026-08-21

Pinned psxport ce2c83ad returns ReadN status 0x22, so guest VBlank leaves ReadN/Busy and dispatches every queued Pause; the default run no longer stalls in the first transfer.

> Anything that cited this claim as proof must be re-checked. Grep the repo for it.

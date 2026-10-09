---
id: 0047
title: libds CD command completion never delivered, Setloc retried forever
status: resolved
symptom: the stream or BATTLE read stalled with Setloc re-sent every 0.5 s
tags: S004,S006,S013,title,cd
created: 2026-10-09
updated: 2026-10-09
---

`game/cd/cd_command.cpp:handleCdCommand`: stock sync HLE never invokes the cbsync slot (0x800321FC), so libds' deadline (0x800326C0) expired and retried; `DsControl` (0x80025B7C) also blocked.

## Fix

`handleCdCommand` records the owed command, `LibDsField::completeOwedCommand` calls cbsync(2, 0x80039C50) on the next field before the tick; `DsControl`/`DsControlB` are native; `ds_cbready` (0x8002559C) is wrapped so the owed completion precedes INT1 (instant-CD ordering).

## Test

`tests/test_vagrant_runtime.cpp` CD_cw completion test; `tests/test_dynarec_dispatch.cpp` `everyClaimedResidentLeafIsBound`.

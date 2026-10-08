---
id: 0044
title: The TITLE save-file owner reached the guest _initMemcard that its own native owner replaced
status: resolved
symptom: the run presented both TITLE splash halves and then parked for 2000+ fields inside _saveFileExists
tags: save,memcard,cd,title,re-23
created: 2026-10-04
updated: 2026-10-04
---

Issue 34 recorded the right fix for TITLE's `_initMemcard` — native-own it as finite staged reads of
the exact extents — and `TitleMemcardInit` was written and unit-covered. It was never reached:
`TitleSaveCheck::begin`/`finishInitField` called the GUEST `_initMemcard` at `title_memcard::kOwner`
(`0x8006A49C`) through `ResidentCallServices::call1`, so every field re-entered a body that
re-enqueues SPMCIMG.BIN on the libds CD queue and returns 0 until the slot is `Loaded`.

Measured 2026-10-04 through the product's own control channel at the stall (frame 2341): the
overlay's `_initMemcardState` `0x800DC8C4` = 0 (`none`), its `cdQueueSlot` `0x800DC8C8` = `0x800501E0`
with `slot->state` = 2 (`Reading`), `cdFile.lba` = `0x00014C98`, `cdFile.size` = `0x0001C000`, and all
eight `_memcardEventDescriptors` at `0x800DEA98` zero. The slot was one `_processCdQueue` short of
`Loaded` (4) and needed `_diskGetState() == diskIdle`, which psxport's synchronous CD controller never
establishes.

Note the recorded focus described this as "a card-insertion event". It is not: the card-event half is
`_memcardEventHandler`, which is reached only AFTER `_initMemcard` returns 1, and it was never entered.

The fix is one line per call site: `TitleSaveCheck` now drives `contextOf(core).titleMemcardInit`,
keeping retail's order (`_initMemcard(1)`, then one `_initMemcard(0)` poll per host field, then the two
card ports). `tests/test_vagrant_runtime.cpp` asserts the guest `_initMemcard` and the three CD-queue
leaves it would have needed are never dispatched, and that both extents were read natively.

**Dead ends:** satisfying the poll by writing `4` into the guest's slot state word (that is writing the
wait's own postcondition into guest RAM, and the port then depends on a word nothing produced), and
teaching the CD owner to raise the libds completion (a much larger surface that this title's other
loads already do not use).
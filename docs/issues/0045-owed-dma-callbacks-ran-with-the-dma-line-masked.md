---
id: 0045
title: Owed DMA callbacks ran while the guest had the DMA line masked
status: resolved
symptom: a guest-owned DMA callback table was invoked before the guest unmasked I_MASK DMA
tags: S004,S006,S013,title,cd
created: 2026-10-09
updated: 2026-10-09
---

`psxport/runtime/psx/hle/hle_interrupt.cpp`: the owed-DMA loop delivered callbacks regardless of I_MASK.

## Fix

The loop skips when a guest-owned callback table exists and the DMA bit is clear.

## Test

`test_guest_table_callback_waits_for_the_dma_line_to_be_unmasked` in psxport `tests/test_direct_dma_callbacks.cpp`.

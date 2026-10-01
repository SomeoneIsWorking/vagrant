---
id: 23
title: Computed dispatch whose base register flows in from a preceding jr-ra fragment
status: resolved
symptom: [recomp-MISS] no entry for 0x800B182C from BATTLE, caller ra=0x800B2AE4
tags: battle,computed-dispatch,re-15
created: 2026-08-26
updated: 2026-08-26
---

The Sony hand-written GTE macro chain is runs of blocks separated by `jr ra` plus a delay slot; a
block's successor is dispatched through `t9` whose base was materialised in an EARLIER block
(`lui/addiu` at `0x800B1818`, `addiu t9,t9,32` at `0x800B16FC`, `jr t9` at `0x800B1704`).

**Dead ends:** per-function reaching-constant analysis cannot see across the `jr ra` boundaries, and
linear image-wide propagation does not help either — intervening DATA decodes as unknown instructions
and clears the map (`t9` is already unknown at `0x800B16FC`).

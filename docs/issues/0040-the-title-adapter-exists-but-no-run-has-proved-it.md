---
id: 40
title: The dynarec title adapter exists and is gate-covered, but the first run's evidence is bounded
status: open
symptom: S015 was `missing` with one named cause: there was no Vagrant Story adapter to psxport's dynarec-only executor, so `run.sh` refused at a boundary and nothing in the title ran. The adapter is now written, compiled into a shipping executable, and covered by negative cases. Everything that depends on a presented frame stays `missing`.
tags: s015,dynarec,adapter,launcher,telemetry,product-slot,run-evidence
created: 2026-09-28
updated: 2026-09-28
---

## What exists

`game/core/dynarec_dispatch.{h,cpp}` is the title's whole adapter surface over `psx::cpu`, in five
operations: image-scoped install, finite call, bounded turn, original call, and a named fatal on a
call that did not return. `vagrant::dynarec` is the only module here that spells a budget, resolves an
image identity, or chooses a dispatch form, so there is one answer to "how long may a turn run"
(`psx::cpu::ExecutionBudget::currentTurn`) rather than two.

`game/core/application.{h,cpp}` composes it and `game/main.cpp` is a one-call entry point.
`tools/launcher/runtime_boundary.py` no longer refuses a product: it provisions the measured inputs,
configures, builds `vagrant_port`, and launches it.

## What is established by the contracts, and what each one does NOT establish

| claim | evidence | what it does NOT establish |
|---|---|---|
| the adapter installs image-scoped overrides and refuses a wrong generation | `vagrant_dynarec_dispatch`: an unscoped install, a stale-generation install, a null handler and a duplicate key are each refused AND counted, with every attempt/accept/refuse reason asserted | nothing about the real image |
| real translated guest code executes and returns its own result | the same test: 1 executed block, `fallback.calls == 0`, and the guest's `v0` holds the value the fixture's instruction produces | the fixture is a synthetic PS-X EXE, not `SLUS_010.40` |
| `callOriginal` reaches the guest body rather than recursing | both overloads (`NativeKey` and address) return the value only the GUEST body produces, with `executedBlocks > 0` | one call each, on a fixture |
| the bounded turn reports a typed exit | an infinite `b .` ends in `BudgetExhausted` with a PC inside the loop and non-zero cycles | the budget's size is psxport's, not measured here |
| an overlay publication retires the prior generation's keys | a TITLE-scoped leaf is unreachable after BATTLE publishes into `0x80068800`, while the resident leaf survives | two synthetic 256-byte images |
| the resident leaf S007 verified is reachable | `hasNativeOverride(core, resident, heap::kInitHeap)` is true on the published generation and false on generation+1 | whether a real boot INVOKES it — now answered by issue 0041 |
| the telemetry census closes | `accepted + refused == attempts`, per-reason attribution, capacity overflow counted not dropped | that a real run's numbers are non-zero — answered by issue 0042 |
| the launcher builds and launches the shipping target | `test_launcher` with the process boundary injected: it provisions, configures, builds, launches, and refuses before configuring when provisioning fails | that it ever launched anything |
| the product links no retired interpreter | `tools/verify.py` `verify_product_link`: 0 of 3 retired entry points and 0 of 3 generated-corpus symbols in `nm -C` of the shipped binary | that no block is ever INTERPRETED at run time — that is `fallback.calls`, read in issue 0042 |

Every mutation above was applied to the shipping source, not to a fixture, and each failed naming its
own subject. Two gaps in the suite were found that way and fixed: no test could produce a
`refusedDispatcher` refusal at all (psxport refuses a DUPLICATE key, and the test only installed
distinct ones), and only the address overload of `callOriginal` was exercised, which left a
non-suppressing implementation of the `NativeKey` overload invisible.

## Why the first run was gated rather than forced

The workspace's single shared product slot was HELD by a Spyro agent, under an exclusive claim so no
two runs overlap. That is a coordination lock, not an inconvenience, so the implementation and the
gates were done and the run waited. Issue 0041 records the run itself.

## Falsifiers

- If a real run reports `fallback.calls > 0` during boot, "the adapter executes through the dynarec"
  is false as stated and the product's engine-free claim needs its measured bound.
- If `ResidentPhase::begin` faults before `kSetVideoMode`, the measured leaf order does not translate
  on Lightrec and the boot phase — not the adapter — is the defect.
- If the guest VSync fatal fires on the very first field, the host frame boundary is wrong rather than
  the guest loop, and `platformHlePlan`'s measured address would be refuted by the run.
- If `verify_product_link` reports a retired symbol, the interpreter IS in the product and S002 is false.
- If `vagrant_dynarec_dispatch` cannot be made to fail when the census arithmetic is broken, the
  telemetry is decoration and the run-end numbers mean nothing.

## NOT established by this issue

Playability. Nothing here shows BATTLE, gameplay, a scene, or a complete game. `resident_image.h`
deliberately does not re-derive the file's SHA-1 — that is `tools/extract_exe.py`'s rule, and a second
hash over the same rule would be a second answer to "are these this title's bytes".
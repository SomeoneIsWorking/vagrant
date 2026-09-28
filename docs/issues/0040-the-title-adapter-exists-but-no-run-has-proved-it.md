---
id: 40
title: The dynarec title adapter exists and is gate-covered, but NO authenticated-overlay run has presented a frame — the product slot was held
status: open
symptom: S015 was `missing` with one named cause: there was no Vagrant Story adapter to psxport's dynarec-only executor, so `run.sh` refused at a boundary and nothing in the title ran. The adapter is now written, compiled into a shipping executable, and covered by negative cases. It has NOT been run against the real disc, so every capability that depends on a presented frame is still `missing`, not `partial`.
tags: s015,dynarec,adapter,launcher,telemetry,product-slot,run-evidence
created: 2026-09-28
updated: 2026-09-28
---

## The negatives, shown red on their own subjects

A gate nobody has seen fail is not a gate. Every mutation below was applied to the SHIPPING source
(not to a fixture), the target rebuilt, and the named test run. All eleven failed, each naming its
own subject, and the tree was restored after each.

| mutation | how it was caught |
|---|---|
| accept an override with no active image at the address | `the no-image refusal was not attributed to its own reason` |
| accept an override against a generation the caller did not publish | `an override was installed against a generation the caller did not publish` |
| count a refused registration as accepted | `the dispatcher's refusal was not counted as a dispatcher refusal` |
| `callOriginal` by `NativeKey` that does not suppress | `the original call by NativeKey returned a value the guest body does not produce, so suppression did not work` |
| `callOriginal` by address that does not suppress | `the original call by address …` |
| do not count an install attempt | `the refused install was not counted as an attempt` |
| do not attribute a dispatch exit to its reason | `the guest-return exit was not attributed to its own reason` |
| count a non-overlapping write as an overlap | `a write that overlapped a prior generation was not counted as one` |
| drop a census overflow silently | `invocations past the census capacity were dropped without saying so` |
| launcher: build and launch after provisioning failed | `the route configured after provisioning failed` / `the route built after provisioning failed` |
| launcher: `--prepare-only` also launches | `--prepare-only launched the product` |

**TWO MUTATIONS DID NOT FAIL on the first pass, and both were gaps in the test rather than in the
product.** Recording that, because a suite that passed while two of its subjects were unreached is
exactly the failure this repository is built to avoid:

1. **No test could produce a `refusedDispatcher` refusal at all.** psxport's dispatcher refuses an
   incomplete or DUPLICATE key; the test only ever installed distinct keys, so the counter had a
   reason code that no test reached. A denominator nobody has seen fire is decoration. Case (e) now
   registers the same key twice.
2. **Only the address overload of `callOriginal` was exercised.** Replacing the `NativeKey` overload's
   `psx::cpu::callOriginal` with a plain `dispatchGuest` — which does NOT suppress the override — left
   the suite green, because that overload was dead code under test. Both overloads are now exercised,
   each asserting the value only the GUEST body produces.

## What exists now

`game/core/dynarec_dispatch.{h,cpp}` is the title's whole adapter surface over `psx::cpu`, in five
operations: image-scoped install, finite call, bounded turn, original call, and a named fatal on a
call that did not return. It mirrors `crash/game/core/dynarec_dispatch.cpp` in SHAPE and in nothing
else — no crash addresses, no crash policy, no crash diagnostics domain, no `RenderCapabilities`
decision. `vagrant::dynarec` is the only module in this repository that spells a budget, resolves an
image identity, or chooses a dispatch form, so there is one answer to "how long may a turn run"
(`psx::cpu::ExecutionBudget::currentTurn`) rather than two.

`game/core/application.{h,cpp}` composes it. `game/main.cpp` is a one-call entry point.
`tools/launcher/runtime_boundary.py` no longer refuses a product: it provisions the measured inputs,
configures, builds `vagrant_port`, and launches it. The `vagrant_port` CMake target went from
`COMMAND false` to a real `add_executable`.

## Why no run happened

`$PSX/coord/claims/product-slot/claim.md` was HELD by a Spyro agent until 2026-09-29T12:00, with an
exclusive claim on the single shared product slot so no two runs overlap. This is a coordination
lock, not an inconvenience, so the implementation and the gates were done and the run was not.

**This is the honest state: the adapter exists and is gate-covered; the title does not run.** Those
are different claims, and only the first is established. S015 stays `missing` because its own
wording is that the title executes authenticated guest images — which is a statement about a run.

## What is genuinely established, and by what

| claim | evidence | what it does NOT establish |
|---|---|---|
| The adapter installs image-scoped overrides and refuses a wrong generation | `vagrant_dynarec_dispatch`, 7 groups; an unscoped install, a stale-generation install, a null handler, and a DUPLICATE key are each refused AND counted, with every attempt/accept/refuse reason asserted | nothing about the real image |
| Real translated guest code executes and returns its own result | same test: 1 executed block, `fallback.calls == 0`, and the guest's `v0` holds the value the fixture's instruction produces | the fixture is a synthetic PS-X EXE, not `SLUS_010.40` |
| `callOriginal` reaches the guest body rather than recursing | same test: BOTH overloads (`NativeKey` and address) return the value only the GUEST body produces, and `executedBlocks > 0` | one call each, on a fixture |
| The bounded turn reports a typed exit | same test: an infinite `b .` ends in `BudgetExhausted` with a PC inside the loop and non-zero cycles | the budget's size is psxport's, not measured here |
| An overlay publication retires the prior generation's keys | same test: a TITLE-scoped leaf is unreachable after BATTLE publishes into `0x80068800`, while the resident leaf survives | two synthetic 256-byte images |
| The resident leaf S007 verified is now reachable | `hasNativeOverride(core, resident, heap::kInitHeap)` is true on the published generation and false on generation+1 | it has not been INVOKED by a real boot |
| The telemetry census closes | `accepted + refused == attempts`, per-reason attribution, capacity overflow counted not dropped | that a real run's numbers are non-zero |
| The launcher builds and launches the shipping target | `test_launcher` 16/16 with the process boundary injected: it provisions, configures, builds `vagrant_port`, launches, and refuses before configuring when provisioning fails | it never launched anything |
| The product links no interpreter | `tools/verify.py` `verify_product_link`: 0 of 3 interpreter entry points in `nm -C` of the shipped binary | that no block is ever INTERPRETED at run time — that is `fallback.calls == 0` in a real run, still unmeasured |

## What a run would settle, in order

1. **Does the resident bootstrap reach TITLE?** `Application::run` calls `core.runtime->bootInit` →
   `ResidentPhase::begin` → the measured leaf order. Whether each of those leaves translates on
   Lightrec is unknown; `vagrant_cadence` and `re_resident` read the BYTES, not the translation.
2. **Where does the first fatal land?** The historical static-recomp runs stopped at
   `_initIntroMovie` (issue 0035). Under the dynarec runtime the stop point can differ, and this run
   is the only way to learn it. The mandatory fatal is guest VSync `0x8001F6C4`, now bound by
   `VagrantRuntime::platformHlePlan` — so a guest VSync is a NAMED, reported refusal rather than a
   hang.
3. **Is `fallback.calls == 0`?** The framework allows bounded per-reason fallback. A non-zero
   fallback count on a boot that looks fine would change S015's claim from "dynarec-only" to
   "dynarec with recorded fallback", and the run-end line prints both.
4. **Does a frame present, and is the guest state readable through the loopback surface?**
   `Application::run` starts `dbg_server`, so `rw`/`w16`/`regs`/`shot` are live. A boot log is not
   this: this workspace records that boot, logos, menus and a clean trace do not establish gameplay.
5. **Does `vs_main_initHeap`'s native leaf plus original call behave on the real image?** The
   override seeds the free list and then re-enters the guest body; whether the real body agrees with
   the seeded state is only observable by reading the control blocks back.

## Falsifiers

- If a real run reports `fallback.calls > 0` during boot, "the adapter executes through the dynarec"
  is false as stated and the product's engine-free claim needs its measured bound.
- If `ResidentPhase::begin` faults before `kSetVideoMode`, the measured leaf order does not translate
  on Lightrec and the boot phase — not the adapter — is the defect.
- If the guest VSync fatal fires on the very first field, the host frame boundary is wrong rather than
  the guest loop, and `platformHlePlan`'s measured address would be refuted by the run.
- If `verify_product_link` reports a symbol, the interpreter IS in the product and S002 is false.
- If `vagrant_dynarec_dispatch` cannot be made to fail when the census arithmetic is broken, the
  telemetry is decoration and the run-end numbers mean nothing.

## NOT established by this issue

Playability. Nothing here shows BATTLE, gameplay, a scene, or a complete game. `resident_image.h`
also deliberately does NOT re-derive the file's SHA-1 — that is `tools/extract_exe.py`'s job, and a
second hash over the same rule would be a second answer to "are these this title's bytes".

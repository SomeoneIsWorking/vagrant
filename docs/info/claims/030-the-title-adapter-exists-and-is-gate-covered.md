---
id: C030
kind: claim
status: holds
created: 2026-09-28
tags: s015,dynarec,adapter,launcher,telemetry,image-identity
depends: game/core/dynarec_dispatch.cpp#installNativeOverride, tests/test_dynarec_dispatch.cpp
---

## Claim

Vagrant Story HAS a title adapter to psxport's per-`Core` dynarec-only executor, and it is registered
from the launcher's own composition chain. `vagrant::dynarec` is the only module in this repository
that resolves an image identity, spells a budget, or chooses a dispatch form, and every image-scoped
native leaf is installed through it with all-or-nothing semantics.

## Scope of the claim, stated because the gap is easy to overstate

This claims the ADAPTER AND ITS GATES. It does not claim the title runs, and the two are different
statements. No authenticated-overlay run has happened: the workspace's single product slot
(`$PSX/coord/claims/product-slot/claim.md`) was HELD by a Spyro agent until 2026-09-29T12:00. S015
therefore stays `missing`. See
`docs/issues/0040-the-title-adapter-exists-but-no-run-has-proved-it.md`.

## Evidence

`tools/verify.py` — compile-backed 38 of 38 first-party C++ units; 18 CTests, 17 passing; the single
failure is `vagrant_psxport_pin_live`, which is the pin guard working (the shared framework advanced
to `b951d747`; this repo records `424d546e`, which the brief says not to touch).

`vagrant_dynarec_dispatch` (CTest 10) exercises the shipping seam through 7 groups, and its value is
in the negatives:

| negative | what it rules out |
|---|---|
| an override installed with no active image at the address | attributing a leaf to whichever module happens to be resident |
| an override installed against a generation the caller did not publish | a retired key answering for a new body |
| an override with a null handler | an installed, uncallable key |
| a TITLE-generation leaf still reachable after BATTLE publishes into `0x80068800` | overrides surviving an overlay that reuses the address slot |
| the resident leaf retired by that same overlay | the test also asserts it SURVIVES, and states why: resident text ends at `0x80062000` and the overlay base is `0x80068800`, so those ranges are disjoint. An earlier draft of this claim asserted the overlap and was WRONG — the bytes refute it, and `tools/re_overlay.py` measures all three overlay bases |
| `callOriginal` returning the native handler's value instead of the guest's | suppression not re-entering the retail body |
| an infinite `b .` not ending in `BudgetExhausted` | a turn with no bounded exit |
| `accepted + refused != attempts` | a census whose zeros are unattributable |
| a reason with no exits reporting one | a zero that cannot be read as "scanned and found none" |
| capacity overflow silently dropping an invocation | a census that truncates into a quiet pass |

`tools/verify.py::verify_product_link` — `nm -C` on the shipped `vagrant_port` binary finds 0 of 3
interpreter entry points. S002's claim is about the LINKED PRODUCT, not about repository text, and a
source pattern cannot establish it. This check runs before `ctest` and independently of its result, so
one unrelated failure cannot suppress it.

`tests/test_launcher.py` — 16/16 with the process boundary injected. It asserts the zero-argument
route provisions, configures, builds `vagrant_port`, and launches it; that it refuses BEFORE
configuring when provisioning fails; and that a refusal names the stage and the tool rather than a
boundary. `--prepare-only` builds without launching, because launching opens a window and plays
audio and belongs to a player, not a check.

`game/core/application.cpp` binds the measured guest VSync (`0x8001F6C4`, derived by
`tools/re_vblank.py` from the authenticated executable) through `platformHlePlan`, so a guest VSync
is a NAMED fatal rather than a hang, and the product is refused before boot if that measurement is
absent.

## What would falsify it

- An override installing against an ambiguous or absent image without refusing, by name, with the
  address. That is the exact mechanism this title needs: BATTLE, TITLE and ENDING all load at
  `0x80068800`.
- `callOriginal` re-entering the native handler instead of the guest body — which would recurse.
- A second module in this repository spelling an `ExecutionBudget` or resolving an image identity.
  Then "one dispatch policy" is two answers.
- `verify_product_link` reporting a symbol: the interpreter IS in the product and S002 is false.
- `vagrant_dynarec_dispatch` passing while the census arithmetic is broken. A telemetry gate that
  cannot fail makes every run-end number decoration.
- A run reporting `fallback.calls > 0`, which would refute "dynarec-only" as stated rather than
  refine it. This is NOT a falsifier of THIS claim — the claim is about the adapter's existence and
  its gates — and recording it here is the point: the claim deliberately does not extend that far.

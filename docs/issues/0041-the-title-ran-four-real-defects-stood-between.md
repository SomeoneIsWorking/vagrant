---
id: 41
title: The title ran for the first time — four sequential real defects stood between the adapter and the first host field, three are fixed, and `fallback.calls` is STILL unmeasured
status: open
symptom: S015 has been `missing` its whole life because nothing had ever run. This run is the first
  authenticated execution of SLUS_010.40 through psxport's dynarec. It did not boot, and the reason
  was not one bug but FOUR, in sequence, each of which a test could pass around: the product never
  installed its `GameRuntime`, its native-leaf table was registered from two boundaries, its
  `PlatformHlePlan` declared no stock libcd leaves, and its projection owner cross-checks the
  resident's display-area publication against BATTLE's viewport rectangle. The first three are fixed
  at root cause here. The fourth is named with its proper fix and NOT patched. Consequently
  `fallback.calls` remains UNMEASURED, and the zeros that were printed carry `executor_calls=0`, so
  they are "the instrument never ran" and not "scanned and found none".
tags: s015,dynarec,run-evidence,product-slot,fallback,platform-hle,projection
created: 2026-09-28
updated: 2026-09-28
---

## What ran, and how far — the guest's own words, not an impression

`tools/run.py --prepare-only` provisioned the authenticated inputs, configured, and built
`vagrant_port`; the product was then launched headless, silent and unpaced through psxport's own
`agent_environment` (the product slot was held; `coord/claims/product-slot/claim.md`, expires
2026-09-29T13:40). Verbatim, in order:

    [vagrant-owners] resident native owners registered against image 1/1: 1 allocator leaf + 4 measured projection publication leaves
    [vagrant-boot]   authenticated resident image: scratch/bin/vagrant/SLUS_010.40 (337920 bytes, sha256 51dfdf15a...), entry 0x8001F544, text 0x80010000+0x52000, stack 0x801FFFF0, image 1/1
    [plat-hle]      3 direct-runtime hardware services installed
    [vagrant-boot]   entering the bounded Vagrant Story product loop
    [dbgsrv]        listening on 127.0.0.1:5949
    [gpu_vk]        present image 960x720 (headless sink)
    [vagrant-proj:error] SLUS_010.40 published a 320 wide draw area while its own viewport rectangle holds 0

So: **the resident image is authenticated and published, the image-scoped native leaves install,
three platform services install, the boot phase completes, the product enters its loop, binds the
live control channel, and reaches a presented headless frame in its FIRST host field.** It dies in
that same field.

## The four fatals, classified three ways as the brief requires

A fault, a budget exit and a translation refusal are three different problems. So is "refused
before any guest state was touched", which is a fourth and is listed because it was the first one.

| # | what | classification | evidence |
|---|---|---|---|
| 1 | `Game construction did not create this Core's VagrantContext` | **refusal before any guest state** — a composition defect, not a guest observation | `Core::Core()` snapshots `psxport_game_runtime()` and calls its `createContext`; the product constructed `Game` having installed nothing, so `core.runtime` AND `core.gameCtx` were both null. Every later deref of `core.runtime` was undefined; the `gameCtx` guard fired first and hid that. |
| 2 | `refused duplicate override 'Vagrant vs_main_initHeap' at image 1:1 address 0x80043F74; owned by 'Vagrant vs_main_initHeap'` | **dispatcher refusal of a duplicate key** | `installResidentNativeOwners` was called from BOTH `VagrantRuntime::loadResidentImage` (the documented publication boundary) and `Application::start`. The first call installed; the second was a duplicate by construction. |
| 3 | `resident call0 required a completed guest call, but execution exited as budget-exhausted at 0x8002105C after 564502 cycles: cycle budget exhausted` | **BUDGET EXIT** — not a fault, not a translation refusal | Host field 0, `ResidentPhase::finishInitCard`. Retail `CD_sync` (`0x80020F28`..`0x800211A8`) spun on its completion poll until the one-field cycle budget (33'868'800/60 = 564,480) expired. A WAIT, not compute: psxport's CD controller completes commands synchronously and models no controller IRQ, so the poll can never be satisfied. Resuming the turn would only spin again. |
| 4 | `published a 320 wide draw area while its own viewport rectangle holds 0` | **owner cross-check disagreement** — a wrong premise in the owner, not guest state | Host field 0, resident `_initScreen` → `SetDefDispEnv` (`0x8002B434`) with `a3` = `0x140` = 320, read from the CC0 decompilation at `main.c:8073`. The owner compared it against `0x8005DFD6`, which `game/render/battle_projection_facts.h` itself documents as written by **BATTLE's** presenter at `0x800761E0..0x80076200` in `BATTLE.PRG`. The boot's rectangle and BATTLE's rectangle are different words with different owners. |

Addresses and register state for #3 and #4, as read: at #3, `0x8002105C` is inside `CD_sync`
(the decompilation's `symbol_addrs.txt` bounds it `CD_sync = 0x80020F28`, next symbol
`CD_ready = 0x800211A8`), reached from `ResidentPhase::finishInitCard`'s first `call0(kCardStart)`;
`sp` was not captured because the process aborts inside the executor and the framework reports the
PC and the cycle count, not a register dump. **No fault and no translation refusal occurred at
any point in this run** — there is no `faults=` count, no `Fault` exit, and no
`threshold-exceeded` fallback line in any log.

## THE HEADLINE, and it is NOT a number

**`fallback.calls` is UNMEASURED.** Not zero — unmeasured, and the distinction is the whole point.

The product reaches `reportRunEnd` only when its `for (frame = 0;; ++frame)` loop ends, and it
aborts inside field 0, so the run-end report is never reached. The live reading over the loopback
control surface (`guest`, which prints `fallback.calls` and every per-reason counter) requires one
`serviced` frame, and `DbgServer::service` is called AFTER `shell.step` in the title's spine — so the
abort happens before the surface can answer once. A driver that binds the endpoint, sends `pause`,
and asks for `guest` gets a broken pipe, which is what the scratch harness in
`scratch/run1/driver.py` does and shows.

The only `fallback` lines this title has ever printed are the shutdown ones, and they read:

    Lightrec fallback telemetry [shutdown]: executor_calls=0 executed_blocks=0 executed_instructions=0 fallback_blocks=0 ...

**`executor_calls=0` with `fallback_blocks=0` is "the instrument never ran", not "scanned and found
none".** Quoting that zero as the answer would be exactly the failure this repository is built to
avoid, so it is recorded here as the absence of a measurement and not as a measurement.

What CAN be said, with its bound and no further: the product itself printed
`PSXPORT_LIGHTREC_FALLBACK_BLOCK_LIMIT = 1`, so any fallback the framework admitted was at most ONE
block per executor call, and exceeding it prints `reportFallbackTelemetry("threshold-exceeded")`. No
such line appeared in any of the four runs. So the run's fallback was 0-or-1 block per executor
call, unmeasured — which is a bound, not the number.

## `verify_product_link` is a FALSE NEGATIVE, and the run is what found it

The gate reports `product link: 0 of 3 interpreter entry points present in the shipped executable`
and S002 leans on it. `nm -C` on the same binary says:

    0000000000722a30 T lightrec_run_interpreter
    0000000000736940 T lightrec_emit_jump_to_interpreter

**The interpreter IS in the product.** The three symbols the check looks for
(`xemu_interpret_block`, `int_exec`, `psx_cpu_interpret_step`) belong to the interpreter psxport
RETIRED; the interpreter this product actually contains is Lightrec's own per-block interpreter
(`vendor/beetle-psx/deps/lightrec/lightrec.c:1921`, reached from JIT code through
`lightrec_emit_jump_to_interpreter`). The check is green because it asks about a component that is
not in the execution path, and it is stated in the strongest possible terms — "the product links no
interpreter", "S002's claim is about the LINKED PRODUCT". That is this workspace's signature
failure: **an instrument answering a different question than the one asked**, and it went green on
the one title that had never run.

This is also why `fallback.calls` is the only possible answer to "is this dynarec-only": a link
check cannot answer it, in either direction.

## The proper fix for #4, and why it is not patched here

`BattleProjectionOwner::observeDrawArea` cross-checks the publication's stated width against
`kViewportWidthWord`. That is only a valid second statement of one horizontal extent when the
publication IS BATTLE's presenter publication. It is not: the owner is installed on the RESIDENT
generation, so it also sees the resident's own `SetDefDispEnv`.

The obvious "fix" — tolerate a zero rectangle — is a special case for the failing input and would
disable the check for the whole boot, which is where the boot's own geometry is published. It is
refused.

The check the owner should make instead is against the rectangle the publication ITSELF writes. For
the resident's `SetDefDispEnv` that is inside the `DISPLAYENV` struct at `a0`, and the
decompilation says it will not agree either:

    SetDefDispEnv(vs_main_dispEnv, 0, 0, w, h - 16);   // main.c:8073 — env 320 wide
    setRECT(&vs_main_dispEnv[0].screen, 0, 8, 256, 224);  // main.c:8074 — screen RECT 256 wide

which is the recorded 320x240→320x224 convention, not a contradiction. So the premise "these are two
statements of one horizontal extent" is false for this title's display-area publication, and
deciding WHICH word is the display area's own horizontal extent is an `tools/re_viewport.py`
measurement on the RESIDENT display-area body — the same instrument that already read the BATTLE
body from bytes (`docs/issues/0038`). That is a real piece of work with its own gate, it touches the
owner S009/S010/S011 are built on, and it is not a patch this task should improvise while chasing a
first number. **The product does not start until it is done, and that is the correct behaviour.**

## What is fixed here, at root cause, each with its gate

1. **`game/core/application.cpp`** — a namespace-scope `VagrantRuntime` is installed with
   `psxport_install_game` BEFORE the `Game` is constructed, with the ordering and the destruction
   order stated in the comment. The old `gameCtx`-only guard is kept and a `runtime`-null check was
   added beside it.
2. **`game/core/vagrant_runtime.cpp`** — `loadResidentImage` is the ONE registration call site and
   it refuses the LOAD itself on a partial registration, so the composition owner neither
   re-registers the table nor duplicates the all-or-nothing check. `platformPlan_` became an
   aggregate initialiser (a static-storage lambda could throw during construction).
3. **`game/core/vagrant_runtime.cpp` + `game/sync/vsync_facts.h`** — `vsyncQueryCounterAddress` is
   declared from the already-measured `0x80032114`, and `cdCommandAddress` / `cdSyncAddress` are
   declared from `game/cd/cd_facts.h`'s already-measured `0x80021470` / `0x80020F28`, with three
   one-instruction admission windows. `stockCdWorkArea` is deliberately left zero and says why.
4. **`tools/re_vblank.py`** — the new `kVSyncQueryCounter` constant is gated by `--check-source`
   against the same SHA-bound measurement that produced it, and the selftest grew a NEGATIVE case
   that perturbs the shipped constant by +4 and requires the refusal to name it. 4/4, shown red on
   its own subject.

The gate is **18/18 CTest** and the product link check still passes, but **`tools/verify.py` still
exits FAIL**, on the clang-tidy stage alone. The `clang-format` and `clang-tidy` stages were red
BEFORE this work — 56 format violations and a large clang-tidy debt, all from `9eb8b55` — and are now
at **0 format violations and 13 clang-tidy findings**, none of which is in code this issue wrote.
The 13 are 12 `bugprone-unchecked-optional-access` in two test files and one
`bugprone-easily-swappable-parameters` on `ExecutionTelemetry::recordExecutableWrite(uint64_t bytes,
uint64_t overlappedBytes)`, which is a real API defect in a new module and wants a named struct, not
a suppression. The brief's "gate at 17/18" was about CTest: the style stages were never green, which
is worth recording because "18/18" would otherwise have been read as a green gate.

## Falsifiers

- If a run of the current tree reaches `SetDefDispEnv` with `a3` != 320, the decompilation
  attribution of that leaf to the resident's `_initScreen` is wrong and fatal #4 is somewhere else.
- If `lightrec_run_interpreter` were absent from a Release `vagrant_port`, this issue's reading of
  `verify_product_link` would be wrong and the gate would need a different subject, not a different
  symbol list.
- If the projection owner is proved to be right and the BATTLE rectangle to be stale rather than
  unrelated, then #4 is a guest-state bug and not a wrong premise, and the proper fix is upstream in
  what the boot publishes rather than in the owner.
- If a run that DOES survive a field reports `fallback.calls > 0`, "dynarec-only" is false for this
  title and the per-reason breakdown — not this issue — is what says which instruction class is
  unsupported.
- If the abort in field 0 turns out NOT to be inside `shell.step` (so a serviced frame precedes it),
  the claim that the live control surface cannot answer before the abort is wrong, and one command's
  reachability would settle it.

## NOT established by this issue

`fallback.calls`. Any translated/executed block count. Any guest state read back over the control
surface. Any frame looked at — the product reaches a headless present, but `shot` needs the surface
that field 0 does not reach, so there is no captured picture and no gameplay claim of any kind.
Playability, TITLE, BATTLE, widescreen, interpolation: all still `missing`.

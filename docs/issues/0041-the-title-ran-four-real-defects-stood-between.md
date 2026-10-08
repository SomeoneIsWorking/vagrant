---
id: 41
title: The title ran for the first time — four sequential real defects stood between the adapter and the first host field
status: open
symptom: S015 was `missing` its whole life because nothing had ever run. This was the first authenticated execution of SLUS_010.40 through psxport's dynarec. It did not boot, and the reason was not one bug but four, in sequence, each of which a test could pass around. All four are now fixed at root cause (the fourth by issue 0042).
tags: s015,dynarec,run-evidence,product-slot,fallback,platform-hle,projection
created: 2026-09-28
updated: 2026-09-28
---

## What ran, and how far — the guest's own words

The product was provisioned, built, and launched headless, silent and unpaced through psxport's
`agent_environment` (the product slot was held). Verbatim, in order:

    [vagrant-owners] resident native owners registered against image 1/1: 1 allocator leaf + 4 measured projection publication leaves
    [vagrant-boot]   authenticated resident image: SLUS_010.40 (337920 bytes, sha256 51dfdf15a...), entry 0x8001F544, text 0x80010000+0x52000, stack 0x801FFFF0, image 1/1
    [plat-hle]      3 direct-runtime hardware services installed
    [vagrant-boot]   entering the bounded Vagrant Story product loop
    [dbgsrv]        listening on 127.0.0.1:5949
    [gpu_vk]        present image 960x720 (headless sink)
    [vagrant-proj:error] SLUS_010.40 published a 320 wide draw area while its own viewport rectangle holds 0

So the resident image authenticates and publishes, the image-scoped leaves install, the platform
services install, the boot phase completes, the loop is entered, the control channel is bound, and a
headless frame presents — in the FIRST host field, where it then dies.

## The four fatals

A fault, a budget exit and a translation refusal are three different problems, and "refused before any
guest state was touched" is a fourth.

| # | what | classification | cause and fix |
|---|---|---|---|
| 1 | `Game construction did not create this Core's VagrantContext` | refusal before any guest state | `Core::Core()` snapshots `psxport_game_runtime()`; the product installed nothing, so `core.runtime` and `core.gameCtx` were both null. Fixed: `Application` installs the namespace-scope `VagrantRuntime` with `psxport_install_game` **before** constructing `Game`. |
| 2 | `refused duplicate override 'Vagrant vs_main_initHeap'` | dispatcher refusal of a duplicate key | `installResidentNativeOwners` was called from both the image publication boundary and `Application::start`. Fixed: `loadResidentImage` is the one registration call site and refuses the LOAD on a partial registration. |
| 3 | `resident call0 ... budget-exhausted at 0x8002105C after 564502 cycles` | **budget exit — a wait, not compute** | Retail `CD_sync` (`0x80020F28..0x800211A8`) spun on its completion poll; the host CD controller completes commands synchronously and models no controller IRQ. Fixed in issue 0042 by declaring the guest CD-ready callback layout, not by widening the budget. |
| 4 | `published a 320 wide draw area while its own viewport rectangle holds 0` | owner cross-check disagreement — a wrong premise | The owner compared the publication against `0x8005DFD6`, which is **BATTLE's** rectangle, not the boot's. Fixed in issue 0042: the owner now measures the leaf's own `env + 4` word. |

## What was NOT established

`fallback.calls` was UNMEASURED in this run, not zero. The product aborts inside field 0, before
`DbgServer::service`, so the live surface could not answer once and the run-end report was never
reached; the only `fallback` lines printed were shutdown ones carrying `executor_calls=0`, which means
"the instrument never ran". Issue 0042 superseded this with a real reading.

The link check was also a false negative here: it looked for the three symbols of the interpreter
psxport RETIRED, while the product links Lightrec's own per-block interpreter, which the architecture
keeps for bounded accounted fallback. `tools/verify.py` now reports that interpreter as present and
permitted, and names `fallback.calls` as the only number that answers "is this dynarec-only".

## NOT established by this issue

Any TITLE phase, any gameplay, playability, widescreen, interpolation: all still `missing`.
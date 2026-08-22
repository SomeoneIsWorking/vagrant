---
id: C019
kind: claim
status: holds
created: 2026-08-22
tags: 
depends: game/core/vagrant_runtime.cpp#VagrantRuntime::configureRenderPath, game/core/vagrant_runtime.cpp#VagrantRuntime::bootInit, game/core/vagrant_runtime.cpp#VagrantRuntime::registerOverrides, game/core/game_hooks.cpp, game/core/main.cpp, tests/test_vagrant_runtime.cpp
reconfirmed: 2026-08-22 19:09:18
verified_at: 2026-08-22 19:09:18
---

## Claim

Vagrant Story installs one derived VagrantRuntime that owns the direct-native render default,
measured guest-main dispatch, and CD/VBlank override composition; the legacy GameHooks
bootInit/registerOverrides slots are null.

## Evidence

2026-08-22: vagrant_runtime_test passed against psxport 7f5d3f13, checking derived types, installed Core identity, non-null compatibility views, null legacy behavior slots, and exactly one call to each override owner; full vagrant_port linked and a bounded real run reached the unchanged TITLE watchdog boundary.

## What would falsify it

the project default no longer resolves to native, a boot/override behavior slot becomes non-null in
compatibilityHooks, main installs the legacy pair directly, Core no longer snapshots VagrantRuntime,
or the bounded boot fails before the previously verified TITLE boundary

## Re-confirmed 2026-08-22 14:15:50

2026-08-22: vagrant_runtime_test passed against psxport 7f5d3f13, checking the direct-native default, derived types, installed Core identity, non-null compatibility views, null legacy behavior slots, and exactly one call to each override owner. Full vagrant_port linked; a bounded real-disc run selected native, dispatched guest main, armed VBlank, entered TITLE 0x80071334 work, and reached the unchanged no-present watchdog boundary.

## Re-confirmed 2026-08-22 17:51:59

2026-08-22 VagrantRuntime inheritance/context ownership, render default, override composition and boot dispatch rebuilt with Clang; full 6/6 CTest including clang-format/tidy/structure passed; owned-disc default route rendered the first splash

## Re-confirmed 2026-08-22 18:14:40

2026-08-22 against recorded/built psxport ad5cf802: derived-runtime/context tests, full Clang CTest 6/6, shipping real-disc positive, and compile-time producer-disabled negative all pass

## Re-confirmed 2026-08-22 18:46:01

2026-08-22: vagrant_runtime_test and full CTest 6/6 pass after composing per-Core TitleMovieProducer; shipping disassembly retains the generated TITLE callback super.

## Re-confirmed 2026-08-22 19:09:18

2026-08-22 against recorded/built psxport 57a17a14: fresh 799-resident/137-TITLE emission, Clang build, vagrant_runtime_test, full CTest 6/6, shipping real-disc positive, and producer-disabled negative all pass.

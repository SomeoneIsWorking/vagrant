---
id: C019
kind: claim
status: holds
created: 2026-08-22
tags: 
depends: game/core/vagrant_runtime.cpp#VagrantRuntime::configureRenderPath, game/core/vagrant_runtime.cpp#VagrantRuntime::bootInit, game/core/vagrant_runtime.cpp#VagrantRuntime::registerOverrides, game/core/game_hooks.cpp, game/core/main.cpp, tests/test_vagrant_runtime.cpp
reconfirmed: 2026-08-22 14:15:50
verified_at: 2026-08-22 14:15:50
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

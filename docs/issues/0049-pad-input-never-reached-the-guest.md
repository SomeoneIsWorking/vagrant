---
id: 0049
title: Pad input never reached the guest
status: resolved
symptom: tap/hold had no effect on the movie or menu
tags: S004,S006,S013,title,cd
created: 2026-10-09
updated: 2026-10-09
---

`game/runtime/vagrant_runtime.cpp:VagrantRuntime`: no `guestPadBufferLayout()`, so `biosPadShouldService` never delivered.

## Fix

Declare the measured PadInitDirect buffers.

## Test

`declaresThePadReceiveBuffers` in `tests/test_dynarec_dispatch.cpp`.

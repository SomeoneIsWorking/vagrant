---
id: 34
title: TITLE _initMemcard waits forever on interrupt-driven SPMCIMG queue
status: resolved
symptom: After the native save-check removes guest gametimeUpdate/VSync, the exact product remains black after field 739 because _initMemcard(0) never observes its first retail CD queue slot as Loaded.
tags: S003,S004,S013,title,memcard,cd-queue,native-ownership,re-23
created: 2026-08-27
updated: 2026-08-27
---

## Live evidence

Exact psxport `3c342ec3` Clang product PID 3213121 completed 1000/1000 native-owned fields with zero dropped layers and no guest-VSync violation. Exactly 728 splash sprites covered fields 12..739. Captures at fields 749, 750, 751, 752, 760, 780, 800, 850, 900, and 950 were all 0/691,200 non-black, and the TITLE save-check completion log was absent.

## Root cause

SHA-bound TITLE bytes and the CC0 decomp agree that `_initMemcard` enqueues SPMCIMG.BIN and then MCDATA.BIN+MCMAN.BIN through the retail asynchronous libds queue. psxport completes CD commands synchronously and models no controller IRQ, so the callback that marks these newly enqueued slots Loaded cannot run. The wait is before `_memcardEventHandler`; it is not a card-event bug.

## Proper fix

Native-own `_initMemcard` as finite staged disc reads of exact extents `(85144,0x1C000)` and `(85200,0x2000)`, while preserving heap allocation, overlay pointer graph, SPMCIMG upload, reset policy, and eight-event open/enable lifecycle. Retain the generated body as the override super/A-B path; do not fake queue completion or weaken guest VSync.

## Implementation state

`TitleMemcardInit` and `tools/re_title_memcard.py` implement and gate that boundary. Measurement passes 33/33 facts plus 4/4 destructive controls; the runtime boundary contract and full fresh Clang CTest suite pass 8/8. No post-implementation game run has been made yet, so the issue remains investigating pending an authorized real-disc falsifier.

### Resolution (2026-08-27)
Exact 3c342ec3 Clang product PID 3309285 live-copied both measured extents, completed TITLE save-file initialization, and reached the _initIntroMovie ownership boundary with 1000/1000 fields, zero drops, and no guest VSync.

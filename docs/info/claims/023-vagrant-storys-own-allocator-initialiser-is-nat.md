---
id: C023
kind: claim
status: holds
created: 2026-08-24
tags: ownership,re-07,heap,override,mirror-verify
depends: tools/re_heap.py#measure, game/core/game_heap.cpp#initHeap, game/core/game_heap.cpp#registerHeapOverride
reconfirmed: 2026-08-24
verified_at: 2026-08-24 20:08:15
---

## Claim

Vagrant Story's own allocator initialiser (vs_main_initHeap 0x80043F74) is owned by a native body seeded from the CC0 matching decomp, and that body provably installed, ran, and byte-matched the substrate on the live boot path

## Evidence

2026-08-24 against psxport d2266f4b and owned SLUS_010.40: tools/re_heap.py derives the call site 0x80042B2C (1 match / 83,964 candidates), target 0x80043F74, and heads 0x800501A8/0x800501B8 from the image bytes; rood labels agree. The real-disc gate prints `[mirror-verify] 0x80043F74 OK (pass #1)` — a line only reachable from inside the override dispatch after both legs run — and the same gate turned RED naming `MISMATCH ram 0x8010C008: native=00 substrate=FF` under a deliberate blockSz sabotage, so hollow substrate-only passes cannot produce it. vagrant_game_heap_test pins the 11-word contract hermetically; ctest 7/7.

## What would falsify it

if re_heap.py --check-source ever reports a shipped constant differing from its measurement, if the live boot no longer prints the override-only `[mirror-verify] 0x80043F74 OK` reach marker, or if mirror-verify reports a mismatch at 0x80043F74 on an unmodified tree

## Re-confirmed 2026-08-24 19:41:40

2026-08-24 against psxport d2266f4b: the shipping recorded-input run printed [mirror-verify] 0x80043F74 OK (pass #1), reached the same 0x800798A4 frontier, and re_heap.py --check-source --selftest passed 5/5; Clang CTest passed 7/7.

## Re-confirmed 2026-08-24

Post-landing re_heap re-derived sole call, body, heads and arena from real bytes with 5/5 controls; hermetic 11/11 heap contract and Clang CTest 7/7 passed; fresh live replay retained mirror-verify OK

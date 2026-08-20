---
id: 10
title: re_crt0 static-assert negatives depended on source alignment
status: resolved
symptom: clang-format made four of five re_crt0 --gate-config negative cases report stale mutation anchors instead of compiling sabotaged inputs
tags: tooling,re-01,clang-format,selftest
created: 2026-08-21
updated: 2026-08-21
---

Root cause: both the shipping-value negatives and static-assert negatives used exact whitespace-sensitive C++ substrings as mutation anchors. Applying the tracked formatter changed alignment without changing constants, so the instrument correctly refused but its negative gate was unusable. Fixed by matching semantic constant assignments and field bindings with bounded regular expressions, requiring exactly one match before mutation. Verified on the SHA-bound executable: re_crt0.py --selftest passes 24/24 and the compile-time assert gate passes 6/6, including all five sabotaged builds.

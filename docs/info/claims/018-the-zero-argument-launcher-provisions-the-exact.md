---
id: C018
kind: claim
status: holds
created: 2026-08-22
tags: launcher,overlay,title
depends: tools/run.py#execute, tools/extract_overlays.py#provision, tests/test_launcher.py
reconfirmed: 2026-08-22 18:14:40
verified_at: 2026-08-22 18:14:40
---

## Claim

The zero-argument launcher provisions the exact resident and TITLE inputs, retains unchanged generated output, Clang-builds vagrant_port, and launches the current headless TITLE-bootstrap target.

## Evidence

scratch/logs/title-overlay-default-launcher.log: executable and TITLE hashes match, extract_overlays verifies 1/1, ensure_recomp reports up to date, Clang build reaches 100%, and the live stack executes ov_title_func_80071334 before the recorded issue #17 watchdog.

## What would falsify it

if ./run.sh needs a hidden mode/argument, re-emits unchanged input, selects a non-Clang build, fails to route TITLE, or claims a non-black/gameplay outcome not established by the run

## Re-confirmed 2026-08-22 18:14:40

2026-08-22 against recorded/built psxport ad5cf802: zero-argument ./run.sh provisions exact resident+TITLE, builds with Clang, renders the publisher splash, then reaches the documented 24-bit boundary

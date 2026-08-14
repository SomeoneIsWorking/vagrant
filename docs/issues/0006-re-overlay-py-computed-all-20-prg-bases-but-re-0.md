---
id: 6
title: re_overlay.py computed all 20 PRG bases but RE-03 remained partial
status: resolved
symptom: Full overlay sweep printed measured: 20 yet exited 1, exposed only one slot, and docs kept 19 non-empty module mappings unknown
tags: re-03,overlay,tooling,instrument
created: 2026-08-14
updated: 2026-08-14
---

## Root cause

The tool conflated incomplete M1 file-descriptor recovery (1/14 candidate sites) with failure of the
independent M2 per-image placement measurement. It built its slot list only from M1-resolved sites,
so the same run could print 20 M2 answers, expose one slot, and exit 1.

## What was tried / dead ends

Extending M1's straight-line argument recovery was not needed to decide the mappings: 13 sites still
do not expose a static disc descriptor in the supported idioms. They remain a stated M1 coverage
limit rather than being silently skipped or promoted into evidence.

## Resolution

### Resolution (2026-08-14)
Made M2 the owned-byte measurement, added M3 as a strict SHA-first rood identity/link-address
corroborator, and derived slots only from M2+M3-verified module bases. Real corpus: 20/20 agreements,
three slots, selftest 7/7, shipping gate 24/24.

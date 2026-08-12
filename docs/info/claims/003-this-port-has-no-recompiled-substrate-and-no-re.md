---
id: C003
kind: claim
status: falsified
created: 2026-08-12
tags: status
depends: game/core/game_config.cpp
falsified_on: 2026-08-12
---

## Claim

This port has no recompiled substrate and no RE'd guest address: every GameConfig address field is 0

## Evidence

game/core/game_config.cpp is all zeros except port facts (discEnvVar, cardEnvVar/Path, paceQuota, windowTitle, preserveVramBackdrop); generated/ does not exist, so cmake does not configure vagrant_port at all (configure output, 2026-08-12). docs/re-frontier.md: 7 entries, 2 todo + 5 blocked, 0 re-verified.

## What would falsify it

any non-zero guest address appearing in game/core/game_config.cpp, or generated/rec_sources.cmake existing

## FALSIFIED 2026-08-12

SUPERSEDED 2026-08-12 by its own stated falsifier: non-zero guest addresses now appear in game/core/game_config.cpp. RE-01 (the crt0/boot group) is MEASURED and re-verified — 11 fields, each with the disassembly line that justifies it (see C004). What REMAINS true and is why this claim mattered: there is still NO recompiled substrate (generated/rec_sources.cmake absent, cmake does not configure vagrant_port), and every OTHER GameConfig group — RE-02 seeds, RE-03 overlay bases, RE-04 CD, RE-05 OT/pool, RE-06 pad, RE-08 HLE — is still zero. Read docs/re-frontier.md (1 re-verified / 6 todo / 1 blocked of 8) rather than treating this claim's replacement as 'the port works'. Grepped for downstream reliance: no doc, source file or tool cites C003 (the only hits are info.py's own selftest fixture, which uses the same id for an unrelated corpus).

> Anything that cited this claim as proof must be re-checked. Grep the repo for it.

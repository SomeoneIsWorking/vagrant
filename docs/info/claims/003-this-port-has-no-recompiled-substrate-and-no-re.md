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

SUPERSEDED first by RE-01's measured non-zero boot group, then fully falsified by RE-02's resident
substrate. `generated/` is reproducibly emitted from the verified PS-EXE entry, `vagrant_port` builds,
and bounded runs execute crt0, guest main, and `_initRand`; with psxport `be03593f` the current boundary
is a no-frame watchdog whose sampled stack is in `Core::mem_w32` beneath generated `0x8002411C`,
without a recompilation miss or BIOS fatal. The sample does not classify the stall.
This does not mean the game works: overlay execution, CD/platform HLE, frame/pad/render ownership, and gameplay remain
open in `docs/re-frontier.md`. Grepped for downstream reliance: no source or tool uses C003 as a current
premise.

> Anything that cited this claim as proof must be re-checked. Grep the repo for it.

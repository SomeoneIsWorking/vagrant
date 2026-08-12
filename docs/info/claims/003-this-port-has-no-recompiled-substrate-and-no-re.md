---
id: C003
kind: claim
status: holds
created: 2026-08-12
tags: status
depends: game/core/game_config.cpp
---

## Claim

This port has no recompiled substrate and no RE'd guest address: every GameConfig address field is 0

## Evidence

game/core/game_config.cpp is all zeros except port facts (discEnvVar, cardEnvVar/Path, paceQuota, windowTitle, preserveVramBackdrop); generated/ does not exist, so cmake does not configure vagrant_port at all (configure output, 2026-08-12). docs/re-frontier.md: 7 entries, 2 todo + 5 blocked, 0 re-verified.

## What would falsify it

any non-zero guest address appearing in game/core/game_config.cpp, or generated/rec_sources.cmake existing

---
id: C002
kind: claim
status: holds
created: 2026-08-12
tags: boot
depends: game/core/game_config.cpp
---

## Claim

Vagrant Story boots SLUS_010.40 directly with no boot stub; its PS-EXE header is entry 0x8001F544, text 0x80010000+0x52000, initial sp 0x801FFFF0, gp0=0

## Evidence

SYSTEM.CNF extracted from the disc reads BOOT = cdrom:\\SLUS_010.40;1 / STACK = 801fff00 / TCB = 4 / EVENT = 16; PS-EXE header read by tools/extract_exe.py on the extracted 337920-byte image (2026-08-12).

## What would falsify it

a disassembly showing the entry point loads and LoadExec's a second image, which would make SLUS_010.40 a stub rather than the engine

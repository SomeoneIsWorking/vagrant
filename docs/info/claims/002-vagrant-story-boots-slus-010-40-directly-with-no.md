---
id: C002
kind: claim
status: holds
created: 2026-08-12
tags: boot
depends: game/core/game_config.cpp, tools/re_crt0.py
reconfirmed: 2026-08-12
verified_at: 2026-08-12
---

## Claim

Vagrant Story boots SLUS_010.40 directly with no boot stub; its PS-EXE header is entry 0x8001F544, text 0x80010000+0x52000, initial sp 0x801FFFF0, gp0=0

## Evidence

SYSTEM.CNF extracted from the disc reads BOOT = cdrom:\\SLUS_010.40;1 / STACK = 801fff00 / TCB = 4 / EVENT = 16; PS-EXE header read by tools/extract_exe.py on the extracted 337920-byte image (2026-08-12).

## What would falsify it

a disassembly showing the entry point loads and LoadExec's a second image, which would make SLUS_010.40 a stub rather than the engine

## Re-confirmed 2026-08-12

STRENGTHENED 2026-08-12 against its own falsifier ('a disassembly showing the entry point loads and LoadExec's a second image'). The entry point IS now disassembled and executed (tools/re_crt0.py, claim C004): 0x8001F544 is a stock SN crt0 that clears .bss, sets sp/gp from _ramsize/_stacksize, calls BIOS InitHeap (0x80026864 = A0:0x39 thunk) and then jal 0x80042C38 (rood-reverse: vs_main_exec) followed by a 'break' — two calls total, no LoadExec, no second image. SLUS_010.40 is the engine, not a stub. One correction to this claim's own wording: the header's initial sp 0x801FFFF0 is what the BIOS shell sets, NOT what the game runs on — crt0 overwrites sp with _ramsize-8 = 0x801FFFF8.

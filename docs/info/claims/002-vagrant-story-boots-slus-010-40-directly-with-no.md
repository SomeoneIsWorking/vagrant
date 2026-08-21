---
id: C002
kind: claim
status: holds
created: 2026-08-12
tags: boot
depends: game/core/game_config.cpp, tools/re_crt0.py
reconfirmed: 2026-08-21
verified_at: 2026-08-21 11:17:52
---

## Claim

Vagrant Story boots SLUS_010.40 directly with no boot stub; its PS-EXE header is entry 0x8001F544, text 0x80010000+0x52000, initial sp 0x801FFFF0, gp0=0

## Evidence

SYSTEM.CNF extracted from the disc reads BOOT = cdrom:\\SLUS_010.40;1 / STACK = 801fff00 / TCB = 4 / EVENT = 16; PS-EXE header read by tools/extract_exe.py on the extracted 337920-byte image (2026-08-12).

## What would falsify it

a disassembly showing the entry point loads and LoadExec's a second image, which would make SLUS_010.40 a stub rather than the engine

## Re-confirmed 2026-08-12

STRENGTHENED 2026-08-12 against its own falsifier ('a disassembly showing the entry point loads and LoadExec's a second image'). The entry point IS now disassembled and executed (tools/re_crt0.py, claim C004): 0x8001F544 is a stock SN crt0 that clears .bss, sets sp/gp from _ramsize/_stacksize, calls BIOS InitHeap (0x80026864 = A0:0x39 thunk) and then jal 0x80042C38 (rood-reverse: vs_main_exec) followed by a 'break' — two calls total, no LoadExec, no second image. SLUS_010.40 is the engine, not a stub. One correction to this claim's own wording: the header's initial sp 0x801FFFF0 is what the BIOS shell sets, NOT what the game runs on — crt0 overwrites sp with _ramsize-8 = 0x801FFFF8.

## Re-confirmed 2026-08-14 11:53:32

Re-verified 2026-08-14 after the RE-03-only game_config.cpp change: tools/re_crt0.py --check-config and --gate-citations remain 0 FAILED; --selftest 22/22 and --gate-config 6/6. Entry still executes crt0 to exactly two calls, InitHeap then gameMain, with no LoadExec.

## Re-confirmed 2026-08-14 12:36:31

Reverified after RE-02: PS-EXE identity/header gate and bounded resident boot agree; crt0 selftest 24/24.

## Re-confirmed 2026-08-21 01:04:32

2026-08-21: re_crt0 concrete execution passed 24/24 and the direct Clang-built port loaded the same PS-EXE entry, applied crt0, and entered guest main with no LoadExec or second-image path.

## Re-confirmed 2026-08-21 02:47:31

2026-08-21: re_crt0 executable identity/check-config/citations/selftest and Clang rebuild passed after RE-09 GameConfig extension.

## Re-confirmed 2026-08-21 03:31:41

RE-10 final gate reran tools/re_crt0.py --selftest clean; explicit Clang rebuild and real no-argument launcher again loaded the SHA-matched SLUS_010.40 at entry 0x8001F544

## Re-confirmed 2026-08-21

Post-landing re_crt0 and live default launcher revalidated the SHA-bound SLUS_010.40 identity and direct boot on psxport 9f1bb927.

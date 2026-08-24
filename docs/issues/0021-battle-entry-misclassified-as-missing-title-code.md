---
id: 21
title: BATTLE entry misclassified as missing TITLE code
status: resolved
symptom: After Start-skip title return, resident caller 0x80042C0C fails at 0x800798A4 even though the guest just loaded BATTLE.PRG and INITBTL.PRG
tags: runtime,overlay,battle,re-15
created: 2026-08-25
updated: 2026-08-25
---

## Root cause

RE-15 described `0x800798A4` as a TITLE target, but resident `vs_main_execTitle`
loads `BATTLE/BATTLE.PRG` into slot 0 and `BATTLE/INITBTL.PRG` into slot 1 before its
direct `jal 0x800798A4` at `0x80042C0C`. The port provisioned and emitted TITLE alone,
so the fixed-overlay router had no BATTLE descriptor or dispatch body after the guest
replaced TITLE in slot 0.

Owned-disc evidence rejects the old classification. SHA-1
`d53aaccc3b3a2fc057d05e0dcea92f7182bc72a9` binds BATTLE to rood-reverse's exact
target; at BATTLE offset `0x110A4`, `0x800798A4` begins
`addiu sp,sp,-0x50; sw s7,0x44(sp); lui s7,0x8006`. The same offset in the separately
SHA-bound TITLE image is data and does not decode as an instruction. BATTLE's entry
then directly calls INITBTL target `0x800FA35C` at `0x800798E4`, so both newly loaded
images are runtime prerequisites, not optional future inventory.

## What was tried / dead ends

Adding `0x800798A4` as a TITLE or resident seed is ruled out: each would decode bytes
from the wrong image at an overlapping guest address. No new seed was needed after the
correct images were supplied; the framework emitter's binary discovery produced both
reached entries.

## Resolution

`tools/extract_overlays.py` now provisions and SHA-verifies BATTLE, INITBTL, and TITLE;
`tools/ensure_recomp.py` requires all three
descriptors plus `ov_battle_func_800798A4`, `ov_initbtl_func_800FA35C`, and the existing
TITLE entry. Against psxport `aa0b2067`, emission must produce all three modules and a
Clang product build links them.

The one authorized bounded Start-replay run (PID 199806) removed the old
`recomp-MISS 0x800798A4`. Its host write-watch backtrace contains
`ov_battle_func_800798A4` / `ov_battle_gen_800798A4` and
`ov_initbtl_gen_800FA35C`, proving actual execution of both newly provisioned modules rather than
descriptor presence alone. It stopped at the later concrete BATTLE target `0x800E6EAC`, called by
INITBTL with return address `0x800FA4A8`; issue #22 owns that distinct emitter defect.

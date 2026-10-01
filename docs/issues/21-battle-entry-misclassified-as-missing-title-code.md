---
id: 21
title: BATTLE entry misclassified as missing TITLE code
status: resolved
symptom: a fast-fail at 0x800798A4 was recorded as an unresolved TITLE target
tags: overlay,battle,routing,re-15
created: 2026-08-24
updated: 2026-08-24
---

Resident `vs_main_execTitle` loads `BATTLE.PRG` into slot 0 and `INITBTL.PRG` into slot 1 **before**
its direct `jal 0x800798A4` at `0x80042C0C`. At BATTLE offset `0x110A4` that address begins
`addiu sp,sp,-0x50; sw s7,0x44(sp)`, and the same offset in the SHA-bound TITLE image is data. BATTLE
then calls the INITBTL entry `0x800FA35C` at `0x800798E4`.

**Dead end:** classifying the address from the decompilation's module map alone. Address identity is
not module identity when TITLE, BATTLE and ENDING share `0x80068800`; image generation decides.

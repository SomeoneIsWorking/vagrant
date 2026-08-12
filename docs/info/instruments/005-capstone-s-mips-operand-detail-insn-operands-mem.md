---
id: I005
kind: instrument
status: DISTRUSTED
created: 2026-08-12
distrusted_on: 2026-08-12
---

## Instrument

capstone's MIPS operand detail (insn.operands[].mem.base, capstone 5.0.7 python bindings) — DO NOT use it to find which register a load/store addresses

## Validated by

CAUGHT LYING 2026-08-12, and the failure is SILENT. Asked 'which gp-relative accesses exist in SLUS_010.40', a census over the whole .text using capstone with md.detail=True returned 0 gp-based memory operands — a clean, plausible-looking negative. Validating the instrument against a case that MUST be non-empty exposed it: the same census reports only 85 memory operands in the whole 83,968-word (335,872-byte) loaded image and all 85 have base $zero, while a hand-written opcode decoder (op in the load/store range, rs = bits 21..25) over the identical bytes finds 3,251 $sp-based, 1,787 $v0-based, ... and (remeasured 2026-08-12 over all load/store opcodes including lwl/lwr/swl/swr and the coprocessor forms) 5 $gp-based, not the 4 first recorded. All 5 are in DATA: 0x80040B08/0B10/0B18/0B20 in a byte ramp in libgte's .rodata, and 0x8002FB34 in segment 1's .data. The conclusion (no gp-relative CODE access exists in this image) is unchanged; the count and the "all in byte-ramp tables" description were both slightly wrong. capstone's disassembly TEXT is correct (it prints '-0x27ed($gp)'); it is the structured operand list that is empty/wrong for MIPS in this build. Use raw opcode decoding for any base-register question; capstone remains fine for producing a disassembly LINE, which is all tools/re_crt0.py uses it for (it does not use capstone at all — it has its own decoder). This is the exact 'uniform output = broken instrument' tell from the workspace rules: the census's all-$zero answer was uniform, and a uniform answer that agrees with your hypothesis is the one to distrust.

## Known failure modes

(none recorded yet)

## DISTRUSTED 2026-08-12

recorded AS distrusted at creation: this entry exists to stop the next session repeating the mistake. capstone MIPS operand detail (mem.base) returns an almost-empty operand list in capstone 5.0.7; a negative result from it means nothing. Any past conclusion of the form 'no accesses to X were found' that used capstone operand detail must be re-run with a raw opcode decoder.

> Every result this instrument produced is suspect until it is re-validated.


NOTE ON THE WORD COUNT, corrected 2026-08-12: an earlier version of this entry said "84,224-word image" and that number matches nothing. The file is 337,920 bytes = a 2,048-byte PS-EXE header plus a 335,872-byte loaded image = 83,968 words; 84,480 words would be the whole FILE including the header. 84,224 was arithmetic that was never checked, and it had propagated into docs/re-frontier.md and claim C004 as well.

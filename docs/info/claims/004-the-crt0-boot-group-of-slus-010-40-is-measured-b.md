---
id: C004
kind: claim
status: holds
created: 2026-08-12
tags: boot,re-01
depends: game/core/game_config.cpp,tools/re_crt0.py
reconfirmed: 2026-08-21
verified_at: 2026-08-21 11:17:52
---

## Claim

The crt0/boot group of SLUS_010.40 is MEASURED: bssZero [0x80033678,0x800401A8) · stackTop globals 0x80049138/0x8004913C (_ramsize 0x200000 / _stacksize 0x4000) · heapBase 0x800401A8 · __heapsize 0x80030FB8 / __heapbase 0x80030FB4 · gp 0x80033674 · libcInit 0x80026864 (BIOS A0:0x39 InitHeap thunk) · gameMain 0x80042C38 · crt0 0x8001F544; derived sp=fp=0x801FFFF8

## Evidence

tools/re_crt0.py EXECUTES crt0 on the extracted SLUS_010.40 (sha1 fababcfd4325d42f350d95b3472874affeb0e48c) from the PS-EXE header's own entry PC to crt0's second call — 52,051 instructions — and reports every store (13,004 zero-stores = the clear loop's own footprint), every load, and both calls, each with its disassembly line. Nothing is keyed to an address the tool knows in advance, so the numbers cannot be a transcription of the rood-reverse reference; that decomp's symbol names (__ra_temp, _ramsize, _stacksize, __heapbase, __heapsize, InitHeap, vs_main_exec, __SN_ENTRY_POINT) agree as independent LABELS.

Cross-checks: (a) the header has b_addr=b_size=0 so no declared .bss exists and the loop is the only possible source for the range; (b) [0x80033678,0x800401A8) is all-zero in the loaded image (52,016 B) while the 120 bytes immediately below hold 44 non-zero bytes, so the low bound is a real boundary not an arbitrary address; (c) ADDED 2026-08-12 — the SN linker's own record, kept as initialised data at 0x80030FBC by the SN startup object and therefore independent of crt0's instruction stream, gives __data+__datalen = 0x8002F534+0x4140 = 0x80033674 = the measured gp and __bss+__bsslen = 0x80033680+0xCB28 = 0x800401A8 = the measured bssZeroHi. Two of the eleven values now have a second source; re_crt0.py asserts all three identities and REFUSES if the record is not present rather than skipping the cross-check silently.

THE GATE THAT MAKES THE SHIPPED VALUES CHECKED, rebuilt 2026-08-12 because they were NOT: this tool used to keep its own FIXTURE_EXPECT copy of the eleven values while game/core/game_config.cpp kept a second hand-typed copy, and nothing compared them — moving kHeapSizePtr +4 and pointing kLibcInit at an unrelated nop passed BOTH gates (workspace PROTOCOL.md, "THE SHIPPED VALUE MUST BE COMPARED TO THE MEASURED ONE"). FIXTURE_EXPECT is deleted; 're_crt0.py --check-config' parses game_config.cpp's eleven kXxx constants AND the designated initialisers that bind them to GameConfig fields and diffs them against the measurement, and '--gate-citations' regenerates the file's disassembly block from the bytes and fails on any difference. Gates run 2026-08-12: '--selftest' = 22 assertions / 0 failed, 13 of them negatives — 6 binary/corpus mutations that must REFUSE (nopped clear loop -> 'no .bss clear loop found'; unknown opcode -> 'UNMODELLED instruction'; entry that returns; broken PS-X EXE magic; entry outside text; missing file) and 7 hand-edits of the SHIPPING FILE that must be REPORTED (kHeapSizePtr +4; kLibcInit -> a real nop; '.gp = kLibcInit', a right-valued constant bound to the wrong field; a deleted constant; a retyped citation word; a deleted citation line; the whole block removed). '--gate-config' compiles game_config.cpp pristine (passes) and with 5 plausible mutations, each of which must fail a NAMED static_assert = 6/6. Sabotage-proven on the real file, not only inside the selftest: kHeapSizePtr->0x80030FBC + kLibcInit->0x8001F564 made --check-config exit 1 naming both; retyping 0x8001F548's word made --gate-citations exit 1 naming line 71; both green on restore.

KNOWN LIMITS, stated because a reader will otherwise assume otherwise:

1. gp has no independent witness IN CODE: remeasured over the 83,968-word (335,872-byte) loaded image there are ZERO gp-relative load/stores in code — 5 candidate encodings exist and all 5 are in DATA (four in a byte ramp at 0x80040B08..0x80040B20 in segment 2's libgte .rodata, one at 0x8002FB34 in segment 1's .data). An earlier version of this claim said "the whole 84,224-word text" and "4 candidate encodings, all 4 inside byte-ramp DATA tables": the word count was simply wrong (335,872 bytes / 4 = 83,968; 84,480 would be the whole FILE including its 2,048-byte header) and the encoding count was 4 where it is 5. Conclusion unchanged. Cross-check (c) above now supplies the independent witness gp previously lacked.
2. THE HEAP CRT0 DECLARES IS NOT FREE RAM, and an earlier reading of these same values got this wrong. This image concatenates THREE separately-linked segments; 0x800401A8 is the end of the FIRST one's .bss, not the end of the image. The arena crt0 declares, [0x800401AC,0x801FBFFC), overlaps the loaded image over [0x800401AC,0x80062000) = 138,836 bytes of which 45,761 are non-zero, and gameMain 0x80042C38 plus the _ramsize/_stacksize globals 0x80049138/0x8004913C all sit inside it. Measured segment profile (zero/non-zero runs in the image; rood-reverse's splat config supplies the labels and agrees to the byte): seg1 text/data [0x80010000,0x80033678) 94,803 non-zero · seg1 .sbss+.bss [0x80033678,0x800401A8) all zero, the range crt0 clears · seg2 libgte [0x80040210,0x80041D68) 5,912 non-zero · seg3 main [0x80041D68,0x8004FF88) 39,849 non-zero · seg3 main .bss [0x8004FF88,0x80062000) all zero and NEVER cleared by crt0 (the verbatim load supplies the zeros, which is why b_size=0 works). Not a contradiction, because of 3.
3. THE BIOS HEAP IS NEVER ALLOCATED FROM. Census over the whole image (2,023 jal sites against 19 BIOS A0 thunks): the only heap-related A0 thunk present at all is InitHeap 0x80026864 and its only caller is crt0 itself at 0x8001F5CC; there is no malloc/free/calloc/realloc thunk in the image, so no code in it can reach one. The game uses its own allocator instead (rood-reverse: vs_main_initHeap 0x80043F74, arena 0x8010C000 + 0xF2000, above the image's 0x80062000 end). So the overlapping BIOS arena is inert stock-crt0 boilerplate on real hardware exactly as here. Consequence for issue #3: this game cannot demonstrate psxport's BIOS-heap contract working OR broken, so #3 is a faithfulness defect that is LATENT here, not a live defect here.
4. RE-02 now executes this boot group through guest main. This confirms the measured application path;
it does not claim gameplay or overlay execution.

## What would falsify it

're_crt0.py --check-config' or '--gate-citations' going red (the shipped constants or the shipped citation block no longer agreeing with the bytes) — or a booting substrate whose crt0 diverges from these values — e.g. a [recomp-MISS] or a BIOS InitHeap logged with a different base/size than a0=0x800401AC a1=0x001BBE50 — or a different SLUS_010.40 sha1, in which case re_crt0.py --selftest FAILS its fixture-identity assertion rather than silently redefining the numbers

## Re-confirmed 2026-08-12

Re-verified 2026-08-12 after a review refuted the 'gap: NONE' framing. The eleven values are unchanged and are now checked by CODE against the bytes: re_crt0.py --check-config 0 FAILED (11/11 constants + their field bindings), --gate-citations byte-identical, --selftest 22 assertions 0 failed (13 negatives, 7 of them hand-edits of the shipping file that must be REPORTED), --gate-config 6/6. Sabotage-proven RED on the real file (kHeapSizePtr->0x80030FBC and kLibcInit->0x8001F564 -> exit 1 naming both; retyped citation word -> exit 1 naming line 71) and GREEN on restore. Two values gained an independent witness (SN link record at 0x80030FBC). Three limits added to the claim rather than glossed: the declared BIOS heap arena overlaps 138,836 bytes of the loaded image but is never allocated from (census: 2023 jal sites, 19 A0 thunks, no malloc/free/calloc/realloc thunk exists, InitHeap's only caller is crt0), the gp-encoding census was 5 not 4, and nothing has ever executed this boot group.

## Re-confirmed 2026-08-12

Re-verified 2026-08-12: tools/re_crt0.py --check-config reports 11 of 11 shipped constants matching these bytes, 0 FAILED, rc=0; and psxport tools/crt0_extract independently agrees on all 8 fields it resolves (claim C005).

## Re-confirmed 2026-08-14 11:53:32

Re-verified 2026-08-14 after adding only measured overlay slots to game_config.cpp: --check-config 11/11 and citation block byte-identical, --selftest 22 assertions/0 failed, --gate-config 6/6, seam build green. Boot constants unchanged.

## Re-confirmed 2026-08-14 12:36:31

Reverified after RE-02: re_crt0 selftest 24/24, static-assert gate 6/6, live InitHeap/main path exact.

## Re-confirmed 2026-08-14 12:57:01

Reconfirmed after psxport be03593f integration: re_crt0 shipping gate remains exact and the bounded resident run executes measured InitHeap and guest main and completes _initRand with no recompilation miss or BIOS fatal. Its later no-frame watchdog sample is in Core::mem_w32 beneath generated 0x8002411C and is not yet classified; this adds no gameplay claim.

## Re-confirmed 2026-08-21 01:04:32

2026-08-21: after repository clang-format, re_crt0 passed 24/24 and its static-assert compile gate passed 6/6; the direct port run logged the exact measured bss, sp/fp, gp, heap a0/a1, libcInit, and guest-main values.

## Re-confirmed 2026-08-21 02:47:31

2026-08-21: re_crt0 shipped-vs-measured config/citation/selftest/gate-config all passed after RE-09 GameConfig extension.

## Re-confirmed 2026-08-21 03:31:41

RE-10 final gate reran the full crt0 executable/config/citation/static-assert selftest with 0 failures; the real launcher logged the same applied crt0 plan

## Re-confirmed 2026-08-21

Post-landing re_crt0 passed 24/24 plus the six-case compile/assert gate; the pinned runtime entered measured crt0 and guest main.

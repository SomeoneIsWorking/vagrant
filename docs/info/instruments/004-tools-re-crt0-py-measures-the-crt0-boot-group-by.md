---
id: I004
kind: instrument
status: trusted
created: 2026-08-12
---

## Instrument

tools/re_crt0.py — measures the crt0 boot group by EXECUTING crt0 on the extracted SLUS_010.40; --check-config diffs the SHIPPED constants in game_config.cpp against that measurement; --gate-citations regenerates the file's disassembly block from the bytes; --gate-config proves the static_asserts fire

## Validated by

BOTH classes gated 2026-08-12 and the real output quoted in claim C004.

POSITIVE: --selftest yields the 11 fields, asserts them against the SHIPPED copy in game_config.cpp (not against a table inside the tool — see the failure mode below), asserts the citation block is byte-identical to what the bytes generate, asserts the .bss loop actually FIRED (13,004 zero stores >= 4096), asserts crt0 passes a non-zero a1, asserts the independent SN link record at 0x80030FBC agrees on gp and bssZeroHi, asserts the declared heap arena really does overlap the loaded image, and asserts no BIOS malloc/free/calloc/realloc thunk has a caller. It checks the image sha1 FIRST and REFUSES (exit 2) rather than comparing against expectations measured on a different image.

NEGATIVE, 13, all PASS. Six must exit 2 rather than report a number: the clear loop's 'sw $zero' nopped -> 'no .bss clear loop found ... longest run was 0 bytes'; an unmodelled opcode at the entry -> refuses instead of guessing register state; an entry that immediately 'jr $ra'; broken PS-X EXE magic; a header entry outside the text; a missing file -> names the path and says nothing was scanned. Seven mutate the SHIPPING FILE's text and must be REPORTED: kHeapSizePtr +4; kLibcInit -> a real nop; '.gp = kLibcInit' (a right-valued constant bound to the wrong field); a constant deleted (must refuse to compare a SUBSET rather than certify the fields it could not find); a retyped citation word; a deleted citation line; the whole citation block removed. Each of these seven calls the same functions the gate calls, not a helper beside them.

--gate-config: pristine game_config.cpp compiles AND 5 plausible mutations (gp off by one word, bss end shrunk, heapBase moved off the .bss end, gameMain outside the image, _stacksize no longer adjacent) each fail a NAMED static_assert = 6/6.

Sabotage-proven outside the selftest, on the real committed file: kHeapSizePtr -> 0x80030FBC and kLibcInit -> 0x8001F564 made --check-config exit 1 naming both ("SHIPPED 0x80030FBC (via kHeapSizePtr) != MEASURED 0x80030FB8"); retyping 0x8001F548's word to 24427836 made --gate-citations exit 1 printing the file line against the generated one; both green again after restore.

Blind spots it states rather than hides: it models only the instruction subset crt0 uses and refuses on anything else; it says nothing about the 21 .PRG overlay bases (RE-03); it cannot corroborate gp from CODE, because this executable contains no gp-relative code accesses at all (5 candidate encodings in the image, all 5 in data) — the SN link record is the only corroboration available and the tool asserts it. RE-02 now supplies separate running-boot evidence through guest main.

## Known failure modes

CAUGHT 2026-08-12, and it is the reason this entry was rewritten. The tool USED to hold its own copy of
the answer — a `FIXTURE_EXPECT` dict of the eleven values — and `--selftest` asserted the binary matched
*that*. game/core/game_config.cpp held a SECOND hand-typed copy in its `kXxx` constants, and **nothing
compared the two**, so the tool could be fully green while the value that actually shipped was anything
at all: a reviewer moved `kHeapSizePtr` +4 and pointed `kLibcInit` at an unrelated nop and BOTH
`--selftest` and `--gate-config` passed. (`--gate-config` only ever checked the constants' internal
RELATIONS, and `hi - lo == 0x46B20` holds just as well when both values are wrong.) FIXTURE_EXPECT is
deleted; the shipping file is the fixture. Workspace PROTOCOL.md, "THE SHIPPED VALUE MUST BE COMPARED TO
THE MEASURED ONE — BY CODE, NOT BY A HUMAN'S EYES".

CAUGHT 2026-08-12, same shape one level down: the 22-line disassembly block the tool's output was
supposed to justify had been RETYPED into game_config.cpp rather than pasted, and three of its raw words
did not match the executable (0x8001F548 read `24427836` for a real `24423678`; 0x8001F588/8C read
`002420c0`/`002420c2` for real `000420c0`/`000420c2`) while being presented as an audit trail. The block
is now emitted by `--emit-citations` and gated by `--gate-citations`.

CAUGHT 2026-08-12, in this tool's own new negative class: the "retyped citation word" negative first
reported nothing, because its anchor was the bare word `24423678` and `str.replace(..., 1)` mutated an
occurrence in the surrounding PROSE instead of the block. A negative whose anchor drifts silently is the
gate-blindness bug one level up; the anchor is now address+word and the miss made the selftest FAIL
rather than pass.

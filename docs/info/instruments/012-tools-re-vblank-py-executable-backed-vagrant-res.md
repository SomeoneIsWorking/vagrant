---
id: I012
kind: instrument
status: trusted
created: 2026-08-21
---

## Instrument

tools/re_vblank.py — executable-backed Vagrant resident VBlank/VSync route measurement and shipping gate

## Validated by

4/4 selftest: the real SHA-bound image produces the complete route, including the HookEntryInt setjmp buffer and restored PC; destroying the handler's counter increment yields 0 matches across 83,943 candidates; shifting the shipped handler +4 names kVBlankHandler and refuses; deleting restored PC 0x8001FAD0 from main_reentry names that seed class and refuses

## Known failure modes

(none recorded yet)

---
id: I006
kind: instrument
status: trusted
created: 2026-08-14
---

## Instrument

tools/re_overlay.py — measures and gates every non-empty .PRG load base and the three shared slots

## Validated by

2026-08-14 on the owned SLUS-01040 disc: selftest 7/7 PASS, 0 SKIP. It showed both opposite classes in the shipping paths: one owned-byte mutation was rejected by M3 SHA before address; a +4 rood vram was rejected after identity; M2 moved -4 when a word was prepended and refused after all entries were destroyed; a +4 shipped slot and +4 BATTLE seed were both named by --check-config. Real corpus: 20/20 M2+SHA-bound-M3 agreements, 24/24 shipping checks.

## Known failure modes

(none recorded yet)

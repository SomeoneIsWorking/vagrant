---
id: I014
kind: instrument
status: trusted
created: 2026-08-21
---

## Instrument

tools/re_async_cd.py — executable-backed Vagrant async libds completion and queue contract

## Validated by

2026-08-21: --selftest 3/3 on owned SLUS_010.40; destroyed callback completion, changed Pause literal, and destroyed VBlank decoded-read predicate each produce zero matches with a searched denominator

## Known failure modes

This instrument derives the guest contract from executable bytes; it does not observe controller
timing or prove that a runtime follows the contract. Use the reproducible live diagnostic in issue
#16 for the drive-side answer.

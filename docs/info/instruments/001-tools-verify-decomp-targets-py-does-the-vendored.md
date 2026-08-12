---
id: I001
kind: instrument
status: trusted
created: 2026-08-12
---

## Instrument

tools/verify_decomp_targets.py — does the vendored CC0 decomp target OUR disc's bytes, per module?

## Validated by

Validated in BOTH directions on real data 2026-08-12. Positive: 21/21 modules MATCH against the real disc. Negative: --selftest substitutes 40 zeros for the first target's expected hash and the run prints exactly one MISMATCH line and exits 1 — so the tool demonstrably CAN report the other answer. It also refuses (exit 2) when external/rood-reverse is absent or when zero splat configs are discovered, and every run prints its denominators (configs discovered, matched, mismatched, extract-failed, disc code images covered vs not) plus its blind spot (a hash match says nothing about decomp COVERAGE).

## Known failure modes

(none recorded yet)

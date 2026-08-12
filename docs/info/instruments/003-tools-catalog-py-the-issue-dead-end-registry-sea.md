---
id: I003
kind: instrument
status: trusted
created: 2026-08-12
---

## Instrument

tools/catalog.py — the issue/dead-end registry search

## Validated by

DISTRUSTED ON ARRIVAL, then fixed. As copied from spyro/tools/ it printed '(no matches)' and exited 0 for a docs/issues/ that did not exist (measured 2026-08-12, issue #2). Fixed locally: a missing corpus now exits non-zero saying it searched NOTHING, and a genuine zero-hit search prints its denominator (entries scanned, absolute path, terms) and its blind spot. Verified both ways. The copies in the other game repos still have the defect.

## Known failure modes

(none recorded yet)

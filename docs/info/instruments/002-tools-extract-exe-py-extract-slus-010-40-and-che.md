---
id: I002
kind: instrument
status: trusted
created: 2026-08-12
---

## Instrument

tools/extract_exe.py — extract SLUS_010.40 and check its identity

## Validated by

Positive path verified 2026-08-12 (extracted 337920 B, sha1 matched the decomp's stated target, PS-EXE header parsed). NOT yet exercised: the MISMATCH path (a different-region dump) and the 'CANNOT CHECK' path (decomp submodule absent) — both are coded to say what they did not verify rather than to pass quietly, but neither has been run. Treat those two branches as unproven.

## Known failure modes

(none recorded yet)

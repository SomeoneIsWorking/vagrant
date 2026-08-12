---
id: 5
title: info.py claim check reports a claim STALE forever when its verified_at DATE equals the date of the last commit touching its deps
status: open
symptom: info.py claim check keeps printing STALE for a claim that was just re-confirmed with 'claim confirm'; the named commit is dated the same day as verified_at
tags: tooling,instrument,registry
created: 2026-08-12
updated: 2026-08-12
---

## Symptom

`python3 tools/info.py claim confirm C004 --evidence '...'` prints "staleness baseline reset to
2026-08-12", and the very next `claim check` still reports:

```
STALE  C004  The crt0/boot group of SLUS_010.40 is MEASURED: ...
       verified at: verified_at: 2026-08-12   deps: declared
       game/core/game_config.cpp  [file-scope] — 1 commit(s) since:
         403d350 2026-08-12 vagrant: bootstrap the Vagrant Story port tree
```

## Cause

`verified_at` is stored as a DATE (`2026-08-12`), while the git side has full commit timestamps. The
"commits since" query cannot order a commit against a same-day verification, so any claim re-confirmed
on the same calendar day as the last commit to its `depends:` files is permanently STALE. It is not
wrong so much as UNRESOLVABLE at that granularity — but it presents as a definite STALE, which is the
worse failure: a reader who re-verifies and re-confirms sees no change and learns to ignore the field.

Hit on 2026-08-12 in `vagrant` while re-confirming C004 after re-deriving RE-01. Two of three checked
claims read STALE for this reason alone, so the signal is majority noise on a young repo where every
commit is the same day as every verification.

## Where the fix belongs

`external/psxport/tools/port/info.py` (the shared engine — `tools/info.py` here is a shim). NOT
fixable from this repo, and it must not be worked around by back-dating a `verified_at`. Two candidate
fixes, both for whoever owns the framework clone: store `verified_at` as a full timestamp, or — better,
since old entries only carry a date — report same-day-as-verification commits as a distinct third
state (`AMBIGUOUS (same day)`) rather than folding them into STALE. A tool that cannot tell must say it
cannot tell.

## Not this

Do not "fix" it by marking the claim fresh. The claim IS re-verified (`re_crt0.py --selftest` 22/0,
`--check-config` 0 failed, sabotage-proven red and green), and the registry saying otherwise is the
registry's defect, not the claim's.

---
id: 4
title: info.py claim check reports a declared depends: on an UNTRACKED file as 'names files this repo does not have'
status: open
symptom: claim check prints '*** CANNOT SEE ***  C0NN (evidence names files this repo does not have: tools/foo.py)' for a claim whose depends: file exists on disk but has never been committed
tags: tooling,instrument,registry
created: 2026-08-12
updated: 2026-08-12
---

## Symptom

`python3 tools/info.py claim check` on 2026-08-12, with C002 declaring `depends: tools/re_crt0.py`:

```
  *** CANNOT SEE .............. 1 ***  these record NO resolvable code dependency.
        C002  (evidence names files this repo does not have: tools/re_crt0.py)
```

The file exists (`ls tools/re_crt0.py`), and the `depends:` line is present in the claim's frontmatter.

## Cause

The dependency index is built from **git-tracked** files (`1498 tracked files across 3 repo(s)`), so a
brand-new tool that has not been committed yet is invisible to it. The message then attributes the miss
to the CLAIM ("names files this repo does not have"), which reads like a typo in the claim rather than
"this path is not committed yet".

## Why it matters more than it looks

This is the registry's own green-over-nothing shape, one level up. The bucket is *correctly* labelled
"CANNOT SEE ... NOT fresh — UNCHECKED", so it does not lie about coverage — but a reader who trusts the
parenthetical will go and *delete a correct `depends:` line* to silence it, and then the claim really is
invisible. It bites hardest exactly when a claim is fresh, because a new claim's instrument is usually a
new, uncommitted file.

## Status / fix

Not fixed here. Two candidate fixes, both in `info.py`: (a) fall back to `os.path.exists` and say
"exists on disk but is UNTRACKED — commit it or the staleness baseline cannot be computed"; (b) keep the
git-only index but change the wording to name untracked-ness as the cause. (a) is better — the point of
the check is to catch rot, and an untracked dependency should be reported as "no baseline yet", which is
a different state from "path does not exist".

Related, same run and same root: a claim whose own file is untracked is reported STALE against the last
commit that touched its dependency (`STALE C004 ... claim file is UNTRACKED — baseline is coarse`). That
one at least states the coarseness inline. Both resolve once the operator commits.

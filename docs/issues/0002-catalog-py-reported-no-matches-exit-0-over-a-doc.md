---
id: 2
title: catalog.py reported '(no matches)' exit 0 over a docs/issues that did not exist
status: resolved
symptom: a search of a MISSING corpus reads exactly like a search that found nothing
tags: tooling,instrument
created: 2026-08-12
updated: 2026-08-12
---

Measured in this repo's copy on 2026-08-12, immediately after copying tools/catalog.py from spyro/tools/: with docs/issues/ deleted, `catalog.py search boot` printed '(no matches)' and exited 0.

This is the failure mode the workspace rules name explicitly: a diagnostic that can print nothing is lying, and 'refuse, don't return empty, when the corpus is missing'.

FIXED HERE: _load_all() takes refuse_if_missing and cmd_search passes it, so a missing directory now exits non-zero saying it searched NOTHING; and the negative case prints its denominator ('searched N entries in <abs path> for <terms>') plus its blind spot instead of a bare '(no matches)'. Verified both ways: missing dir -> exit 1 with the refusal; present-but-empty dir -> exit 0 with 'searched 0 entries'.

STILL BROKEN ELSEWHERE: spyro/tools/catalog.py (the copy this was taken from) and any other copy in the workspace. This is the divergence cost the tooling hoist decision exists to remove — the engine belongs in psxport/tools/port/ alongside re_frontier.py.

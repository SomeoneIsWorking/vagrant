---
id: 9
title: Vagrant reaches a no-frame watchdog after BIOS rand
status: resolved
symptom: bounded resident run reaches main and completes srand/rand, then watchdog samples Core::mem_w32 under generated 0x8002411C with no first frame
tags: boot,stall,sync,re-08
created: 2026-08-14
updated: 2026-08-14
---

## Root cause

The watchdog sampled a store inside the polling path, not the condition being awaited. Generated
SLUS_010.40 code gives the call chain `0x80044A60 -> 0x80025BE4 -> 0x8002411C -> 0x80020F28`.
The SHA-matching CC0 reference independently names these `_diskReset`, `DsControlB`, `DsSync`, and
`CD_sync`; `_diskReset` is waiting for asynchronous `DslPause` completion before Setmode.

## What was tried / dead ends

The original `Core::mem_w32` stack sample was treated only as unclassified evidence. It does not
justify a memory-store fix or a low-level hardware-sync handler. A framework-dev fntrace attempt also
produced no trace because `fntrace_init` is not wired into the current boot path; the generated body
and the byte-matching reference supplied the classification instead.

## Resolution

`tools/re_cd.py` measures and gates the `DsControlB` owner. The override owns the blocking-control
command class, retains the generated body, reuses psxport's native controller semantics, and refuses
unsupported query/read commands. `vagrant_cd_contract_test` compiles that same classifier, accepts all
9 supported IDs, and refuses query, read, and unknown examples. `scratch/logs/re04-owner-run.log`
records Pause and Setmode and advances beyond `_diskReset` to a later watchdog under `0x8001355C`.

Async commands, callbacks, query results, reads, and XA remain explicitly open under RE-04; this
resolution does not claim those contracts or gameplay.

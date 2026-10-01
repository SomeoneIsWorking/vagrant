---
id: 30
title: DsInit reaches independent CD command and sync VSync queries
status: resolved
symptom: binding nested CD-sync moved the fatal from 0x80020F64 to 0x80021634, and binding only CD_cw restored 0x80020F64
tags: cd,vsync,platform-hle,re-20
created: 2026-08-24
updated: 2026-08-24
---

`CD_cw 0x80021470` has TWO guest-owned waits: it calls `CD_sync 0x80020F28`, whose body queries
VSync(-1), and later calls VSync(-1) directly at `0x8002162C`. `CD_init 0x80021B14` also calls CD_sync
directly, so both platform leaves are independently live and both must be bound.

**Dead end:** binding only one of the two leaves, in either combination — each alone moves the fatal
rather than removing it. The owner declares three one-instruction windows: mandatory-fatal VSync,
native synchronous CD_cw, native synchronous CD_sync.

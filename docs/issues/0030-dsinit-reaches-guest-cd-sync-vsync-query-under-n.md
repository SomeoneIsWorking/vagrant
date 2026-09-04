---
id: 30
title: DsInit reaches independent CD command and sync VSync queries under native frame ownership
status: resolved
symptom: Bounded CHD launches abort at Sony VSync 0x8001F6C4 from CD_cw 0x80021470, first through nested CD_sync and then from CD_cw's own wait.
tags: S003,frame-loop,vsync,cd,dsinit,native-ownership,re-20
created: 2026-08-27
updated: 2026-08-27
---

## Root cause

`CD_cw 0x80021470` has two guest-owned waits: it calls `CD_sync 0x80020F28`, whose body queries
VSync(-1), and later calls VSync(-1) directly at `0x8002162C`. Binding only nested CD-sync moved the
fatal from return address `0x80020F64` to `0x80021634`. Binding only outer CD_cw correctly served
CD-init commands `0x01`, `0x0A`, and `0x0C`, but `CD_init 0x80021B14` then called CD_sync directly and
restored the `0x80020F64` fatal. Both exact platform leaves are independently live and required.

## Current work

`tools/re_cd.py` derives both exact leaves. The generic framework seam now supplies four exact-window
slots, so Vagrant declares three one-instruction windows without admitting the intervening resident
code: mandatory-fatal VSync, native synchronous CD_cw, and native synchronous CD_sync. The combined
Clang runtime/product build, full 7/7 CTest suite, clang-tidy, and executable-backed 3/3 controls pass.

## Remaining gap

The combined binding needs a newly authorized serialized real-disc run. That run must pass DsInit
and identify the next residual VSync, if any.

### Resolution (2026-08-27)
Combined real-disc PID 2657967 installed all three exact leaves, served CD-init commands 0x01/0x0A/0x0C, and passed both formerly-failing CD_cw/CD_sync paths. The next mandatory fatal moved to libgpu timeout arm 0x8002AB84 from ClearImage during TITLE reinitialisation, proving the CD ownership root cause is resolved.

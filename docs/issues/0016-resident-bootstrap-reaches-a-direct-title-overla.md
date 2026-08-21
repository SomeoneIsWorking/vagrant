---
id: 16
title: Resident bootstrap reaches a direct TITLE overlay call without an emitted overlay
status: open
symptom: after four WAVE reads and the TITLE image read complete, default runtime fails fast at recomp-MISS 0x80071334 from resident jal at 0x80042BD8
tags: boot,overlay,re-03,re-04,routing
created: 2026-08-21
updated: 2026-08-21
---

## Evidence

The pinned deterministic CDC trace at `scratch/logs/re18-3418a79b-direct-runtime.log`
records five ReadN operations. Four are WAVE reads through `vs_main_diskLoadFile 0x8004493C`; the
fifth transfers 271 sectors, LBA 256000 through 256270, for TITLE.PRG. Its final callback is the
sixth observed `DsEndReadySystem` call because call one belongs to initialization, not a read. The
real zero-argument route in `scratch/logs/re18-3418a79b-default-launcher.log` then fails fast
at `0x80071334`, with caller return address `0x80042BE0`.

Reproduce the detailed transition against the framework recorded in `psxport.pin` without a private
harness:

```sh
PSXPORT_DEBUG=cdc,cdcpace \
PSXPORT_FNTRACE=80043FB4,800262E8,80023B34,800235A4,8004493C,80024BDC,80025630,8002484C \
PSXPORT_FNTRACE_REGS=180 PSXPORT_WWATCH=80032680,800326C8 ./run.sh
```

The ordinary `./run.sh` route independently prints the same final target; the extra diagnostics only
make the preceding guest-owned CD transition auditable.

Executable disassembly of resident function `0x80042BAC` proves a direct `jal 0x80071334` at
`0x80042BD8`. The target is inside the verified TITLE overlay slot based at `0x80068800` (offset
`0x8B34`), not inside the resident PS-EXE. Current resident emission reports zero overlays and
`generated/overlay_table.c` has no registered overlay module.

## Root cause / next work

The CD/file-load prerequisite now succeeds, exposing the first real overlay dispatch. The port has
measured overlay bases but has not extracted, emitted, or registered TITLE.PRG for runtime routing.
Do not add `0x80071334` as a resident/main seed: that would decode unrelated or absent PS-EXE bytes
at an overlay virtual address. Extract the SHA-verified TITLE image, emit it through the framework
overlay path at measured base `0x80068800`, register the generated overlay module, and gate the
reached call plus a forced missing-overlay negative.

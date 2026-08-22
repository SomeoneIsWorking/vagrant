---
id: 16
title: Resident bootstrap reaches a direct TITLE overlay call without an emitted overlay
status: resolved
symptom: after four WAVE reads and the TITLE image read complete, default runtime fails fast at recomp-MISS 0x80071334 from resident jal at 0x80042BD8
tags: boot,overlay,re-03,re-04,routing
created: 2026-08-21
updated: 2026-08-22
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

That historical ordinary `./run.sh` route independently printed the same target; the extra
diagnostics made the preceding guest-owned CD transition auditable.

Executable disassembly of resident function `0x80042BAC` proves a direct `jal 0x80071334` at
`0x80042BD8`. The target is inside the verified TITLE overlay slot based at `0x80068800` (offset
`0x8B34`), not inside the resident PS-EXE. The pre-fix generated table contained zero overlays.

## Root cause

The CD/file-load prerequisite exposed a real overlay dispatch, while the emitter consumed only the
resident PS-EXE. Adding `0x80071334` as a resident seed would decode unrelated PS-EXE bytes at an
overlay address. The correct owner is the independently extracted TITLE image at its measured base.

### Resolution (2026-08-22)
`tools/extract_overlays.py` SHA-verifies TITLE.PRG, and `tools/ensure_recomp.py` emits it as a
fixed-base module at `0x80068800`. The live headless run routes resident `jal 0x80042BD8` into
`ov_title_func_80071334`/`vs_title_exec`. The generated-output gate requires that descriptor and
entry; its unit negative removes the entry and is refused. Issue #17 owns the later visual boundary.

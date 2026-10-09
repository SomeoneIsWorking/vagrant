---
id: 0043
title: After the memcard wait, _copyTitleBgData aborted inside its own run-length expand
status: resolved
symptom: with the TITLE save-file check reached, the next leaf exited budget-exhausted at 0x8006FCEC and the process aborted naming "guest call0"
tags: resident,title,render,re-23
created: 2026-10-04
updated: 2026-10-04
---

Owning `_initMemcard` released `_saveFileExists`, and the very next leaf it calls did not fit a host
turn. `_copyTitleBgData` (`0x8006FC6C`) expands TITLE's compressed 544x576 background: a bounded
walk of 55,732 words of `_titleScreenBg` at `0x80076AD4`, zeroing each run and copying each literal,
then two `LoadImage`s. Measured 2026-10-04 on the authenticated TITLE.PRG it consumed **4 host turns
and 1,823,518 guest cycles**; under the single-turn `callReturning0` it aborted at `0x8006FCEC`, in the
middle of the literal-copy loop.

It is not a wait. The loop touches nothing but RAM: no GP0/GP1 register, no `VSync`, no CD access, no
exception. `ExecutionBudget::currentTurn` is one display field (33,868,800/60 = 564,480 cycles), so a
finite compute leaf that measures longer than that is the framework's own "ordinary bounded exit",
and the executor contract's answer is to resume it deliberately.

**Dead ends:** raising the budget for this call only (it is the turn count, not the cycle count, that
must be named), and replacing the guest body with a native expand (the run-length format and the
`LoadImage` layout are guest-owned and unmeasured here).

The fix reaches `psx::cpu::callGuestToReturnResuming` through the one module allowed to spell a
dispatch form: `vagrant::dynarec::callGuestResumingToReturn(core, entry, turnCap)`, with the return
address read from `r[31]` before the call because the guest body overwrites it as it calls deeper.
`ResidentCallServices::callResuming` is the owner-facing seam and
`title_splash::kCopyTitleBgDataTurns` the stated cap (the measurement plus one field), so
`tests/test_vagrant_runtime.cpp` fails if this leaf silently returns to the single-turn form.
## Update 2026-10-09

`callResuming` and `kCopyTitleBgDataTurns` no longer exist; TITLE's guest code, including this leaf, now runs as a suspended guest call that spans fields (`TitleExecPhase`).

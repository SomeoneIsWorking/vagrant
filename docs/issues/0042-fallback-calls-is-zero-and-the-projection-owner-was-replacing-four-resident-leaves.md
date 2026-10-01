---
id: 42
title: `fallback.calls` is 0 in a real run, and the projection owner was REPLACING four resident leaves
status: open
symptom: issue 0041's fatal #4 is fixed at root cause, field 0 survives it, and the number S015 was `missing` for its whole life is now measured: `fallback.calls == 0` with every per-reason counter at zero beside nonzero executor counters. The boot is still incomplete: it dies in field 1 on a budget exit inside libcd's `CD_sync`.
tags: s015,dynarec,fallback,projection,superCall,display-area,cd-sync,product-slot
created: 2026-09-28
updated: 2026-09-28
---

## The number, and what it is not

`fallback.calls = 0`, read live over the loopback control surface in a session that survived field 0:

    guest: calls=44 translated_blocks=617 executed_blocks=10722 executed_instructions=58663
          host_dispatches=138 cache_hits=10105 cache_misses=620 invalidations=9526 faults=0
    fallback: calls=0 instructions=0 refused_calls=0 compilation_failed=0 self_modifying_code=0
              unsupported_block=0 load_delay_hazard=0 unsafe_instruction_fetch=0 (…all zero)

`executor_calls` is 44, `translated_blocks` 617, `executed_blocks` 10,722 — a zero printed beside
`executor_calls=0` would be "the instrument never ran". This is not that: the instrument ran, scanned,
and found no fallback. **What it does not establish:** 58,663 executed instructions is one and a half
host fields of boot. It is not a title phase, not gameplay, not playability.

## 1. WHAT 0x8005DFD6 IS, FROM BYTES

**It is BATTLE's publication rectangle and nothing else, and the resident executable never writes
it.** A reference census over all four provisioned modules finds 7 references, all in BATTLE.PRG; the
resident, TITLE.PRG and INITBTL.PRG contain NONE. The only stores anywhere are BATTLE's
`func_800760CC` at `0x800761E0/E8/F0/0x80076200` (`sh $zero,-0x202C` → x; `sh $zero,-0x2028` → y;
`sh $s2,-0x202A` → w; `sh $s3,-0x2026` → h).

So a zero rectangle means "no overlay publication has run yet", which is the ordinary state of the
whole boot and not a guest defect. At the moment the boot publishes, BATTLE.PRG is not loaded and
`0x8005DFD4..DA` is untouched BSS.

## 2. WHICH WORD IS THE RESIDENT PUBLICATION'S OWN HORIZONTAL EXTENT

**`env + 4`, where `env` is the caller's `$a0` — a per-call address, not a constant.** Both env leaves
store the stated width there:

    0x8002B434  SetDefDispEnv  lw $v1,16($sp) ; sh $a3,4($v0)   ; +4 w <- the stated width
    0x8002B374  SetDefDrawEnv  sh $s0,4($s1)                   ; +4 w <- the stated width

For this title's boot, `env` is `0x8005E188` (`vs_main_dispEnv`, from the decompilation's own
`symbol_addrs.txt:790` and from the body's own `lui 0x8006` + `addiu -7800`). Its sole caller is
`_initScreen` at `0x80042054`, which states 320x240 and calls `SetDefDispEnv` at `0x8004207C`. The
boot's own width word is therefore `0x8005E18C`, and a run reads it:

    8005E18C: 00E00140   <- 0x0140 = 320
    8005E18A: 01400000   <- the height the leaf stored
    8005DFD6: 00000000   <- BATTLE's rectangle, still zero, and no longer consulted

## 3. THE FIX, and why this is the root cause rather than tolerating the symptom

Tolerating a zero rectangle would be a special case for the failing input and would disable the check
for the whole boot — which is where the boot's own geometry is published. The real defect was two
halves of ONE thing:

**(a) The owner was REPLACING four resident SDK leaves, not observing them.** psxport consults a
title's image-scoped override first and enters the original body only when no override is active, so
the four projection overrides ran INSTEAD of `SetGeomOffset`, `SetGeomScreen`, `SetDefDrawEnv` and
`SetDefDispEnv` — and the guest's GTE geometry, display environment and draw environment were written
by nothing in the product, while the header claimed the opposite. Two shapes now: the two GTE leaves
PERFORM their measured retail effect through psxport's public `libgte_set_geom_offset` /
`libgte_set_geom_screen` and reproduce the leaf's own argument side effect from its `sll` words, then
observe; the two env leaves RUN THE ORIGINAL GUEST BODY through the framework's own
`psx::cpu::callOriginalToReturn` (`runtime/cpu/native_dispatch.h:96`), then read the word the leaf just
filled. Their retail effect is pure guest memory, so the guest's own body is its correct
implementation. No title-local copy of the resume-and-refuse rule was added — the framework owns it.

**(b) The cross-check named BATTLE's rectangle.** It now names the leaf's own `env + 4` and `env + 6`,
with the guest-RAM bound applied to the DERIVED address.

**The tests are the point.** The old fixture pre-seeded the coprocessor and the guest rectangle before
invoking the override, so it passed against an owner that did nothing. The new fixture seeds NOTHING
and asserts the destinations moved (`gte_read_ctrl(24) == 160<<16`, `(25) == 112<<16`, `(26) == 256`,
the leaf's own `$a0`/`$a1` side effects), replays the boot's 320x224 publication with `0x8005DFD6`
deliberately left at zero, and requires the owner to survive it — the exact input that killed field 0.

## 4. A FRAME, LOOKED AT, AND WHICH PHASE IT IS

One frame presented and captured, and opened: 320x224, a **uniform, featureless black rectangle** —
0 of 71,680 pixels non-black, 1 distinct colour. The guest's own log explains it: the run reaches
`[gpu] display standard -> NTSC` in the same field, so the display area was published and the mode set,
and nothing had been drawn into it. **WHICH PHASE: the boot's first host field, before the title's
first splash** — not a splash, not the intro movie, not the Start-skip menu, not gameplay. Every field
was sampled (the capture driver shoots every field and prints its parity) and two independent runs at
the same field produced byte-identical captures, so this is not a sampling artefact.

## 5. WHAT S015 IS NOW, PRECISELY

| clause | state | evidence |
|---|---|---|
| the product executes the AUTHENTICATED guest image through Lightrec | established | authenticated 337,920-byte resident, then 58,663 executed instructions over 617 translated blocks |
| no guest block is interpreted | established | `fallback.calls=0` with all per-reason counters printed and zero, beside nonzero executor counters |
| the title's boot is owned rather than merely executed | established | the boot's own display-area publication is measured through the guest's leaf, 320x224 at `0x8005E18C` |
| the title reaches a TITLE phase | **missing** | the run ends in field 1, inside libcd's `CD_sync` |
| the title is playable | **missing** | — |

## 6. THE PERSISTING FATAL, AND WHAT IT IS NOT

    [executor:error] resident call2 ... budget-exhausted at 0x80020F28 after 564486 cycles

`0x80020F28` is `CD_sync`, a libcd field-count wait: it reads the guest's VSync counter
(`0x80032114`), targets `counter + 960`, and retries until the target passes or the counter exceeds a
bound of `0x3C0000` (3,932,160). **That bound is a BOUND, not a modulus**: the compare is a `slt`
against a 32-bit constant and there is no remainder anywhere on the path. The state word trio
`0x80039C68/6C/70` is **not private to `CD_sync`** — a reference census finds 28 references, of which
21 are in three further resident routines that each write and read all three; zero in BATTLE.PRG,
TITLE.PRG or INITBTL.PRG. Whatever owns the CD wait must agree with those four routines.

The framework's in-segment guest clock is **falsified as the cause**: the guest counter at `0x80032114`
advances one increment per host field and zero times across the 564,486 guest cycles of field 1, and
the framework commit that makes the clock advance inside a translated segment did not change the exit.

**What it is instead: a title-side declaration gap with a named address.** The loop's only other exit
is the CD completion, and the byte that carries it (`0x800324D8`, read by `CD_sync` at `0x80021000`)
has exactly one writer in the whole resident, in the unnamed libcd command-state function between
`CdDataSync` (`0x800209A0`) and `CD_sync`. The boot never reaches it, so the byte is never written and
the only remaining exit is a 960-field timeout one turn cannot contain. Independently,
`VagrantRuntime` does not override `GameRuntime::guestCdStreamCallbackLayout()`, and psxport's
`cdReadyCallbackOwnedByGuestInterrupt()` requires a declared layout with a non-zero
`readyCallbackPointer` owned by `GuestInterrupt`; with none declared the framework's CD-ready delivery
to the guest's interrupt path is not part of this title's contract and `deliverCdReadyCompletionOnInterrupt`
returns `NotOwned`. **That declaration is the next step.** Widening `CD_sync`'s budget, or writing
`0x800324D8`, would be forging guest state.

## 7. FRAMEWORK GAP THAT EXPOSES

`psx::cpu::callOriginalToReturn` delegates to `requireGuestReturn`, which treats `BudgetExhausted` as
fatal, while the framework's own comment above `resumeOriginal` calls budget exhaustion "an ordinary
bounded exit" the host handles and then resumes deliberately. `vs_main_initHeap` re-enters a body that
legitimately needs more than one host turn and carries its own bounded resume for it. The framework
needs `psx::cpu::callOriginalToReturnResuming(core, key, budget, owner)` — the same rule, resuming
through `resumeOriginal` on `BudgetExhausted` until `GuestReturn`, capturing the return address before
the first dispatch — until then this repository carries the loop, which is framework policy duplicated
with a named owner.

## Falsifiers

- If `0x8005E18C` does not read 320 in a run whose log shows the boot's publication, the `env + 4`
  reading is wrong, though the bytes at `0x8002B444` and `0x8002B3B4` would then have to be something
  else.
- If a resident `SetDefDispEnv` call site other than `0x8004207C` exists, the boot is not the only
  caller and the "one publication" reading changes.
- If `fallback.calls` is non-zero on a longer run, "dynarec-only" is false for this title and the
  per-reason breakdown says which instruction class is unsupported.
- If a declared `guestCdStreamCallbackLayout` does NOT end the `CD_sync` wait, the completion byte has a
  route this issue has not found.
- If `lui 0x8004` with displacement `-0x6398` does not name `0x80039C68`, the address correction is
  wrong the other way; one `rw` of `0x80039C68` and `0x80049C68` over the control surface settles it.
- If any instruction on the path `0x80020FCC..0x8002105C` performs a remainder against 60, then the
  bound is a modulus after all.

## NOT established by this issue

Any TITLE phase. Any gameplay. Playability, widescreen, interpolation, BATTLE, INITBTL: all still
`missing`. A completed run, so no run-end census. The `CD_sync` route to its completion. Whether
`fallback.calls` stays 0 past the boot.
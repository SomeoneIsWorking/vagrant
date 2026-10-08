---
id: 42
title: `fallback.calls` is 0 in a real run, the projection owner was REPLACING four resident leaves, and the `CD_sync` wait was two unbound leaves
status: open
symptom: issue 0041's fatal #4 is fixed at root cause, field 0 survives it, and the number S015 was `missing` for its whole life is now measured: `fallback.calls == 0` with every per-reason counter at zero beside nonzero executor counters. The boot is still incomplete: it dies in field 1 on a budget exit inside libcd's `CD_sync`.
tags: s015,dynarec,fallback,projection,superCall,display-area,cd-sync,product-slot
created: 2026-09-28
updated: 2026-10-04
---

**SUPERSEDED IN PART (2026-10-04).** Sections 1-7 record the 2026-09-28 run and are kept as the
measurement that produced them. Section 6's conclusion — that the `CD_sync` wait needed a declared
`guestCdStreamCallbackLayout` — is **wrong**, and section 8 is the boot as it now runs: the wait was
reached through an UNBOUND `DsControlB`, the run reaches and presents a TITLE phase, and a second
unbound leaf (the libapi DMA callback table) stood directly behind the first.

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

## 8. RESOLVED 2026-10-04: the `CD_sync` wait was NOT a missing CD-ready layout, and the boot now reaches a TITLE phase

**The hypothesis in section 6 was falsified, and the run names what was actually wrong.** The title
does not need `GameRuntime::guestCdStreamCallbackLayout()` at all for this wait.
`psx::cd::deliverCdReadyCompletionOnInterrupt` serves the controller's DATA-READY completion (response
type 1) and deliberately retires no command response (`cd_ready_delivery.cpp`: "Nothing is retired
from the response FIFO here... the guest consumes its own command responses"). A blocking `DsControlB`
waits on the command completion, so a declared ready-callback layout cannot end it. Nothing was
declared, and nothing needed to be.

**Where the boot actually stopped, and why — measured in a live run, not read off a census.** `gdb`
on `psx::cpu::requireGuestReturn`'s abort named the exact title call and the exact leaf:

    #3  vagrant::dynarec::callReturning2 (core=..., address=2147638244, a0=9, a1=0)
        at game/execution/dynarec_dispatch.cpp:83
    #4  vagrant::ResidentPhase::beginMenuSound (this=0xb2e2c0, core=...)
        at game/boot/resident_phase.cpp:175
    #6  psx::Machine::stepFrame (this=0x7fffffffccd8, frame=2)

`address=0x80025BE4` is libds `DsControlB`, and `resident_phase.cpp:175` is
`call2(cd::kDsControlB, 9u, 0u)` — the title's own replay of `_diskReset`'s first
`DsControlB(CdlStop, NULL, NULL)`. The reported `0x80020F28` is where the turn's LAST translated block
started, not where the wait began; fields 1 and 2 log nothing, so the last log line before the abort
belongs to field 0.

**The chain, every link read out of the SHA-bound image (2026-10-04, `decomp_pipeline.py`):**

| address | symbol | what it does |
|---|---|---|
| `0x80044A60` | `vs_main__diskReset` | `do { DsControlB(9,0,0); } while (!ok)`, `DsFlush()`, `do { DsControlB(0x0E,&DAT_80055D2C,0); }`, `VSync(3)` |
| `0x80025BE4` | `DsControlB(id,param,result)` | `DS_control(...)` then `do { c = DS_getready(h,result); } while (c == 0);` |
| `0x8002411C` | `DS_getready(handle,result)` | calls `DS_sync(0)` on every iteration |
| `0x8002496C` | `DS_sync(result)` | `CD_sync(1, result)` — the NON-BLOCKING variant |
| `0x80020F28` | `CD_sync(noblock,result)` | polls `VSync(-1)` for `DAT_800324D8 == 2 \|\| == 5`; `noblock` returns 0 on the first pass |
| `0x800324D8` | libcd command completion code | written only by `FUN_800209C4`, the CD-interrupt state machine |

**The root cause is one unbound leaf, not a missing declaration.** `game/cd/ds_control.cpp` has
shipped `vagrant::cd::handleDsControlB` since the static-recomp removal (commit `b5be9a5`), with a
documented contract ("the native body for the blocking `DsControlB` boundary") and a unit test for its
command classifier — and **nothing ever installed it**. `installResidentNativeOwners` bound exactly one
leaf (`vs_main_initHeap`) plus the four projection leaves, so `DsControlB` ran as GUEST code into
libds's own unbounded `do/while`, waiting on a completion byte no host code writes. The fix is in
`game/execution/native_owners.cpp:98`: bind `cd::kDsControlB` to that owner at the resident
publication boundary, which is the one place in this title that may bind a resident leaf.

**A SECOND unbound leaf, immediately behind it.** With that fixed the boot reached field 5 and died at
`budget-exhausted` 0x80013570 — the same shape, the same class of defect:

| address | symbol | what it does |
|---|---|---|
| `0x80011DAC` | `vs_main__initSound` | `StartSound` — parks in the waiter below |
| `0x800134A0` | `SpuSetTransferCallback(fn)` | `DAT_800377F0 = 1`; `DAT_80030898 = 0x8001347C` |
| `0x8001355C` | `_waitTransferAvailable` | `do {} while (DAT_800377f0 == 1);` |
| `0x8001347C` | `_spuWriteComplete` | `DAT_800377f0 = 0` — the ONLY clear of the flag |
| `0x80020280` | libapi `DMACallback(ch,fn)` | `slot = &DAT_80032128 + ch`; arms bit `ch+16` and bit 23 |
| `0x8001DE94` | the channel-4 slot's body | `(*DAT_80030898)()` |

`PlatformHlePlan::dmaCallbackTable` was never declared, so `Hle::irqPoll` fell back to the per-Game
native `DmaCallbackRegistry`, which holds no entry for a title that registered none: the DMA4 transfer
completed and the guest's flag never cleared. `resident::kDmaCallbackTable = 0x80032128` (RE-09) was
already measured and shipped and had **no reader at all**. Declared in
`game/runtime/vagrant_runtime.cpp:60`.

**What the product does now.** Headless, one process, `faults=0` and `fallback.calls=0` with every
per-reason counter zero beside 1,404 translated blocks and 1.98M executed instructions:

    [vagrant-boot]   authenticated resident image: SLUS_010.40 (337920 bytes), image 1/1
    [vagrant-owners] resident native owners registered against image 1/1: 2 of 2 title leaf/leaves
                     + 4 measured projection publication leaves
    [disc]           opened Vagrant Story (USA).chd (39894 hunks, 8 frames/hunk)
    [vagrant-resident] finite TITLE reinitialisation loaded TITLE.PRG; entry follows one host field
    [vagrant-resident] TITLE entry prefix reached the native-owned publisher/developer splash

800 consecutive presented fields were captured over the control channel and inspected. Frames 0..332
hold the publisher splash (3,090 non-black of 71,680 pixels, 16 colours); 333..347 are its fade out;
350..364 the developer fade in; 364..690 hold the SQUARESOFT logo (1,052 non-black); 691..711 fade out.
Converted to PNG and opened: the first is **"Published by Square Electronic Arts L.L.C."** and the
second the **SQUARESOFT** logo, in the game's own font on black. That is a TITLE phase with real
pixels from the guest's own VRAM, which is what S015 and S004 needed.

**Where it stops next, characterised but not owned.** After the splash the run stays in
`ResidentPhaseState::TitleSaveCheckRunning` forever: at field 1640 gdb reads
`TitleSaveCheckState::InitFieldWait` after 901 calls, i.e. `finishInitField`'s
`title_memcard::kOwner(0u)` (TITLE.PRG `0x8006E988`, `_initMemcard`) returns 0 on every field and
never reaches `beginPort`. That is the card-insertion event of issue 34's family, and it is the next
thing to own — not part of this fix.

## Falsifiers

- If `0x8005E18C` does not read 320 in a run whose log shows the boot's publication, the `env + 4`
  reading is wrong, though the bytes at `0x8002B444` and `0x8002B3B4` would then have to be something
  else.
- If a resident `SetDefDispEnv` call site other than `0x8004207C` exists, the boot is not the only
  caller and the "one publication" reading changes.
- If `fallback.calls` is non-zero on a longer run, "dynarec-only" is false for this title and the
  per-reason breakdown says which instruction class is unsupported.
- ~~If a declared `guestCdStreamCallbackLayout` does NOT end the `CD_sync` wait, the completion byte has
  a route this issue has not found.~~ **FALSIFIED 2026-10-04 (section 8):** the completion byte had a
  route — the wait was never entered, because the caller of `CD_sync` was an unbound `DsControlB`. No
  layout was declared and none was needed.
- If `DMACallback`'s table base is not `0x80032128`, `_waitTransferAvailable` would still be waiting
  for a completion delivered somewhere else. `refs 0x80032128` names `FUN_800200B4`'s
  `addiu a0,a0,0x2128` and `FUN_80020100`'s `lw v0,0(s2)`, and `FUN_80020280`'s own body computes
  `&DAT_80032128 + ch`.
- If `lui 0x8004` with displacement `-0x6398` does not name `0x80039C68`, the address correction is
  wrong the other way; one `rw` of `0x80039C68` and `0x80049C68` over the control surface settles it.
- If any instruction on the path `0x80020FCC..0x8002105C` performs a remainder against 60, then the
  bound is a modulus after all.

## NOT established by this issue

Any gameplay. Playability, widescreen, interpolation, BATTLE, INITBTL: all still `missing`. A completed
run, so no run-end census — `machine.run(0u)` has no field cap and this session never stopped the
product cleanly. Whether `fallback.calls` stays 0 past the splash: measured 0 over 1,849 presented
fields, which is the first fifteen seconds of a boot and not a game. The intro movie and the Start-skip
menu, and the `_initMemcard` poll the run now parks in.
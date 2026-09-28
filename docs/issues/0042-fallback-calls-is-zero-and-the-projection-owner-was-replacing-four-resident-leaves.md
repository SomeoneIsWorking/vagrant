---
id: 42
title: `fallback.calls` is 0 in a real run — the projection owner was REPLACING four resident leaves and cross-checking BATTLE's rectangle, and both halves are fixed at root cause
status: open
symptom: issue 0041's fatal #4 is fixed at root cause, field 0 survives it, and the number S015 was
  `missing` for its whole life is now measured: `fallback.calls == 0` with every per-reason counter
  at zero beside nonzero `executor_calls`, `translated_blocks`, `executed_blocks` and
  `executed_instructions`. The boot is still incomplete: it dies in field 1 on a budget exit inside
  libcd's `CD_sync`, and that is now narrowed to a TITLE-side declaration gap rather than the
  framework's in-segment clock, which was measured and refuted as the cause.
tags: s015,dynarec,fallback,projection,superCall,display-area,cd-sync,product-slot
created: 2026-09-28
updated: 2026-09-28
---

## THE NUMBER, and what it is not

`fallback.calls = 0`, read live over the loopback control surface in a session that survived field 0.
The full reading, verbatim, twice from independent runs:

    guest: calls=40 translated_blocks=430 executed_blocks=8400 executed_instructions=44855
          host_dispatches=135 cache_hits=7970 cache_misses=433 invalidations=9353 faults=0
    fallback: calls=0 instructions=0 refused_calls=0 compilation_failed=0 self_modifying_code=0
              unsupported_block=0 load_delay_hazard=0 unsafe_instruction_fetch=0
              refused_compilation_failed=0 refused_self_modifying_code=0 refused_unsupported_block=0
              refused_load_delay_hazard=0 refused_unsafe_instruction_fetch=0

    guest: calls=44 translated_blocks=617 executed_blocks=10722 executed_instructions=58663
          host_dispatches=138 cache_hits=10105 cache_misses=620 invalidations=9526 faults=0
    fallback: calls=0 instructions=0 refused_calls=0 compilation_failed=0 self_modifying_code=0
              unsupported_block=0 load_delay_hazard=0 unsafe_instruction_fetch=0
              refused_compilation_failed=0 refused_self_modifying_code=0 refused_unsupported_block=0
              refused_load_delay_hazard=0 refused_unsafe_instruction_fetch=0

**THIS IS THE INSTRUMENT HAVING RUN, and that is the whole distinction issue 0041 was blocked on.**
`executor_calls` is 40 and then 44; `translated_blocks` is 430 and then 617; `executed_blocks` is
8,400 and then 10,722. A zero printed beside `executor_calls=0` — which is what the run-end line
carried before — is "the instrument never ran". This is not that: the instrument ran, scanned, and
found no fallback. Every per-reason counter is present and zero, so this is a SCANNED ZERO rather
than an absent tail.

**What it does NOT establish.** 58,663 executed instructions is one and a half host fields of boot.
It is not gameplay, it is not a title phase, and it is not a title that has run. S015's wording is
"executes authenticated guest images through psxport's dynarec-only runtime"; the honest reading of
that today is "the title's boot executes authenticated guest images through Lightrec and no block
was interpreted", which is one clause of the item and not the whole of it. See
`docs/project-state.md` for how S015's row is worded now.

**And the link check still cannot answer it in either direction**, but it no longer claims to.
`tools/verify.py::verify_product_link` now prints two lines, and the second is the important one:

    [verify] product link: 0 of 3 retired-interpreter entry points present; 0 of 3 generated-corpus symbols present
    [verify] product link: 2 of 2 Lightrec per-block interpreter entry points ARE linked
           (lightrec_run_interpreter, lightrec_emit_jump_to_interpreter). That is PERMITTED — the
           architecture keeps them for bounded, accounted fallback. It is NOT a measurement of
           whether this title used one: that number is `fallback.calls` at run time.

So issue 0041's "this check is a FALSE NEGATIVE" finding has been acted on: the gate asks about a
subject in the execution path and names the number that answers the question it is being cited for.
That supersedes the reading in `docs/info/claims/031`, which recorded the old behaviour.

## 1. WHAT 0x8005DFD6 IS, FROM BYTES

**It is BATTLE's publication rectangle and nothing else, and the resident executable never writes
it.** `tools/re_display_area.py` decides that from a reference census over all four provisioned
modules, and prints every reference it found with the count per module:

      every reference found, per module, as the SUM of the `lui` page and the displacement:
        BATTLE.PRG  7 reference(s): 0x800761E0:sh, 0x800761E8:sh, 0x800761F0:sh, 0x80076200:sh,
                               0x800BB890:lhu, 0x800BB908:lhu, 0x800BB940:lhu
        INITBTL.PRG 0 reference(s): NONE — this module never names the rectangle
        SLUS_010.40 0 reference(s): NONE — this module never names the rectangle
        TITLE.PRG   0 reference(s): NONE — this module never names the rectangle
      every store of the rectangle in every provisioned module: 0x800761E0 0x800761E8 0x800761F0 0x80076200
      the overlay publication's own four stores:                0x800761E0 0x800761E8 0x800761F0 0x80076200

The four stores are `func_800760CC`'s, read at BATTLE.PRG file offset 0xD8CC:

    0x800761E0  sh $zero, -0x202C($v0)   ; 0x8005DFD4  x = 0
    0x800761E8  sh $zero, -0x2028($v0)   ; 0x8005DFD8  y = 0
    0x800761F0  sh $s2,   -0x202A($v0)   ; 0x8005DFD6  w = the width argument
    0x80076200  sh $s3,   -0x2026($v0)   ; 0x8005DFDA  h = height - 16

**So a 0 rectangle means "no overlay publication has run yet", which is the ordinary state of the
whole boot and not a guest defect.** At the moment the boot publishes, BATTLE.PRG is not loaded, so
0x8005DFD4..DA is untouched BSS. The previous agent's reading of the fatal — that the two numbers
were two statements of one horizontal extent and disagreed — was wrong about the second statement,
and this census is what settles it.

## 2. WHICH WORD IS THE RESIDENT PUBLICATION'S OWN HORIZONTAL EXTENT

**`env + 4`, where `env` is the caller's `$a0` — a per-call address, not a constant.** Both env
leaves store the stated width there, read from the leaves' own words:

    0x8002B434  SetDefDispEnv   lw  $v1, 16($sp)     ; the fifth argument
    0x8002B438                 addu $v0, $a0, $zero
    0x8002B43C                 sh  $a1, 0($v0)      ; +0  x
    0x8002B440                 sh  $a2, 2($v0)      ; +2  y
    0x8002B444                 sh  $a3, 4($v0)      ; +4  w   <- the stated width
    0x8002B46C  (delay slot)   sh  $v1, 6($v0)      ; +6  h

    0x8002B374  SetDefDrawEnv   lw  $s2, 56($sp)     ; the fifth argument
    0x8002B384                 addu $s1, $a0, $zero
    0x8002B3A4  (delay slot)   addu $s0, $a3, $zero
    0x8002B3B4                 sh  $s0, 4($s1)      ; +4  w   <- the stated width
    0x8002B3DC  (delay slot)   sh  $s2, 6($s1)      ; +6  h

And for THIS title's boot, `env` is 0x8005E188. The resident's publication is `_initScreen` at
0x80042054, it is the only caller of `SetDefDispEnv` in the whole resident (one `jal`, at
0x8004207C), and it builds the struct pointer itself:

    0x80042058  addu    $a3, $a0, $zero       ; the STATED WIDTH, carried from its own $a0
    0x80042060  lui     $s0, 0x8006
    0x80042064  addiu   $s0, $s0, -7800       ; 0x8005E188  = vs_main_dispEnv[0]
    0x8004206C  addiu   $a1, $a1, -16         ; height - 16
    0x80042070  sw      $a1, 16($sp)          ; into the fifth slot
    0x8004207C  jal     0x8002B434            ; SetDefDispEnv(disp, 0, 0, w, h-16)

`vs_main_dispEnv = 0x8005E188` is the decompilation's own
`config/SLUS_010.40/symbol_addrs.txt:790`, and the body derives it from `lui 0x8006` plus
`addiu -7800` — two independent sources for the number the owner's refusal is about. Its sole caller
is `_displayLoadingScreen` at 0x800420BC, which states `addiu $a0, $zero, 320` /
`addiu $a1, $zero, 240` immediately before the `jal` at 0x800420F0. So the boot's publication's own
width word is **`0x8005E18C`**, and the run reads it:

    [drive] pre rw 8005E18C 1
    8005E18C: 00E00140                       <- the halfword is 0x0140 = 320
    [drive] pre rw 8005E18A 1
    8005E18A: 01400000                       <- 0x00E0 = 224, the height the leaf stored
    [drive] pre rw 8005DFD6 1
    8005DFD6: 00000000                       <- BATTLE's rectangle, still zero, and no longer consulted

**That is the direct proof the fix did what it claims: the leaf wrote 320 into the publication's own
word, and the overlay rectangle is still 0 next to it.**

## 3. THE FIX, and why this is the root cause rather than tolerating the symptom

Tolerating a zero rectangle would be a special case for the failing input and would disable the
check for the whole boot — which is where the boot's own geometry is published. The real defect was
two halves of ONE thing, and both are fixed:

**(a) The owner was REPLACING four resident SDK leaves, not observing them.** psxport's dispatch
consults a title's image-scoped override first and only enters the original body when no override is
active (`native_dispatch.cpp`, "the title's own override is consulted FIRST"). The four projection
overrides therefore ran INSTEAD of `SetGeomOffset`, `SetGeomScreen`, `SetDefDrawEnv` and
`SetDefDispEnv` — and the header already said the opposite: *"Each runs the retail body FIRST and
observes afterwards, so an observer can never change what the guest published."* That sentence was
false, and the consequence is larger than the abort: **the guest's GTE geometry, its display
environment and its draw environment were never written by anything in the product.** Two shapes
now, and the difference is measured rather than chosen:

  * the two GTE leaves PERFORM their measured retail effect through psxport's public
    `libgte_set_geom_offset` / `libgte_set_geom_screen` (which is the one implementation of the
    control-register write AND of the port's own record of it), and reproduce the leaf's own argument
    side effect from its `sll` words, then observe;
  * the two env leaves RUN THE ORIGINAL GUEST BODY through the framework's own
    `psx::cpu::callOriginalToReturn`, then read the word the leaf just filled. Their retail effect
    is pure guest memory, so the guest's own body is the correct implementation of it.

**WHY THE FRAMEWORK'S ENTRY POINT AND NOT A TITLE COPY — and this is a CORRECTION to what this
section first said.** It first claimed that a new `dynarec::callOriginalToReturn` in
`game/core/dynarec_dispatch.*` was "the ONE bounded resume-and-refuse rule". That would have been a
SECOND implementation of a rule `psxport` already owns: `psx::cpu::callOriginalToReturn` is declared
at `runtime/cpu/native_dispatch.h:96` and defined at `native_dispatch.cpp:434`, and duplicating
framework policy is not a style preference. The two leaves therefore call the framework's function,
and `game/core/dynarec_dispatch.*` and `game/core/native_owners.cpp` are UNCHANGED from `bdb151c`.

That is also the RIGHT function for these two leaves, for a second reason worth stating: it **aborts**
on a budget exit, and here that is a correct reading rather than a harsh one. The measured bodies are
12 and about 20 instructions against a 564,480-cycle turn, so a budget exit inside one of them means
the leaf at that address is not the leaf this owner was measured against — which is exactly the
failure the observation exists to catch.

**AND THE FRAMEWORK GAP THAT EXPOSES IS NAMED, because one caller in this repository DOES need a
resume.** `vs_main_initHeap` re-enters a body that can legitimately need more than one host turn and
carries its own bounded resume for it. It should not have to. `psx::cpu::callOriginalToReturn`
delegates to `requireGuestReturn`, which treats `BudgetExhausted` as fatal, while the framework's own
comment above `resumeOriginal` (`native_dispatch.cpp:334-345`) calls budget exhaustion "an ordinary
bounded exit" the host handles and then "resumes deliberately", and records that three repositories
each hand-rolled that resume because the framework lacked the entry point.

**THE REQUIREMENT, and it belongs to `psxport` and not to this repository:** add
`psx::cpu::callOriginalToReturnResuming(core, key, budget, owner)` to `runtime/cpu/native_dispatch.*`
— the same rule as the existing one, but resuming through `resumeOriginal` on `BudgetExhausted` until
`GuestReturn`, capturing the return address BEFORE the first dispatch — and let `vs_main_initHeap`
call it. Until that entry point exists this repository carries the loop, and that is framework policy
duplicated with a named owner.

**(b) The cross-check named BATTLE's rectangle.** It now names the leaf's own word, `env + 4` and
`env + 6`, with the guest-RAM bound applied to the DERIVED address — which the old constant-address
version could not need.

**The tests are the point, and one of them is the test that would have caught (a).** The old fixture
pre-seeded the coprocessor and the guest rectangle before invoking the override, so it passed against
an owner that did nothing. The new fixture seeds NOTHING and asserts the destinations moved:

    7d. THE OWNER PERFORMS THE GTE LEAVES RATHER THAN OBSERVING A FIELD NOBODY WROTE.
        gte_read_ctrl(24) == 160 << 16        ; SetGeomOffset moved CR24 ITSELF
        gte_read_ctrl(25) == 112 << 16        ; and CR25
        gte_read_ctrl(26) == 256              ; SetGeomScreen moved CR26
        projParams.geomOfx/Ofy/geomH == 160/112/256
        core.r[4] == 160 << 16, core.r[5] == 112 << 16   ; the leaf's own argument side effect
        core.r[4] == 256 after SetGeomScreen             ; and that leaf does NOT shift

plus `7b`, which replays the BOOT's 320x224 publication with 0x8005DFD6 deliberately left at zero and
requires the owner to survive it — the exact input that killed field 0 — and two refusals that are
observed to fire on the shipping reader (`refusesDrawAreaDisagreement`, stated 320 against a stored
256, which is the pair BATTLE's own `screen` rect literal produces; and
`refusesNonGuestRamArea`, which only exists because the address is derived now).

## 4. A FRAME, LOOKED AT, AND WHICH PHASE IT IS

One frame was presented and captured, and it was **opened**:

    scratch/run5/field0000.ppm   320x224, P6, 215,040 payload bytes
    scratch/run5/field0000.png   the same pixels, 2x, so it can be looked at rather than measured

It is a **uniform, featureless black rectangle**: no text, no border, no gradient, no noise, nothing
but the two window edges. The measurement agrees exactly — **0 of 71,680 pixels non-black, 1
distinct colour in the whole frame** — and the guest's own words say why: the run reaches
`[gpu] display standard -> NTSC (59.940 Hz fields …, GP1(08)=08000001)` in the same field, so the
display area was published and the mode was set, and nothing had been drawn into it yet.

**WHICH PHASE: the boot's first host field, before the title's first splash.** Not a splash, not the
intro movie, not the Start-skip menu, not gameplay. This repository's rule is explicit that boot,
logos, menus, FMV and a clean trace do not establish gameplay conformance, and this frame is one
step earlier than all of those. The run ends in field 1, so no later phase was ever presented.

**THE CADENCE TRAP WAS HANDLED EXPLICITLY AND DID NOT BITE, and the reason is worth recording.**
`tools/shot.py` exists because ports that double-buffer submit on odd fields can hide a per-field
overlay from a single even-field sample. The driver shoots EVERY field by default (`--shot-every 1`),
prints the parity of each, and two independent runs at the same field produced **byte-identical
captures**. So the black frame is not a sampling artefact: it is the whole of what this field had.
A single sample is still not a measurement of a per-present question, and the rule stands for the
next field that presents something.

## 5. WHAT S015 IS NOW, PRECISELY

S015 is `partial`, and the wording that carries the evidence is in `docs/project-state.md`. The
honest decomposition:

| clause | state | evidence |
|---|---|---|
| the product executes the AUTHENTICATED guest image through Lightrec | **established** | `authenticated resident image: scratch/bin/vagrant/SLUS_010.40 (337920 bytes, sha256 51dfdf15a…)`, then 44,855 → 58,663 executed instructions, 430 → 617 translated blocks |
| no guest block is interpreted | **established** | `fallback.calls=0` with all thirteen per-reason counters printed and zero, beside nonzero executor counters |
| the title's boot is owned rather than merely executed | **established** | the boot's own display-area publication is measured through the guest's leaf, 320x224 at `0x8005E18C` |
| the title reaches a TITLE phase | **missing** | the run ends in field 1, inside libcd's `CD_sync` |
| the title is playable | **missing** | — |

## 6. FATAL #3 PERSISTED, AND IT IS NOT THE FRAMEWORK'S IN-SEGMENT CLOCK

It persisted, unchanged, and the brief's hypothesis is **MEASURED AND REFUTED**.

`[executor:error] resident call2 required a completed guest call, but execution exited as
budget-exhausted at 0x80020F28 after 564486 cycles: cycle budget exhausted`

`0x80020F28` is `CD_sync` (the decompilation is `INCLUDE_ASM` for it, so the bytes are the source).
The loop is a libcd field-count wait, read from the words:

    0x80020F3C  addiu $a0, $zero, -1
    0x80020F5C  jal    0x8001F6C4          ; VSync(-1): the field counter
    0x80020F84  addiu $v0, $v0, 960       ; target = counter + 960
    0x80020F8C  sw    $v0, -0x6398($at)   ; -> 0x80039C68, the target word
    0x80020FA8  jal    0x8001F6C4
    0x80020FB4  lw    $v1, -0x6398($at)   ; $v1 = the target
    0x80020FBC  slt   $v1, $v1, $v0
    0x80020FC0  bne   $v1, $zero, 0x80020FF4   ; done when target <= counter
    ...  the retry counter at 0x80039C6C, and the counter-exhausted edge below.

**THREE ADDRESSES IN THE PARAGRAPH ABOVE WERE WRONG BY 0x10000, and so was the reading of the
number 0x3C. Both are corrected here rather than quietly, because the wrong addresses would send the
next reader to words nothing touches and the wrong reading would send them looking for a 60-cycle
tick that does not exist.** A 16-bit displacement is SUBTRACTED from the `lui` page; this title's
compiler emits `lui 0x8004` + `-0x6398`, which is 0x80040000 - 25496 = **0x80039C68**, not 0x80049C68.
Re-derived from the words, with the page and the displacement printed separately:

| what | `lui` page | displacement | the address, as a SUM |
|---|---|---|---|
| the target word | 0x80040000 | -25496 (`0x9C68` signed) | **0x80039C68** |
| the retry counter | 0x80040000 | -25492 (`0x9C6C` signed) | **0x80039C6C** |
| the third word | 0x80040000 | -25492 | **0x80039C70** |

**AND THE TRIO IS NOT PRIVATE TO `CD_sync`.** A reference census over all four provisioned modules
finds **28 references** to those three words — 16 writes and 12 reads — and only 7 of them (the 3
writes, 3 reads and 1 counter increment) are inside `CD_sync` at 0x80020F28..0x800211A8. The other 21
are in four further resident routines, in three groups that each write all three and read all three:
0x8002120C..0x8002128C, 0x80021644..0x800216E8 and 0x80021D40..0x80021DB8. Zero references in
BATTLE.PRG, TITLE.PRG or INITBTL.PRG. So `CD_sync`'s state is SHARED with three other routines, and
"the one word this routine owns" is not what the image shows. This matters for the next step: whatever
owns the CD wait has to agree with those three groups, not just with this function.

**AND "EVERY 60th ITERATION" IS NOT WHAT THE BYTES SAY — the number is a BOUND, not a modulus.**
0x8002105C has exactly **one** in-function edge into it in the whole of `CD_sync`, from the `beq` at
0x80020FEC, and the compare on that edge is a `slt` against a 32-bit constant:

    0x80020FE4  lui    $v0, 0x003C      ; $v0 = 0x003C0000 = 3,932,160
    0x80020FE8  slt    $v0, $v0, $v1   ; $v0 = (3,932,160 < counter)
    0x80020FEC  beq    $v0, $zero, 0x8002105C   ; taken when counter <= 3,932,160

There is no `andi`, no remainder and no divide anywhere on that path, so 0x3C is the *iteration
bound* 3,932,160 and not a 60. **The 60 is the bound in units of 65,536, and reading it as a modulus
is the kind of plausible decoding that produces a confident answer about a routine the decompilation
declines to decompile** — `external/rood-reverse/src/SLUS_010.40/libcd/BIOS.c` carries `CD_sync` as
`INCLUDE_ASM`, so there is no C body to check any reading against. The bytes are the only source, and
they say a bound.

**WHAT IS NOT ESTABLISHED FROM THE BYTES, and is not claimed.** Which direction the counter runs, and
what arms it. The counter at 0x80039C6C is written by four other routines as well as this one, so its
value on entry is not this function's to establish, and the edge above is relative to whatever they
left. Whether 0x8002105C is a timeout return, a completion return or a partial-failure return is
**NOT DETERMINABLE from the provisioned modules**, and no reading of it is offered here.

**THE MEASUREMENT THAT LOCALISES IT.** `0x80032114` is the guest's own VSync field counter, the word
`VSync(-1)` returns. Read before any field and again after field 0 completed:

    80032114: 00000001     before any field
    80032114: 00000002     after field 0

**One increment per host field, and zero increments across the 564,486 guest cycles of field 1.**

**AND THE FRAMEWORK'S FIX DID NOT CHANGE IT.** `4a08ec55` "The guest clock now advances INSIDE a
translated segment, so a guest polling a hardware counter can leave its loop", merged as
`5d4b3327`, landed in the shared framework while this work was in flight. The product was rebuilt
against it and the exit is the same address with the same 564,486 cycles. So the brief's
"possibly the framework's frozen in-segment clock" is **falsified as the cause**, and the
`cpu-executor` claim is NOT a dependency of this defect.

**WHAT IT IS INSTEAD, and it is a title-side gap with a named address.** The loop's only other exit
is the CD completion, and the byte that carries it has **exactly one writer in the whole resident
executable**:

    0x80020D38  sb  $v0, -0x1DB28($at)   -> 0x800324D8

which `CD_sync` reads at 0x80021000 (`lbu $a0, 0($s2)`) with `$s2 = 0x800324D8`. The single writer
sits in the unnamed libcd command-state function between `CdDataSync` (0x800209A0) and `CD_sync`
(0x80020F28) — the module map names no symbol there. **The boot never reaches it, so the byte is
never written, and the only remaining exit is a 960-field timeout that one turn cannot contain.**

Separately, and independently: `VagrantRuntime` does **not** override
`GameRuntime::guestCdStreamCallbackLayout()`. psxport's `cdReadyCallbackOwnedByGuestInterrupt()`
requires a declared layout whose `readyCallbackPointer` is non-zero and whose owner is
`GuestInterrupt`; with none declared it returns false, so the framework's CD-ready-callback delivery
to the guest's own interrupt path is not part of this title's contract, and
`deliverCdReadyCompletionOnInterrupt` returns `NotOwned`. A stock libcd consumer learns a sector
arrived because the BIOS's CD-ROM interrupt handler calls the function pointer the guest installed —
which is ROM this framework does not have — so that declaration is the seam, and this title has not
made it.

**WHAT I DID NOT ESTABLISH, and it matters.** I have not proved that declaring the layout ends the
wait, because I have not measured the slot address `CdReadyCallback` writes. That is RE, it is
title-side, and it is the next step — not a framework fix, and not something to work around here.
Widening `CD_sync`'s own budget, or writing 0x800324D8, would be forging guest state.

## 7. THREE TOOLS WHERE THERE WAS ONE, because the cap was telling the truth

`tools/verify.py` failed this work at `tools/re_viewport.py:1201: source has 1216 lines; cap is
1200`, and the cap is a real rule rather than a formatting preference: a file holding two
responsibilities is a file whose halves stop agreeing. So:

| tool | subject | gate |
|---|---|---|
| `tools/re_viewport.py` | the BATTLE OVERLAY publication, plus the MIPS-I field decoder and the SHA-bound image loaders both other tools import | `vagrant_viewport_bytes_selftest` 6/6, `vagrant_viewport_bytes` 25 claims |
| `tools/re_display_area.py` | the RESIDENT display-area publication, and which word IS one horizontal extent | `vagrant_display_area_selftest` 4/4, `vagrant_display_area` 7 claims |
| `tools/re_vsync_sites.py` | every `jal VSync` site and the field count its argument holds | `vagrant_vsync_sites_selftest` 3/3, `vagrant_vsync_sites` |

The decoder is IMPORTED, never copied, and `re_viewport.py` imports `re_display_area` **at the point
of use, not at module scope** — a module-scope import there is a cycle, because the callee imports the
caller, and whichever tool runs first re-enters the other while it is half initialised. That is the
same class of bug as two files owning each other's names, and it is fixed the same way: one direction
of ownership, resolved where it is used.

## 8. TWO INSTRUMENT DEFECTS THIS WORK FOUND IN ITS OWN INSTRUMENTS

**`re_viewport.py` named every GTE register move `mfc2` or `mtc2` from bit 25 alone**, so it
labelled a WRITE as a READ on every coprocessor move it printed, and `battle_projection_facts.h`
hedged `mtc2/mfc2` because the tool's label was not trustworthy. Naming a direction needs the
R3000A COP2 transfer ENCODING, which is a reference and not a field extraction, so the tool now
reports the register number and the raw selector and names no direction, and the claim says so. The
`cr` field was always right — it is the `rd` field of every transfer encoding — so no claim changed
verdict.

**`re_vsync_sites.py` printed a hardcoded sentence about BATTLE** — "Two sites, both VSync(1) …
the BATTLE module itself never waits a field count through VSync" — as a fixed claim rather than
deriving it from the census printed directly above it. Deriving it immediately produced
"2 of them waiting", because the histogram keys are argument VALUES and the comparison was against
the strings `"0"` and `"1"`. The sentence is now derived, names its three cases, and refuses to draw
the conclusion when the line contradicts it. It was right for this image and wrong as a mechanism,
which is the combination that survives review.

## Falsifiers

- If `0x8005E18C` does not read 320 in a run whose log shows the boot's publication, then the leaf
  does not store the stated width at `+4` and this issue's `env + 4` reading is wrong — though the
  bytes at 0x8002B444 and 0x8002B3B4 would then have to be something else.
- If a resident `SetDefDispEnv` call site other than 0x8004207C exists, then the boot is not the only
  caller and the "one publication" reading of the fatal changes.
- If `fallback.calls` is non-zero on a longer run, then "dynarec-only" is false for this title and
  the per-reason breakdown — not this issue — says which instruction class is unsupported. The
  per-reason counters all exist and are printed, so that run is one command away.
- If a declared `guestCdStreamCallbackLayout` does NOT end the `CD_sync` wait, then the completion
  byte at 0x800324D8 has a route this issue has not found, and the single-writer census becomes a
  statement about the `lui`-reachable references only. The census states its method for that reason.
- If the product dies at 0x80020F28 with a cycle count other than 564,486 after the framework's
  in-segment clock commit, then this issue's reading that the commit does not reach this defect is
  wrong.
- If the first presented field is non-black on a machine whose run reaches a later phase, then the
  black field was a timing artefact of the headless present and not the field's content.

- **FOR THE ADDRESS CORRECTION ABOVE.** If `lui 0x8004` with displacement `-0x6398` does not name
  0x80039C68, then the address is not `page - displacement` and the correction is wrong the other
  way. The check is a direct read: `0x80039C68` must hold the value `CD_sync` stored, and
  `0x80049C68` must hold nothing that routine wrote. One `rw` over the control surface settles it,
  and the census that produced 28 references printed the page and the displacement separately
  precisely so the sum could be re-checked by hand.
- **FOR "A BOUND, NOT A MODULUS".** If any instruction on the path from 0x80020FCC to 0x8002105C
  performs a remainder against 60 — an `andi`, a mask to 0x3F, or a divide — then 0x3C is a modulus
  after all and "every 60th iteration" was right. The claim is that a full decode of that straight
  line finds none, and that decode is what a reader should repeat rather than take.
- **FOR THE SHARED-TRIO CENSUS.** If 0x80039C68/6C/70 are in fact private to `CD_sync`, then the 21
  references outside 0x80020F28..0x800211A8 belong to some other address, and the census's sum rule
  is admitting a page borrowed from a different word. The control in the same scan — a word the
  resident demonstrably names — is what makes that checkable rather than asserted.
- **FOR THE FRAMEWORK-OWNERSHIP CORRECTION.** If `psx::cpu::callOriginalToReturn` is absent from
  `runtime/cpu/native_dispatch.h`, then the projection leaves had no framework entry point to call
  and a title-owned one was necessary after all; the named requirement would then be an addition
  rather than a rename.

## NOT established by this issue

Any TITLE phase. Any gameplay. Playability, widescreen, interpolation, BATTLE, INITBTL: all still
`missing`. A frame with content. A completed run, so no run-end census. The `CD_sync` route to its
completion. Whether `fallback.calls` stays 0 past the boot — the number is 0 over 58,663 executed
instructions and that is all it covers.

---
id: 3
title: crt0_setup never sets a1, so the BIOS InitHeap HLE builds a ZERO-SIZE heap (framework defect; LATENT in Vagrant Story — nothing in this image calls BIOS malloc)
status: fixed
symptom: guest malloc/InitHeap: every heapAlloc returns 0 with no unusual log line; on a game whose crt0 calls BIOS A0:0x39 InitHeap the arena is created with size 0
tags: framework,boot,heap,hle,re-01
created: 2026-08-12
updated: 2026-08-12
---

## SEVERITY CORRECTED 2026-08-12 — read this before the symptom section

This was filed as a defect that Vagrant Story *surfaces*, on the reasoning "crt0 calls BIOS InitHeap,
therefore this game's malloc is broken". The second half does not follow, and it is now measured false
for this game: **nothing in `SLUS_010.40` can call BIOS malloc.** Census over the whole loaded image
(`tools/re_crt0.py`, 2,023 `jal` sites against 19 BIOS A0 thunks): the only heap-related A0 thunk
present at all is `InitHeap` at `0x80026864`, and its only caller is crt0 itself at `0x8001F5CC`. There
is no `malloc`/`free`/`calloc`/`realloc` thunk anywhere in the image, so no code in it can reach one.
The game allocates from its own allocator instead — rood-reverse names it `vs_main_initHeap`
(`0x80043F74`), initialised with an arena at `0x8010C000 + 0xF2000`, which is *above* the image's
`0x80062000` end.

Two consequences, and the second is the one that matters:

1. **The zero-size arena is INERT here.** Nothing allocates from it, so this game boots (or fails to)
   for reasons unrelated to this bug. The defect is real and the contract is genuinely wrong — fix it
   upstream for that reason, not because this port is blocked by it.
2. **This game cannot demonstrate the fix.** "How to verify once it is fixed" below still works (the
   BIOS-call log line shows the argument), but a *successful boot* of Vagrant Story is not evidence
   that the heap contract is right, and a broken boot is not evidence that it is wrong. Whoever fixes
   it upstream needs a consumer whose guest actually calls BIOS `malloc`.

Related correction: the crt0-declared arena `[0x800401AC,0x801FBFFC)` overlaps 138,836 bytes of the
loaded image (this executable is three separately-linked segments, and `heapBase` is the end of the
FIRST one's `.bss`). That is true on real hardware too and is *not* a reason to distrust the measured
values — see claim C004 limits 2 and 3 — but it does mean a psxport heap given the faithful size would
hand out addresses inside the guest's own code if anything ever asked it to. Nothing does.

## Symptom

A guest whose crt0 initialises the heap through the **BIOS** (`A0:0x39 InitHeap`) gets an arena of
**size 0**. `Hle::heapAlloc` then returns 0 for every request (`if (!heap_ok || size == 0) return 0;`
plus no block large enough), and nothing in the log says the size was wrong — the BIOS-call debug line
prints the zero as if it were the guest's own argument.

## Root cause (static, in the PINNED framework — NOT this repo's code)

`external/psxport/runtime/recomp/native_boot.cpp`, `crt0_setup()`:

```cpp
  uint32_t heapsz = (v0 - v1) - a0;
  c->mem_w32(cfg->heapSizePtr, heapsz);              // heap size  <-- computed, written to memory
  a0 |= 0x80000000u;
  c->mem_w32(cfg->heapBasePtr, a0);                  // heap base
  c->r[28] = cfg->gp;
  c->r[29] = sp; c->r[30] = sp;
  c->r[4]  = a0 + 4;                                 // a0 for the init call   <-- ONLY a0 is set
  rec_dispatch(c, cfg->libcInit);                    // libc/heap init
```

`heapsz` is computed and stored to the guest global, but never placed in **`c->r[5]` (a1)**. The
consumer of that register is the framework's own HLE — `runtime/recomp/hle.cpp:355`,
`case 0x39: heapInit(a0, a1);` — and `Hle::heapInit(addr, size)` takes the size **from a1**, not from
`heapSizePtr`.

## Why the defect is REACHED here at all, and why Tomba! 2 apparently is not affected

Measured in this repo (RE-01, claim C004) — this is why `crt0_setup` reaches the buggy path on this game, NOT why the game breaks (see the severity correction above): `SLUS_010.40`'s `libcInit` is `0x80026864`, which is
`addiu $t2,$zero,0xa0 / jr $t2 / addiu $t1,$zero,0x39` — a **tail-jump thunk into the BIOS A0 table**,
i.e. it is not a linked routine at all; the HLE is the only implementation. The guest crt0 provably
passes the size in a1:

```
8001F59C  00432823  subu  $a1, $v0, $v1     ; a1 = (_ramsize-8) - _stacksize
8001F5A0  00a42823  subu  $a1, $a1, $a0     ; a1 = 0x001BBE50   (heap size)
8001F5A8  ac250fb8  sw    $a1, 0xfb8($at)   ; __heapsize
8001F5CC  0c009a19  jal   0x80026864        ; InitHeap(a0=0x800401AC, a1=0x001BBE50)
```

`tools/re_crt0.py` prints both argument registers at that call precisely so this cannot be missed
again, and its selftest asserts a1 is non-zero.

Tomba! 2's config has the same crt0 SHAPE (`bssZeroHi == heapBase`, adjacent stack-top globals,
`libcInit = 0x80089860`), so it is likely that its libcInit is a **linked** libc routine that reads
`__heapsize` from memory rather than a BIOS thunk — which would make the missing a1 invisible there.
That is a HYPOTHESIS about Tomba! 2, not a measurement: nobody has disassembled 0x80089860 here.

## The fix, and where it belongs

One line in the framework: `c->r[5] = heapsz;` next to `c->r[4] = a0 + 4;` in `crt0_setup`. It is
faithful for both shapes (a linked libc that ignores a1 is unaffected), and it is *not* a special
case — it restores an argument the guest crt0 actually passes.

**Not fixed here.** `external/psxport` is a read-only pinned consumer; framework edits happen only in
the workspace dev clone, and another agent held it during this session. **Do not work around it
game-side** — a game-side heap fixup is exactly the "magic that makes boot line up" this port must not
accumulate. `game/core/game_config.cpp` carries a ⚠ note pointing here.

## How to verify once it is fixed

There is no substrate yet, so this is a code-read, not a run. When `vagrant_port` first boots:
`PSXPORT_DEBUG=bios` must show `A0:0x39(0x800401AC, 0x001BBE50, ...)` — the second argument is the
whole point. A zero there means the fix is absent or was reverted.

## FIXED IN THE FRAMEWORK 2026-08-12 — psxport 726d10c9, and this repo now pins it

`crt0_setup` no longer applies anything it computed itself: the whole boot group moved into
`runtime/recomp/crt0_boot.h` as a pure `crt0_plan`, and `crt0_apply` sets `a1` (`w.reg(5, p.a1)`)
beside `a0`. Exactly the one-line fix this card specified, in the place it said it belonged.

The fix is gated in both directions rather than asserted: deleting `w.reg(5, p.a1)` turns
`tests/test_crt0_boot_group.cpp` RED (verified by sabotage, then restored at identical md5), and
`crt0_verify.h::crt0_audit` re-derives the group from the guest's own instruction stream at every
boot and refuses a confirmed disagreement.

### THIS CARD'S HYPOTHESIS ABOUT TOMBA! 2 IS FALSIFIED — and the truth is worse, not better

The card reasoned that Tomba! 2's `libcInit = 0x80089860` is "likely a **linked** libc routine that
reads `__heapsize` from memory rather than a BIOS thunk — which would make the missing a1 invisible
there", and correctly labelled it a hypothesis nobody had disassembled. It is now MEASURED, two ways,
and it is wrong:

* `psxport/build/tools/crt0_extract` over Tomba! 2's `MAIN.EXE` reports **"libcInit IS the A(39h)
  InitHeap thunk: YES · a1 IS live at the guest's own jal: YES"**.
* A real 428-frame boot of `tomba2_port` logs `[hle] InitHeap(base=0x8010622C, size=0xF99D0 = 1022416
  bytes) from guest a0/a1`, and the crt0 line beside it reads **"a1 held 0x00000000 = 0 before crt0
  set it"**.

So Tomba! 2 — the framework's own reference consumer — was ALSO calling `InitHeap(base, 0)`. The bug
was never Vagrant-specific and was never invisible elsewhere; it was latent everywhere for the same
reason this card established here by census: the measured paths make no BIOS malloc calls. Spyro and
Spider-Man show the identical `a1 held 0x00000000` line on their own boots.

**The generalisable lesson, which is this card's real contribution:** the census argument ("no malloc
thunk exists in the image, so no code can reach one") is what made the severity correction sound, and
it is the method that should have been applied to Tomba! 2 instead of a shape comparison. A structural
argument about what the binary CAN do beat a plausible inference about what it probably does — and the
inference was the part that turned out wrong.

`Hle::heap_refused` now counts requests the arena could not satisfy and names the condition on the
first refusal and each power of two after it, so a zero-capacity heap can no longer be silent. Note
what its zero means: on the Tomba! 2 boot it read 0 refusals because 0 allocations were REQUESTED, not
because the heap was healthy.

### Verification once `vagrant_port` boots (unchanged, and now checkable)

`PSXPORT_DEBUG=bios` must show `A0:0x39(0x800401AC, 0x001BBE50, ...)`. Additionally, `crt0_audit` will
print its own AGREE/DISAGREE tally against these bytes; the other five ports currently report
"10 field(s) AGREE, 0 DISAGREE, 0 unresolved".

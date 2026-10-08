---
id: 39
title: Vagrant Story presents 2 fields per game frame (30 fps) or 4 (15 fps) at run time, and the choice is presentation, not simulation speed
status: open
symptom: The workspace map recorded "`vagrant`: `VSync(2)` x3, `VSync(3)` x2 … leads to 30 fps", labelled it a GOAL rather than a measurement, and left the title's interpolation scope undecided on the strength of a docstring. The image and three overlays are provisioned and SHA-1-matched against the decompilation's own targets, so the question is answerable from bytes.
tags: cadence,vsync,frame-rate,presentation,interpolation,decomp,bytes
created: 2026-09-28
updated: 2026-09-28
---

## Answer

**2 fields per game frame = 30 fps, or 4 fields = 15 fps, chosen at run time. NEVER 60 fps.** The
choice is a **presentation** decision, so interpolation over the same source geometry is well-founded.

`vs_main_gametimeUpdate` at `0x8004261C` passes `$a0` straight through to the title's VSync at
`0x8004262C` (`move $s0,$a0` at `0x80042624`, nothing writes `$a0` between), and the battle present
`0x8007629C` loads its argument from `0x8005E24C` at `0x800762F8`. So
**`vs_gametime_tickspeed` (`0x8005E24C`) is the field count passed to VSync.**

## The `n >= 2` rule, from this title's own bytes

VSync at `0x8001F6C4`, found by shape search over 83,876 word-aligned candidates (1 match):

```
8001F71C  bgez  $a0      -> a0 < 0 returns without waiting
8001F738  beq   $a0,1    -> a0 == 1 returns without waiting
8001F740  blez  $a0      -> a0 <= 0 returns the current count
8001F770  addiu $a1,$a0,-1   -> a0 >= 2 waits (a0-1) further fields
8001F774  jal   0x8001F83C   -> the one shared wait helper
```

The helper does `sll $a1,$a1,15` then `slt counter,target; beqz -> return`, so a count of 0 returns
immediately. With the in-progress field included, **`a0 >= 2` waits `a0` fields, and 0, 1 or negative
waits not at all.** `VSync(0)` and `VSync(-1)` therefore carry no rate information in this title.

## The rate is VARIABLE, over a closed domain of two values

Census of every access to `0x8005E24C` across the resident image and three overlays: 368,826 words
scanned, 63 accesses matched, 10 writers — 8 in BATTLE.PRG, 1 in INITBTL.PRG, 1 in TITLE.PRG, none in
the resident. One BATTLE writer's value is not a literal within 12 instructions and is counted as
unresolved rather than assumed.

The public setter `func_8007C36C` makes the domain closed and provable:

```
8007C36C  addiu $v0,$zero,2 ; beq $a0,$v0 -> store
8007C374  addiu $v0,$zero,4 ; bne $a0,$v0 -> else return unchanged
```

**It admits only 2 and 4.** There is no path by which the global can hold 1, and 1 could not pace the
game anyway because `VSync(1)` does not wait. So the answer is 30 or 15 fps, and 60 fps is
structurally impossible — not merely unobserved.

## The 2-vs-4 choice is PRESENTATION

- the **game clock** adds `vs_gametime_tickspeed` per frame and wraps at 60 frames to the second
  (`0x80042674` `lbu $v0,0xE24C($v0)`, then `slti $v1,$v1,0x3C`);
- **`D_80050468.frames`** (a second h/m/s/f clock) adds and subtracts the same value, wrapping at 60;
- **`battleAbilityTimer`** adds it per frame and is compared against
  `battleAbilityTargetWindow - tickspeed*2`;
- the **angle accumulators** add it modulo 720 and modulo 30;
- a **countdown helper is handed a margin DIVIDED by it**: `func_80096FF0((margin * 2) / tickspeed)`.

Every consumer scales its per-step increment by the same value that scales the field wait, so a
doubled increment under a doubled wait is **rate-invariant**: the game's clock keeps real time while
the picture is presented half as often. The simulation is not slowed; the sampling is. **The source
geometry is the same stream, so interpolation over it is correct.**

## What the earlier lead got wrong

The prior `VSync(2)` x3 / `VSync(3)` x2 list was a census of the **decompiled source text**, not of the
image, and it mixed CD/sound wait loops into the rate question — every `vs_main_gametimeUpdate(0)`
site is a no-wait poll and never sets the rate, and `VSync(3)` appears nowhere in the image's pacing
path. The **rate-bearing** argument is exactly one variable, with exactly two legal values.

## Coverage, stated rather than implied

The census covers the resident and **3 of 11 declared `.PRG` modules**; `MENU/*`, `GIM/*` and
`ENDING/*` are not provisioned, so a writer in one of them is not in the denominator. The
`func_80096FF0` countdown claim rests on its ARGUMENT, which is decompiled; its internals are
`INCLUDE_ASM`. The `{2,4}` domain is falsifiable rather than asserted: a writer storing 5 would be
rejected by the domain check.

## What this changes

Vagrant Story is a **30 fps title**, so an interpolated 60 fps presentation is **IN scope**, and its
variable-rate cutscenes do not change that: the 4-field mode is the same geometry sampled at half
the rate, not a different simulation.

## Falsifier

If the BATTLE writer at `0x80073468` — the one whose value is unresolved — stores something other than
2 or 4, the closed domain is wrong and "never 60 fps" is wrong with it. A writer in an unprovisioned
`MENU/*.PRG`, `GIM/*.PRG` or `ENDING/*.PRG` outside `{2,4}` makes the domain incomplete. And if the
game clock's 60-frames-to-the-second wrap is not the retail unit — i.e. `vs_main_gametime` is a
cosmetic counter and the real simulation is uncompensated — then the choice would be a
simulation-speed change and interpolation would be over a *slowed* stream.
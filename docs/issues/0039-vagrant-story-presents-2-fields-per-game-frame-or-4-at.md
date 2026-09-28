---
id: 39
title: Vagrant Story presents 2 fields per game frame (30 fps) or 4 (15 fps) at run time, and the 2-vs-4 choice is presentation, not simulation speed
status: open
symptom: The workspace map recorded "`vagrant`: `VSync(2)` x3, `VSync(3)` x2, plus 0 and -1 -> **leads to 30 fps**", labelled it a GOAL not a measurement, and left the title's lerp scope undecided on the strength of a docstring. The image and all three overlays are provisioned and SHA-1-matched against the decompilation's own targets, so the question is now answerable from bytes.
tags: cadence,vsync,frame-rate,presentation,interpolation,lerp,decomp,bytes
created: 2026-09-28
updated: 2026-09-28
---

## Answer

**2 fields per game frame = 30 fps, or 4 fields = 15 fps, chosen at run time. NEVER 60 fps.**
The choice is a **PRESENTATION** decision, so interpolation over the same source geometry is
well-founded.

`vs_main_gametimeUpdate` is at `0x8004261C`. Its single `jal` to the title's VSync
(`0x8004262C`) passes `$a0` straight through — the bytes are
`move $s0,$a0` at `0x80042624` and nothing writes `$a0` in between — and the battle present
`func_8007629C` loads its argument from `0x8005E24C` at `0x800762F8`. So
**`vs_gametime_tickspeed` (0x8005E24C) is the field count passed to VSync.**

## The `n >= 2` rule, established from THIS title's own bytes

Not carried over from `crashbash`. VSync is located by a shape search (`tools/re_cadence.py`
`VSYNC_SHAPE`, matched 1 of 83,876 word-aligned candidates) and its argument branches are read
back and asserted every run:

```
8001F71C  04810005  bgez  $a0      -> a0 < 0 returns without waiting
8001F734  24020001  addiu $v0,zero,1
8001F738  1082003A  beq   $a0,$v0  -> a0 == 1 returns without waiting
8001F740  18800007  blez  $a0      -> a0 <= 0 takes the snapshot target
8001F768  18800002  blez  $a0      -> a0 <= 0 sends count 0 to the helper
8001F770  2485FFFF  addiu $a1,$a0,-1  -> a0 >= 2 waits (a0-1) further fields
8001F774  0C007E0F  jal   0x8001F83C   -> the one shared wait helper
```

The helper at `0x8001F83C` does `sll $a1,$a1,15` and then `slt counter,target; beqz -> return`,
so a count of 0 returns immediately. With the in-progress field included, **`a0 >= 2` waits
`a0` fields and `a0` of 0, 1 or negative does not wait at all.**

**`VSync(0)` and `VSync(-1)` therefore carry no rate information in this title either**, exactly
as in `crashbash`, `ctr` and `spyro`.

## The rate is VARIABLE, over a closed domain of two values

Census of every access to `0x8005E24C` across the resident image and all three overlays —
**368,826 words scanned, 63 accesses matched, 10 of them writers**:

| module | writers | values stored |
|---|---|---|
| BATTLE.PRG | 8 | 2 (`0x8006FC90`), 4 (`0x800703E4`), 2 (`0x800734A4`), 4 (`0x80074218`), 2 (`0x800742C4`), 2 (`0x80074338`), and 2 not resolved to a literal |
| INITBTL.PRG | 1 | 2 |
| TITLE.PRG | 1 | 2 |
| resident | 0 | — |

The public setter `func_8007C36C` at `0x8007C36C` makes the domain **closed and provable**:

```
8007C36C  24020002  addiu $v0,$zero,2
8007C370  10820003  beq   $a0,$v0      -> store
8007C374  24020004  addiu $v0,$zero,4
8007C378  14820004  bne  $a0,$v0      -> else return unchanged
```

**It admits only 2 and 4. There is no path by which this global can hold 1**, and 1 could not
pace the game anyway because `VSync(1)` does not wait. So the answer is 30 or 15 fps, and
**60 fps is structurally impossible** — not merely unobserved.

## The 2-vs-4 choice is PRESENTATION. This is the deliverable.

`VSync(2)` in a render frame and `VSync(4)` in a "run the game at half speed" branch would mean
opposite things for interpolation. It is the first, and the code says so in the consumers:

- **the game clock** adds `vs_gametime_tickspeed` per frame and wraps at **60 frames to the
  second** — `0x80042674` `lbu $v0,0xE24C($v0)`, then `slti $v1,$v1,0x3C` on the byte counter:
- **`D_80050468.frames`** (a second h/m/s/f clock) adds and subtracts the same value, wrapping
  at 60 to the second (`146C.c:11917`, `11946`);
- **`battleAbilityTimer`** adds it per frame (`146C.c:5546`) and is compared against
  `battleAbilityTargetWindow - tickspeed*2` (`146C.c:5537`);
- the **angle accumulators** add it modulo 720 and modulo 30 (`146C.c:12135`, `12167`);
- a **countdown helper is handed a margin DIVIDED by it** —
  `func_80096FF0((margin * 2) / vs_gametime_tickspeed)` (`146C.c:5540`).

Every consumer scales its per-step increment by the same value that scales the field wait. A
doubled increment under a doubled wait is **rate-invariant**: the game's own clock keeps real
time while the picture is presented half as often. The simulation is not slowed; the sampling
is. **The source geometry is the same stream, so interpolation over it is correct.**

## What the earlier lead got wrong

The prior session's `VSync(2)` x3 / `VSync(3)` x2 list was a census of the **decompiled source
text**, not of the image, and it mixed the CD/sound wait loops into the rate question. The
`vs_main_gametimeUpdate(0)` sites in `main.c` (8013-8062, 9343-9349, 9697, 9710, 10127, 10443)
are all CD/sound waits and pass 0, which is a no-wait poll; they never set the rate. `VSync(3)`
appears nowhere in the image's pacing path at all. The **rate-bearing** argument is exactly one
variable, and it has exactly two legal values.

## Coverage, stated rather than implied

- The census covers the resident image and **3 of the title's overlays**. The decompilation
  declares 11 `.PRG` modules; `MENU/*`, `GIM/*` and `ENDING/*` are **not provisioned**, so a
  writer in one of those is not in the denominator. This is why `re_cadence.py` REFUSES the
  whole report if any listed module fails its SHA-1 rather than silently shrinking the domain.
- The one BATTLE writer whose stored value is not a literal within 12 instructions is counted as
  **unresolved** and excluded from the domain claim, not assumed to be 2 or 4.
- `func_80096FF0` is `INCLUDE_ASM` in the vendored decompilation, so the countdown helper's
  internals are not read; the claim rests on its ARGUMENT, which is decompiled.

## Instrument

`tools/re_cadence.py`, registered as `vagrant_cadence_selftest` and `vagrant_cadence`. VSync,
the wait helper and the game-clock update are all found by `unique_shape`, so no address is
typed in. Every count carries its denominator. `--selftest` is **8/8** and each negative was
shown red:

| negative | shown red as |
|---|---|
| `VSync`'s `a0==1` no-wait branch broken | `VSync+0x74 is 0x1082003B, not 0x1082003A` |
| `VSync`'s `(a0-1)` field count broken | `VSync+0xAC is 0x2485FFFE, not 0x2485FFFF` |
| `VSync`'s count-0 branch broken | `VSync+0xA4 is 0x18800003, not 0x18800002` |
| wait helper's `<<15` countdown broken | `matched 0` with its scanned denominator |
| `VSync`'s shape anchor broken | `matched 0` — the identity search refuses to re-point |
| game clock's tickspeed load broken | `materialises 0x8005E24D, not 0x8005E24C` |
| a writer storing **5** injected | rejected by the `{2,4}` domain check |
| `BATTLE.PRG` store zeroed on disk | `REFUSED: payload SHA-1 ... is not the decompilation's target; not censused` |

The last two are the ones that matter most. The identity check sits *under* every other
negative, so a selftest that only asserted "it refused" would pass while testing SHA-1 six times
over; each case therefore asserts the refusal names its own subject. And the `{2,4}` domain is
falsifiable rather than asserted, because a 5-valued writer is injected and must be rejected.

## What this changes

Vagrant Story is a **30 fps title**, so an interpolated 60 fps presentation is **IN scope** for
it, and its variable-rate cutscenes do not change that: the 4-field mode is the same geometry
sampled at half the rate, not a different simulation.

## Falsifier

If the BATTLE writer at `0x80073468` — the one whose value is not resolved to a literal within
12 instructions — stores something other than 2 or 4, the closed domain is wrong and this
issue's "never 60 fps" is wrong with it. `re_cadence.py` counts that writer as unresolved today,
so the falsifier is already instrumented: it fires as soon as the value is read.

Second falsifier: if a **provisioned `MENU/*.PRG`, `GIM/*.PRG` or `ENDING/*.PRG`** contains a
writer of `0x8005E24C` outside `{2,4}`, the domain is incomplete. The tool will then refuse once
that module is added to its list, which is the intended behaviour.

Third: if the game clock's 60-frames-to-the-second wrap is not the retail unit — i.e. if
`vs_main_gametime` is a cosmetic counter and the real simulation is uncompensated — then the
2-vs-4 choice would be a simulation-speed change and interpolation would be over a *slowed*
stream. The counter's wrap constants (`0x3C` = 60 on the frame byte, `0x64` = 100 on the hour
byte) are asserted in the shape and would have to change for this to be false.

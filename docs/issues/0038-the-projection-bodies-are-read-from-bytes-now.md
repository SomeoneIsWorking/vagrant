---
id: 38
title: The projection bodies are read from bytes now, and the 256 was not a clip
status: open
symptom: `docs/issues/0037` shipped `vagrant::BattleProjectionOwner` against four SDK leaves whose bodies were a decompilation reconstruction, refused to widen, and named the reason as a 256-pixel screen rectangle this port "has not read from bytes". The image it needed is now provisioned, so the reconstruction could be checked.
tags: S008,S010,S011,S015,widescreen,projection,vsync,decomp,bytes
created: 2026-09-27
updated: 2026-09-27
---

## What was found, and how it was found

`tools/re_viewport.py` is the new instrument. It reads the **instruction words** out of the
SHA-bound images, which is a different kind of statement from the two sources issue 0037 had: those
agreed on *which function lives at an address*, and neither could say *what the function does*.

Identity gate, before any address is read:

| image | bytes | sha1 | matches rood-reverse's declared target |
|---|---|---|---|
| `scratch/bin/vagrant/SLUS_010.40` | 337,920 | `fababcfd…e48c` | yes |
| `scratch/bin/overlays/BATTLE.BIN` | 577,828 | `d53aacc…c72a9` | yes |
| `scratch/bin/overlays/TITLE.BIN` | 554,568 | `f74a76e…b139a` | yes |
| `scratch/bin/overlays/INITBTL.BIN` | 7,036 | `d7ea16e…fcc32` | yes |

**THE EXECUTABLE'S FILE MAP IS ITS OWN PS-X HEADER, and that is new.** The header says `t_addr =
0x80010000`, `t_size = 0x52000`, so the text segment covers file offsets `0x800..0x52800` — the whole
file, including the two further code runs after the bss gap. One linear map, file `0x800` ↔ vram
`0x80010000`, is the image's own statement. This repository previously believed three segments had to
be stitched from `splat.yaml`; the header already said all of it, and the 7 named library entry points
decode where that map puts them (7 of 7).

The tool is **zero-dependency on purpose**. The locked environment has no `capstone` and CTest runs
`.venv/bin/python3`, so a `capstone` import would pass on a machine with a global install and fail in
CI. The decoder is a small MIPS-I *field* extractor that names a SPECIAL instruction only for the five
funct values the shipped claims use. That is not gold-plating: an earlier revision of this file used one
conflated table for the SPECIAL funct index and the opcode index, and read `sh $a1, 0($v0)` as `break`
and a 320-wide dispenv as a break instruction — a measurement that could not fail.

### The claim table: 24 CONFIRMED, 1 REFUTED, 1 NOT DETERMINABLE

Run `python3 tools/re_viewport.py`. Each row prints the instruction words that settle it.

| claim | verdict | the words that settle it |
|---|---|---|
| `0x800760CC` is a function entry in BATTLE.PRG (file `0xD8CC`, base `0x80068800`) | CONFIRMED | `0x27BDFFC0  addiu $sp, $sp, -0x40` |
| centre is `arg0/2`, as `(arg0 + (arg0>>31)) >> 1` | CONFIRMED | `0x001227C2 srl $a0,$s2,31` / `0x02442021 addu $a0,$s2,$a0` / `0x00042043 sra $a0,$a0,1`, then `0x80076124 jal 0x80041540` |
| centre is `(arg1-16)/2 + 16` | CONFIRMED | `0x24B3FFF0 addiu $s3,$a1,-0x10` / `0x24A50010 addiu $a1,$a1,0x10` |
| H is `arg2` | CONFIRMED | `0x00C08021 move $s0,$a2`, `0x8007612C jal 0x80041534` |
| two draw areas via `SetDefDrawEnv` | CONFIRMED | `0x8007614C` and `0x80076188` both `jal 0x8002B374` |
| two display areas via `SetDefDispEnv` | CONFIRMED | `0x8007616C` and `0x800761A0` both `jal 0x8002B434` |
| both `screen` rects are literals (0, 8, 256, 224) | CONFIRMED | `0x24050008`/`0x24040100`/`0x240300E0` then eight `sh` at offsets 8,2,4,6,0x1C,2,4,6 |
| resident rect at `0x8005DFD4` | CONFIRMED | `sh` to `0x8005DFD4`, `0x8005DFD8`, `0x8005DFD6`, `0x8005DFDA` through `lui $v0,0x8006` |
| called once from BATTLE.PRG as (320,240,H,0,0,0) | CONFIRMED | `0x8008A270 addiu $a0,$zero,0x140` … `0x8008A288 jal 0x800760CC` |
| called once from INITBTL.PRG as (320,240,H,0,0,0) | CONFIRMED | `0x800FA670 addiu $a0,$zero,0x140` … `0x800FA69C jal 0x800760CC` |
| **the BATTLE call site is `0x8008B0A4`** | **REFUTED** | `0x8008B0A4` is `0x012D5024 and $t2,$t1,$t5`, a mask in a CLUT loop. The only call is `0x8008A288` |
| `SetGeomOffset` writes CR24/CR25 only | CONFIRMED | `0x48C4C000`→CR24, `0x48C5C800`→CR25, `jr $ra` |
| `SetGeomScreen` writes CR26 only | CONFIRMED | `0x48C4D000`→CR26, `jr $ra` |
| `kGteControlOfx/Ofy/H = 24/25/26` | CONFIRMED | the register fields of the two cop2 words above |
| `SetDefDispEnv` writes args to +0/+2/+4/+6, zeroes +8..+0xE | CONFIRMED | eight `sh` at offsets `[0,2,4,8,10,12,14,6]` |
| draw-area clip is zero ⇒ drawing area unclipped | CONFIRMED | `SetDefDrawEnv` zero-fills DRAWENV `[12,14,16,18]`; the publication stores nothing there |
| presenter re-states a literal `SetGeomOffset(160,112)` | CONFIRMED | `0x240400A0` / `0x24050070` before `0x800762E4 jal 0x80041540` |
| presenter re-issues the display area every field | CONFIRMED | `0x80076400` `PutDispEnv` inside the presenter |
| `func_80074580` branches on `< 272` | CONFIRMED | `0x80074584 lw $v0,-0x1db8($v0)` then `0x28420110 slti $v0,$v0,0x110` |
| `func_80074744` branches on `> 272` | CONFIRMED | `0x80074750 slti $v0,$v0,0x111`, i.e. `< 273` |
| **a third threshold: zoom +64, clamp 768** | **CONFIRMED, and NEW** | `0x80078584 addiu $v0,$v0,0x40` / `0x28420300 slti $v0,$v0,0x300` |
| `0x8007CCF0` stores to `0x8005E248` then calls `SetGeomScreen` | CONFIRMED | `0xAC44E248 sw $a0,-0x1db8($v0)` / `0x8007CCFC jal 0x80041534` |
| **retail's resting value is `0x100` (256)** | **NOT DETERMINABLE** | 0 of 129,350 scanned BATTLE.PRG words materialise 256 into that word |
| `0x8005DFD6` has one reader, a `LINE_F2` effect, not a cull | CONFIRMED | `0x34420002 ori $v0,$v0,2` (tag `|= 2`) and one `lhu` of the width |

## The refutations, and what they cost

**1. `0x8008B0A4` is not the call site.** `game/render/battle_projection_facts.h` recorded it, and it
is a `and $t2, $t1, $t5`. The real site is `0x8008A288`, found by a `jal` census over BATTLE.PRG's
declared code extent, which returns exactly one. **Cost of the error:** the port had attributed a
viewport publication to a word that computes a palette mask. Nothing consumed it, so nothing was
*broken* — which is exactly why it would never have surfaced as a failure. Corrected to
`kBattlePublicationCallSite` and asserted in the C++ contract.

**2. The 256 is not a clip, and the previous blocker rested on reading it as one.** This is the
substantive one. The previous text said:

> the horizontal clip is published by the overlay from a VRAM layout and a screen rectangle this
> port has not read from bytes

The bytes say something different and more specific:

* `SetDefDispEnv` at `0x8002B434` writes its four arguments to DISPENV `+0/+2/+4/+6` and **zeroes**
  `+8/+0xA/+0xC/+0xE`, so `+0..+6` is the `disp` rect and `+8..+0xE` is the `screen` rect. Both field
  names come from the Psy-Q `libgpu.h` the decomp vendors unmodified.
* The publication installs the **literals** (0, 8, 256, 224) into the `screen` rect of **both**
  dispenvs, at `0x800761B8..0x800761D8` in BATTLE.PRG, `0x80071968..0x80071988` in TITLE.PRG and
  `0x80042090..0x800420A8` in the **resident executable**. Three independently written modules, one
  set of literals.
* `SetDefDrawEnv` at `0x8002B374` writes the **draw-area** clip (DRAWENV `+0xC/+0xE`) as **zero**, and
  the publication never stores there. The drawing area is **unclipped** for the whole field.

So there is no 256-pixel horizontal clip in this title's draw path. **The previous blocker named a
constraint that does not exist.** Leaving the sentence would have left a refuted claim standing as the
port's reason, which is worse than having had no reason: a reader checking the clip would have
concluded the boundary was a measurement when it was a guess about a measurement.

**3. The vertical centre is 128 at the overlay, not 112.** The decompilation elided it as
`SetGeomOffset(arg0 / 2, …)` and the presenter's literal (160, 112) filled the gap. The bytes show
both, and they genuinely disagree: the publication computes `(240-16)/2 + 16 = 128` and the presenter
re-states `(160, 112)` every field. The presenter's is in force at the frame boundary because it runs
last. The previous file asserted the disagreement while naming only one of the numbers; both are now
`kBattlePublicationCentreY` / `kBattlePresenterCentreY` and asserted. `centreY` stays recorded and
never asserted, which is the correct contract.

**4. There is a third gameplay threshold on the projection distance, and it is the dangerous one.**
Issue 0037 recorded 272 from the decompilation. The bytes show `0x8007458C` `< 272` and `0x80074750`
`> 272` — both as claimed — **and** `0x80078578`, where the word grows by **64** and clamps at
**768** (`0x300`). A widening that "just nudged H" would have cleared 272 and hit 768. All three are
now constants and all three are asserted.

**5. The resting value 256 could not be reproduced from bytes, and is not claimed.** No instruction in
BATTLE.PRG materialises 256 into `0x8005E248`. The word is written by the setters, by the +64/clamp
step, and by the ±64 / ±0xC0 steps at `0x800793F8`, so its resting value is whatever the
camera-transition initialiser computed earlier. The tool prints **NOT DETERMINABLE** rather than
borrowing the decompilation's figure, because a number this port cannot derive is not a fact this port
owns. The fog claim (`SetFogNear(768, …)`) rests entirely on the decompilation; `MENU5.PRG` is not one
of the three provisioned overlays, so it was not measured here either.

## The clip derivation, and what it means for widening

**The clip publication is now owned, and the derivation can be complete.** Both halves of the pair are
measured:

| half | where it is stated | when | from bytes |
|---|---|---|---|
| centre | resident `SetGeomOffset` leaf, a literal (160, 112) | every field | confirmed |
| clip | DISPENV `screen` rect, literals (0, 8, 256, 224) | once, then re-`Put` every field | confirmed, in three modules |

`derive()` already refuses anything that is not the pair, and the two refusal tests
(`refusesUnwidenedClip`, `refusesInconsistentClipEdge`) are now backed by a measured clip rather than
an assumed one.

**So why no widening?** Because the pair is not the whole publication. `SetDefDispEnv(disp, 320, 0,
320, 224)` states the **display resolution**, and `PutDispEnv` at `0x80028E80` turns the `disp` rect
into the GPU's display-mode word — `lui $v0, 0x700` at `0x80029328` and `0x05000000` at `0x80028ED0`
are the two coordinate words it sends. Widening therefore means moving the guest's display mode and its
VRAM layout, and that is presentation infrastructure this port has neither measured nor, with S015
absent, can verify. `kUnappliedBoundary` now says that, and the test asserts the string does **not**
contain `screen rect` or `has not read from bytes` and **does** contain `SetDefDispEnv` — the previous
text trips two of those three, so the guard is not vacuous.

**The outcome is unchanged and the reason is stronger.** That is the honest reading: the previous arm's
refusal was right to refuse and wrong about why.

## The frame-rate census

The method is established elsewhere in this workspace and is confirmed here **from the bytes of this
title's own `VSync` at `0x8001F6C4`**: it spins on the vsync counter, then `beq $a0, 1` returns with
**no wait** at `0x8001F824`, `blez $a0` returns the current count at `0x8001F760`, and only `a0 >= 2`
falls through to the field-count wait. So 0 and 1 consume no field and −1 is the query mode.

Census of every `jal 0x8001F6C4`, over 368,826 instruction words in four modules:

| module | −1 | 1 | 2 | 3 | 4 | 10 | unresolved |
|---|---|---|---|---|---|---|---|
| BATTLE.PRG | — | **2** | — | — | — | — | **0** |
| SLUS_010.40 | 21 | — | 1 | 3 | — | 1 | 2 |
| TITLE.PRG | 9 | 1 | 2 | 1 | 1 | — | 13 |
| INITBTL.PRG | — | — | — | — | — | — | 0 |

**57 sites, 42 arguments resolved, 15 unresolved, and all 15 named in the output.** The unresolved ones
are never counted as zero.

**What this supports.** The per-module field-count profile, and one line of it decisively:
**BATTLE.PRG has exactly two `VSync` call sites, both `VSync(1)`, and both resolved — the BATTLE module
never waits a field count through `VSync` at all.** The frame pacing therefore lives in the resident
executable and TITLE.PRG, not in BATTLE.PRG. That is a real result, and it locates the next step.

**What it does not support, and must not be reported as:** a frame rate. A rate is how many fields
elapse per wall-clock second, so it needs the number of these calls on **one control-flow path** per
frame, and a call-site census cannot recover a path. The workspace's recorded lead for this title —
"three `VSync(2)` and two `VSync(3)` sites, which leads to 30 fps" — is **not reproduced here**: the
BATTLE module has neither. That lead came from the decompilation and its `VSync(2)`/`VSync(3)` sites are
not in the three modules that carry this title's frame loop, or are on paths this scan cannot
distinguish. **No rate is claimed, and the interpolation scope question (S011) stays open.**

**Two instrument defects found and fixed while building this**, both recorded because both produced
*confident wrong answers* rather than absent ones:

* A SPECIAL instruction's destination is `rd`, not `rt`. Reading `rt` made every `move $sX, $a0` erase
  what the backward walk had just established, and **43 of 57** sites came back UNRESOLVED while a
  handful came back with the wrong value.
* The walk returned `None` on hitting a control transfer even when it had already found the answer
  **6** words earlier, and it ignored the call's **delay slot**, which is where this title puts the
  argument at `0x8009975C`. Both BATTLE sites now resolve.

The self-test (`--selftest`, 8 checks, 0 failures) pins a mutated image through the identity gate, a
mutated byte through the shipping claim, a zeroed module through the census, and the resolver's
ability to say "not statically known".

## Owner changes

* `game/render/battle_projection_facts.h` — corrected call site; the `screen`-rect reading with the
  three literal sites; `kBattlePublicationCentreY` and the presenter's pair; the third and zoom
  thresholds; the resident-rect store order and why the width is `+2` not `+4`; the GTE register
  numbers with the words that settle them; `kUnappliedBoundary` rewritten to name the display
  resolution, and the provenance header restated as three sources.
* `game/render/battle_projection.h` — the header no longer claims the bodies are unread, and the
  refusal's reason is the corrected one; `centreY`'s contract explains which site governs and why it
  is still only recorded.
* `tests/test_battle_projection.cpp` — asserts the corrected call sites, both vertical centres, all
  three projection-distance thresholds, the `screen` rect, and the boundary's **content**.
* `tools/re_viewport.py` (new) + `CMakeLists.txt` — the byte census and its self-test, registered as
  `vagrant_viewport_bytes` and `vagrant_viewport_bytes_selftest`.

## What remains, stated as remaining

- **S010 is still `missing` and this issue does not widen a frame.** `derive()` is shipped and
  correct; the display resolution it would have to move is not owned.
- **The resting value of `vs_main_projectionDistance` is still not measured.** 256 is not derivable
  from the provisioned modules. A camera-transition initialiser measurement would settle it, and that
  is the one number the 272/768 branches are stated against.
- **The frame rate is still unmeasured**, and S011's interpolation scope stays open. The next step is
  named: BATTLE.PRG's pacing is not in its `VSync` calls, so it is in the resident exe's five
  `a0 >= 2` sites and TITLE.PRG's five, and a control-flow question rather than a call-site one.
- **The display-mode path (`PutDispEnv` → GP0) is read only as far as the two coordinate words.** The
  `disp.w` resolution-class thresholds (281/353/401/561 and 257/289) are measured but not mapped to
  named modes, and that mapping is the first RE step for owning the widening.
- **S015 is unchanged.** There is still no dynarec title adapter, so nothing runs. The owner remains
  reachable without one, which is why it could be verified at all.

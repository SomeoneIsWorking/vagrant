---
id: 38
title: The projection bodies are read from bytes now, and the 256 was not a clip
status: open
symptom: issue 0037 shipped `BattleProjectionOwner` against four SDK leaves whose bodies were a decompilation reconstruction, refused to widen, and named the reason as a 256-pixel screen rectangle this port "has not read from bytes". The image is provisioned now, so the reconstruction could be checked.
tags: S008,S010,S011,S015,widescreen,projection,vsync,decomp,bytes
created: 2026-09-27
updated: 2026-09-29
---

The four leaves' **instruction words** were read out of the SHA-bound images
(`SLUS_010.40` 337,920 bytes, `fababcfd…e48c`; BATTLE.PRG `d53aacc…c72a9`; TITLE.PRG
`f74a76e…b139a`; INITBTL.PRG `d7ea16e…fcc32`), which is a different kind of statement from the two
sources issue 0037 had: those agreed on *which function lives at an address*; this says *what it does*.

The executable's file map is its own PS-X header: `t_addr = 0x80010000`, `t_size = 0x52000`, so text
covers file offsets `0x800..0x52800`. One linear map, file `0x800` ↔ vram `0x80010000`, and the seven
named library entry points decode where that map puts them.

## The claim table: 24 CONFIRMED, 2 REFUTED, 1 NOT DETERMINABLE

- `0x800760CC` is the publication entry in BATTLE.PRG (file `0xD8CC`) — CONFIRMED
  (`addiu $sp,$sp,-0x40`).
- centre X is `arg0/2` — CONFIRMED (`srl`/`addu`/`sra`, then `0x80076124 jal 0x80041540`).
- centre Y: the publication computes `(arg1-16)/2 + 16` = **128**, the presenter re-states a literal
  **112** every field and runs last, so 112 governs at the frame boundary. Both are shipped and
  asserted; `centreY` is recorded, not asserted.
- H is `arg2` — CONFIRMED (`move $s0,$a2`, `jal 0x80041534`).
- two draw areas (`0x8007614C`, `0x80076188`) and two display areas (`0x8007616C`, `0x800761A0`) —
  CONFIRMED.
- the `screen` rects are the literals (0, 8, 256, 224) in BATTLE.PRG `0x800761B8..D8`, TITLE.PRG
  `0x80071968..88` and the resident `0x80042090..A8` — CONFIRMED. Three modules, one set of literals.
- resident rect `0x8005DFD4` gets x=0, y=0, w, h-16; store order is width at **+2**, height at **+4** —
  CONFIRMED.
- called once from BATTLE.PRG as `(320,240,H,0,0,0)` at `0x8008A288` and once from INITBTL.PRG at
  `0x800FA69C` — CONFIRMED.
- **the BATTLE call site is `0x8008B0A4`** — **REFUTED**. `0x8008B0A4` is `and $t2,$t1,$t5`, a mask in a
  CLUT loop. Corrected to `kBattlePublicationCallSite` and asserted.
- **"the draw-area clip is written to zero, so the drawing area is unclipped"** — **REFUTED 2026-09-29**.
  `SetDefDrawEnv` fills `DRAWENV +0x00..+0x06` from its own arguments (`0x8002B3AC/B0/B4`, delay slot
  `0x8002B3DC`) and `+0x0C/+0x0E` is the texture window. The clip is **640 x 224**, two 320-wide halves
  — the two frame buffers, not two halves of a picture. The wrong reading came from `libgpu.h` field
  names read without the struct's offsets: `RECT clip` is at +0, `short ofs[2]` at +8, `RECT tw` at +0xC.
- `SetGeomOffset` writes CR24/CR25 only and `SetGeomScreen` CR26 only — CONFIRMED.
- `0x8005E248`'s thresholds: `< 272` at `0x80074584`, `> 272` at `0x80074750`, **and a third the
  decompilation had not recorded** — zoom grows the word by **64** and clamps at **768** (`0x80078584`,
  `0x28420300`). All three are shipped constants.
- **retail's resting value of the projection word (256)** — **NOT DETERMINABLE**: 0 of 129,350 scanned
  BATTLE.PRG words materialise 256 into it. It is written by the setters and by the camera-transition
  steps, so its resting value is whatever the transition initialiser computed. Not claimed.

## The clip derivation, and why the widening still does not ship

Both halves of the pair are measured:

| half | where it is stated | when |
|---|---|---|
| centre | resident `SetGeomOffset` leaf, literal (160, 112) | every field |
| clip | DRAWENV `clip` rect, literals (0,0,320,224) and (320,0,320,224) at `0x8005E0D0`/`0x8005E12C` | at `0x8008A288`, then re-`Put` every field by the presenter at `0x8007642C` |
| display resolution | DISPENV `screen` rect, literals (0,8,256,224) | once, then re-`Put` every field |

`derive()` refuses anything that is not the pair, and its two clip refusals now rest on a measured
clip rather than an assumed one. **The outcome is unchanged and the reason is stronger**: the previous
arm's refusal was right to refuse and wrong about why. `SetDefDispEnv(disp, 320, 0, 320, 224)` states
the **display resolution**, and `PutDispEnv` at `0x80028E80` turns the `disp` rect into the GPU's
display-mode word. Widening means moving the guest's display mode and its VRAM layout, which is
presentation infrastructure this port has not measured. `kUnappliedBoundary` names `SetDefDispEnv` and
the test asserts the reason string still contains it.

## The frame-rate census, from this title's own `VSync` at `0x8001F6C4`

`beq $a0,1` returns with no wait at `0x8001F824`, `blez $a0` returns the count at `0x8001F760`, and
only `a0 >= 2` falls through to the field-count wait. Census of all 57 `jal 0x8001F6C4` sites over
368,826 words in four modules: **BATTLE.PRG has exactly two sites, both `VSync(1)`**; the resident has
21 `−1` and five `a0 >= 2`; TITLE.PRG has 9 `−1` and five more. 15 arguments remain unresolved and are
never counted as zero. **BATTLE's frame pacing is therefore not in its VSync calls** — it is in the
resident and TITLE paths. A call-site census does not recover a control-flow path, so no rate is
claimed here; issue 0039 settles it from the rate-bearing word instead.

## What remains

- **S010 is still `missing`**; `derive()` is shipped and correct, the display resolution it would have
  to move is not owned.
- **The resting value of the projection word is still unmeasured** — the one number the 272/768
  branches are stated against.
- **The display-mode path (`PutDispEnv` → GP0)** is read only as far as the two coordinate words; the
  `disp.w` resolution-class thresholds (281/353/401/561, 257/289) are measured but not mapped to named
  modes. That mapping is the first RE step for owning the widening.
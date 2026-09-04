# References — the prior art on this binary, and exactly what we may take from it

The workspace-wide survey is `external/psxport/docs/prior-art.md`. This file is what is specific to
Vagrant Story, and the reason this title is in the workspace at all.

**The standing rule governs everything below: where a reference and a MEASUREMENT disagree, the
measurement wins.** A decomp is an excellent source of function boundaries, names and addresses; it is
not evidence about this port.

## `ser-pounce/rood-reverse` — a CC0 MATCHING decompilation of this exact executable

Vendored as `external/rood-reverse` (submodule, pinned; `f3072188` at the time of writing).

| fact | value | how we know |
|---|---|---|
| licence | **CC0-1.0** | `external/rood-reverse/LICENSE` |
| target | SLUS-01040 (USA) — the same image on our disc | measured, below |
| kind | *matching* decomp: its source compiles to byte-identical objects | its own splat/objdiff pipeline + decomp.dev reporting |
| progress | ~55-63% overall per its decomp.dev badges | **NOT measured here.** Its README renders live badges; no number in this file is ours |

CC0 puts it on the same footing as Dusklight and `open-spyro`: **we may take code AND ideas freely**,
citing as a courtesy. That is what makes this title different from every other port in this workspace.

### MEASURED 2026-08-12: the decomp targets OUR bytes, 21 of 21 code images

`tools/verify_decomp_targets.py` extracts each module named by a rood-reverse splat config from our own
disc and compares SHA-1 against the `sha1:` that config states.

```
decomp configs discovered: 21 · matched 21 · mismatched 0 · extract-failed 0
code images on the disc: 22 · covered by a config 21 · NOT covered: ['MENU/MENUA.PRG']
```

- `SLUS_010.40` — `fababcfd4325d42f350d95b3472874affeb0e48c`, 337,920 bytes.
- `BATTLE/BATTLE.PRG`, `BATTLE/INITBTL.PRG`, `ENDING/ENDING.PRG`, `GIM/SCREFF2.PRG`, `TITLE/TITLE.PRG`
  and 15 `MENU/*.PRG` — all matched.
- The one code image with no config is `MENU/MENUA.PRG`, which is **0 bytes** on the disc, so there is
  nothing to decompile. That is the whole of the uncovered set: 21 covered, 1 empty, 22 total.

**What that buys.** The decomp's symbol addresses are OUR addresses with no translation — the same
property that makes `open-spyro` usable in the Spyro port (verified there by the same kind of SHA-1
match). So `external/rood-reverse/config/*/symbol_addrs.txt` (2,299 lines total; 813 for
SLUS_010.40 alone) is a map into the exact executable this repo extracts.

**What it does NOT buy, and this is the part to hold on to.**

1. **Nothing is filled in from it — not one value, including the group that is now filled in.** A
   borrowed address is a HYPOTHESIS until measured against these bytes; the workspace has already
   recorded wrong conclusions from reading an address out of the wrong image. RE-01 is the pattern to
   copy: `tools/re_crt0.py` EXECUTES crt0 on our extracted image and derives all eleven boot-group
   values from what that execution did, and `game/core/game_config.cpp` carries the disassembly line
   behind each one. The decomp's names for the same addresses (`__ra_temp`, `_ramsize`, `_stacksize`,
   `__heapbase`, `__heapsize`, `InitHeap`, `vs_main_exec`, `__SN_ENTRY_POINT`) turned out to agree —
   which is worth something as corroboration and nothing as evidence. Had they disagreed, the
   measurement would have won. RE-03 now applies the same rule to overlays; all other guest-address
   groups in that file remain zero.
2. **A SHA-1 match says nothing about coverage.** It proves the decomp aims at these bytes, not how
   much of them is decompiled — and its percentage is `objdiff` object identity, which is a different
   axis from this port's SBS byte-exact RAM parity. The two numbers are not comparable and neither
   implies the other.
3. **The load bases in its splat configs are not evidence by themselves.** They read:
   `0x80068800` for BATTLE/TITLE/ENDING, `0x800F9800` for INITBTL/SCREFF2/MAINMENU, `0x80102800` for
   the other non-empty MENU modules — three shared slots. RE-03 is now measured without treating those
   values as the source: `tools/re_overlay.py` M2 derives all 20 bases from each owned module's own
   absolute `jal` targets and entry offsets; M3 then requires that owned image's SHA-1 to match the
   corresponding config before comparing its independently stated `vram`. Result: 20/20 identity and
   address agreements, zero undecided/missing/extra. The three values also appear in four contiguous
   resident words at `0x80010000..0x8001000C`. This closes the static mapping and gates the shipped
   seed/config copies; observing a running loader still awaits a substrate.

### Why a matching decomp matters to the hybrid

The matching decomp is readable evidence for naming state and selecting cohesive native overrides.
It does not execute in the product and does not replace comparison against the authenticated retail
image. Ordinary guest instructions stay in psxport's dynarec; a native owner must still have an exact
guest address, ABI/state contract, scoped activation, and differential evidence against the ordinary
dynarec path. `RE-07` establishes the first such semantic body for `vs_main_initHeap`; registration
waits for the image-scoped adapter tracked by S015.

### Keeping the pin honest

`tools/verify_decomp_targets.py` is the check to re-run whenever the submodule pin moves; its
`--selftest` proves the comparator can actually report a mismatch (it replaces one expected hash with
40 zeros and requires exactly one MISMATCH and exit 1 — verified 2026-08-12). We do not build the
decomp here and do not depend on its toolchain; it is a read-only reference tree.

## Other material

- **Data Crystal's Vagrant Story page** — format/RAM notes; the decomp's README credits it. Unverified
  here; treat any address from it exactly like one from the decomp.
- **decomp.dev** lists this project among ~150 matching decomps (Vagrant Story ~62.63% when the
  workspace survey was written). psxport itself cannot report there — our axis is RAM parity, not
  object identity — see `external/psxport/docs/prior-art.md`.

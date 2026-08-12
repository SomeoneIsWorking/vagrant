# RE Frontier — the ordered RE dependency chain toward a faithful port

Tracked by `tools/re_frontier.py` (a shim onto `external/psxport/tools/port/re_frontier.py` — consult
it FIRST; update it in the SAME commit that changes a step). This is the fine-grained companion to
`docs/codemap.md`: the codemap says *what subsystem exists*, this says *which ordered RE step is real
reverse-engineering vs a hack that jumped ahead*.

**Hard rule (no hacks / no fallbacks):** a `⛔ hack` status is DEBT, never an acceptable resting
state. It marks a shortcut standing in for absent RE and MUST be removed as its real mechanism lands.
`re_frontier.py hacks` is the debt list; `re_frontier.py next` tells you the next RE-ready step.

**`re-verified` MEANS FAITHFUL to the real target — not "the mechanism runs."** A step is
`re-verified` only when its OUTPUT matches the real game/binary on real data. An internal trace is a
mechanism check, NOT faithfulness.

**Fail fast & loud:** a failure must surface loudly, never silently fall back — unless the fallback IS
intended behaviour of the real target being reproduced.

Statuses: ✅ re-verified · 🟡 re-partial (honest gap) · 🔬 in-progress · ⛔ hack (debt, must remove) ·
⬜ todo · ➖ skip-by-design · ⏸ blocked (computed).

## THE STATE OF THIS PORT, 2026-08-12: NOTHING IS RE'd. The repo is scaffolding

Every entry below is `todo` or `blocked`. That is not modesty — it is the whole state of the port.
There is no recompiled substrate, no `GameConfig` value except this game's own env-var name, and no
native body. `game/core/game_config.cpp` is all zeros with TODOs pointing back here, and that is the
honest value: a plausible-looking wrong address breaks boot in a way that reads as a framework bug.

**The one thing that IS measured is the SUPPLY, not the port** — see `docs/references.md`. A CC0
matching decompilation (rood-reverse) targets byte-identical copies of all 21 code images on this
disc, verified 21/21 by `tools/verify_decomp_targets.py`. That changes where RE labour comes from; it
does not fill a single field on its own, because a borrowed address is a REFERENCE until this repo
measures it against this executable.

## boot

### RE-01 — crt0 / boot layout: the GameConfig boot group for SLUS_010.40
- status: todo
- deps:
- evidence: PS-EXE header, read by `tools/extract_exe.py`: entry pc0 = 0x8001F544, text 0x80010000 + 0x52000, initial sp 0x801FFFF0, gp0 = 0 (so gp is set by crt0, not by the header). SYSTEM.CNF: `BOOT = cdrom:\SLUS_010.40;1`, `STACK = 801fff00`, `TCB = 4`, `EVENT = 16`.
- where: game/core/game_config.cpp (bssZeroLo/Hi, stackTopBase/2, heapBase, heapSizePtr, heapBasePtr, gp, libcInit, gameMain, crt0)
- gap: The entry PC is the only value MEASURED so far, and it is not yet written into GameConfig because the framework's crt0_setup consumes the whole group — a lone entry PC with a zeroed BSS range would run a wrong crt0 rather than fail. Needs the entry disassembled (Ghidra via external/psxport/tools/decomp.sh, or the decomp's own symbol_addrs.txt as a starting HYPOTHESIS to confirm).
- notes: rood-reverse names 813 symbols in SLUS_010.40 (config/SLUS_010.40/symbol_addrs.txt). Use it to LOCATE, then confirm against the bytes here; the standing rule is that where a reference and a measurement disagree, the measurement wins.

### RE-02 — recompiler seed set for SLUS_010.40
- status: todo
- deps: RE-01
- evidence:
- where: game/recomp_seeds.json
- gap: Seeds are grown EMPIRICALLY from `[recomp-MISS] 0x800xxxxx` fail-fasts on a booting port, each with the rationale for how the address is reached. There is no booting port yet, so the file holds no addresses. Never copy another game's seeds.
- notes:

## overlays

### RE-03 — load base for each of the 21 .PRG code modules
- status: todo
- deps:
- evidence: Disc listing (`tools/discdump.py`): 21 `.PRG` files, 4 distinct sizes of role — BATTLE/BATTLE.PRG 577828 B, TITLE/TITLE.PRG 554568 B, ENDING/ENDING.PRG 473628 B, BATTLE/INITBTL.PRG 7036 B, GIM/SCREFF2.PRG 2324 B, and 16 MENU/*.PRG (one of which, MENUA.PRG, is 0 bytes).
- where: game/recomp_seeds.json (overlay_bases / overlay_base_patterns)
- gap: NOT MEASURED HERE. rood-reverse's splat configs state a `vram:` per module — 0x80068800 for BATTLE/TITLE/ENDING, 0x800F9800 for INITBTL/SCREFF2/MAINMENU, 0x80102800 for the other MENU modules — which is a strong HYPOTHESIS and is *not* evidence about this port. An overlay is keyed BY its load address: a wrong base emits a whole module of correctly-decoded instructions at wrong addresses. Confirm by observing the loader (`PSXPORT_DEBUG=cd` on a booting port), or by disassembling the loader call site, before any of it reaches a seed file.
- notes: Three shared slots for 21 modules is the `overlay_base_patterns` shape, not one base per module — but that reading, too, is the reference's, not a measurement.

## cd

### RE-04 — CD load chokepoints and the loader's contract
- status: todo
- deps: RE-01
- evidence:
- where: game/core/game_config.cpp (cdInit, cdCommand, cdSync, cdReadPrim, cdFileLoad, cdAsyncRead, …)
- gap: Nothing located. The splat config shows the executable links stock Sony libcd (`libcd/SYS`, `libcd/BIOS`, `libcd/C_011` .rodata subsegments), so the framework's stock-libcd chokepoint set is the likely shape — again a hypothesis about which entry points exist, not their addresses in this image.
- notes: This game streams from the disc heavily (ENDING/ENDING.XA alone is 68 MB, plus MOV/, MUSIC/, SE/), so the CD path is unusually load-bearing here compared with the other ports in this workspace.

## frame

### RE-05 — per-frame OT / packet-pool layout
- status: todo
- deps: RE-01
- evidence:
- where: game/core/game_config.cpp (otRegionBase/Stride, packetPoolBase/Stride, otBasePtr, poolPtrCur/Last, clearOtagR, putDrawEnv, drawSync)
- gap: Nothing located. Until this lands the port cannot use the framework's native frame loop; the Phase-0 shape is the guest's own loop on the substrate.
- notes:

### RE-06 — pad driver buffers
- status: todo
- deps: RE-01
- evidence:
- where: game/core/game_config.cpp (padSlot0Buf, padSlot1Buf, padDriverFn, padSlotPtrTable, padSlotPtrStride)
- gap: Nothing located. The splat config shows `libpad/PADENTRY` linked, so it is libpad rather than a custom SIO driver — which says which SHAPE to look for, not where.
- notes:

## ownership

### RE-07 — native ownership seeded from the matching decomp
- status: todo
- deps: RE-01, RE-02
- evidence:
- where: game/ (no native body exists yet)
- gap: This is the step this title exists to test: psxport's override registry wants (addr, native, gen) triples whose native body byte-matches the substrate body, and a matching decomp is a pre-verified supply of exactly that. Blocked on there being a substrate to match AGAINST. Nothing may be imported before then — an imported body with no byte-gate is a hack with a citation.
- notes: rood-reverse is ~55-63% matched overall (its own decomp.dev badges; not measured here — and the psxport port's axis is SBS RAM parity, not object identity, so the two percentages are not comparable).

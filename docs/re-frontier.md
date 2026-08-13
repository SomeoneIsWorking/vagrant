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

## THE STATE OF THIS PORT, 2026-08-12: ONE step of eight is real. The rest is scaffolding

`RE-01` (the crt0/boot group) is `re-verified` — measured out of the executable's own bytes, not copied
from the vendored decomp; see its evidence block below, claim `C004`, and `tools/re_crt0.py`. **Every
other entry is `todo` or `blocked`**, there is still no recompiled substrate and no native body, and
every `GameConfig` group except the boot group is still zero with a TODO pointing back here. That is
the honest value: a plausible-looking wrong address breaks boot in a way that reads as a framework bug.

Do not read a green RE-01 as "boot works". Nothing has EXECUTED those eleven addresses — there is no
substrate to execute them on. The framework defect found while measuring them (issue #3: `crt0_setup`
formerly omitted `a1`, so this game's BIOS `InitHeap` would have built a zero-size heap) is fixed in
the shared framework; the missing port substrate remains the blocker.

**The one thing that IS measured is the SUPPLY, not the port** — see `docs/references.md`. A CC0
matching decompilation (rood-reverse) targets byte-identical copies of all 21 code images on this
disc, verified 21/21 by `tools/verify_decomp_targets.py`. That changes where RE labour comes from; it
does not fill a single field on its own, because a borrowed address is a REFERENCE until this repo
measures it against this executable.

## boot

### RE-01 — crt0 / boot layout: the GameConfig boot group for SLUS_010.40
- status: re-verified
- deps:
- evidence: MEASURED 2026-08-12 by EXECUTING crt0 on the extracted SLUS_010.40 (sha1 fababcfd4325d42f350d95b3472874affeb0e48c), not by reading a reference: `python3 tools/re_crt0.py` interprets from the PS-EXE header's own entry PC to crt0's second call (52,051 instructions) and reports every store, load and call, each with its disassembly line. Boot group: bssZeroLo=0x80033678 bssZeroHi=0x800401A8 (the clear loop's own footprint — 13,004 word stores) · stackTopBase=0x80049138 (_ramsize=0x00200000) stackTopBase2=0x8004913C (_stacksize=0x00004000) · heapBase=0x800401A8 · heapSizePtr=0x80030FB8 (crt0 writes 0x001BBE50) heapBasePtr=0x80030FB4 · gp=0x80033674 · libcInit=0x80026864 (a BIOS A0:0x39 InitHeap thunk, not a linked routine) · gameMain=0x80042C38 (rood-reverse: vs_main_exec; a `break` follows the jal, so main never returns) · crt0=0x8001F544. Derived: sp=fp=0x801FFFF8, which is NEITHER the header s_addr (0x801FFFF0) NOR SYSTEM.CNF STACK (0x801FFF00) — crt0 computes it from _ramsize. Independent cross-checks: (a) the header has b_addr=b_size=0 so no declared .bss exists and the loop is the ONLY source for the range; (b) [0x80033678,0x800401A8) is 52,016 bytes and all-zero in the loaded image while the 120 bytes immediately below hold 44 non-zero bytes, so the low bound is a real boundary rather than an arbitrary address; (c) THE SN LINKER'S OWN RECORD, kept as initialised data at 0x80030FBC by the SN startup object and therefore independent of crt0's instruction stream, gives __text 0x80010AA4+0x1EA90 -> 0x8002F534 = __data, __data+0x4140 -> 0x80033674 = the measured gp, and __bss 0x80033680+0xCB28 -> 0x800401A8 = the measured bssZeroHi — a genuinely second source for two of the eleven values, asserted by the tool; (d) rood-reverse's independent symbol names agree as labels (__ra_temp, _ramsize, _stacksize, __heapbase, __heapsize, InitHeap, __SN_ENTRY_POINT). Gates, REBUILT 2026-08-12 after the shipped values turned out to be unchecked: `re_crt0.py --check-config` parses game/core/game_config.cpp's eleven kXxx constants AND the designated initialisers that bind them to GameConfig fields and DIFFS THEM AGAINST THE MEASUREMENT, and `--gate-citations` regenerates the file's disassembly block from the bytes and fails on any difference. The tool no longer keeps a copy of the answer (its FIXTURE_EXPECT table is deleted) — the shipping file is the fixture, which is what workspace PROTOCOL.md's "THE SHIPPED VALUE MUST BE COMPARED TO THE MEASURED ONE" requires. `re_crt0.py --selftest` = 22 assertions, 0 failed, of which 13 are negatives: 6 corpus/binary mutations that must REFUSE (nopped clear loop, unknown opcode, entry that returns, broken header magic, entry outside text, missing file) and 7 hand-edits of the SHIPPING FILE that must be REPORTED (kHeapSizePtr +4, kLibcInit -> a real nop, a right-valued constant bound to the wrong field, a deleted constant, a retyped citation word, a deleted citation line, the whole block removed). `re_crt0.py --gate-config` compiles game_config.cpp pristine (must pass) and with 5 plausible mutations (each must fail a named static_assert) = 6/6. SABOTAGE-PROVEN the same day on the real file, not just in the selftest: kHeapSizePtr->0x80030FBC + kLibcInit->0x8001F564 made --check-config exit 1 naming both ("SHIPPED 0x80030FBC (via kHeapSizePtr) != MEASURED 0x80030FB8"); retyping 0x8001F548's word to 24427836 made --gate-citations exit 1 naming line 71; both green again on restore.
- where: game/core/game_config.cpp (crt0/boot group, all 11 fields; a GENERATED disassembly citation block; 6 static_asserts over the relations the measurement established — kept, but NOT the shipped-vs-measured check, since `hi - lo == 0x46B20` holds just as well when both values are wrong) + tools/re_crt0.py (the instrument AND the shipped-vs-measured gate)
- gap: **CORRECTED 2026-08-12 — this field said "NONE for the crt0 group itself" and that was not earned.** The eleven VALUES stand (and are now gated against the bytes, and gp/bssZeroHi have gained the independent SN-link-record witness), but three real gaps were being hidden by that word:
  (1) **NOTHING HAS EVER EXECUTED THIS BOOT GROUP.** There is no recompiled substrate and no port binary, so "re-verified" here means "these are what crt0 does to this image", NOT "the port boots with them". That distinction was in CLAUDE.md but not in this field.
  (2) **THE HEAP CRT0 DECLARES IS NOT FREE RAM, and an earlier reading of it was wrong.** The static_assert kHeapBase == kBssZeroHi carried the rationale "the heap starts where .bss ends", which reads as "the heap is free memory". Measured: this executable concatenates THREE separately-linked segments, 0x800401A8 is the end of the FIRST one's .bss (confirmed by the SN link record, which describes only 0x80010AA4..0x800401A8), and the arena [0x800401AC,0x801FBFFC) overlaps the loaded image over [0x800401AC,0x80062000) = 138,836 bytes of which 45,761 are non-zero — including gameMain 0x80042C38 and the _ramsize/_stacksize globals themselves. Resolved, not left dangling: the BIOS heap is NEVER allocated from (census over the whole image — 2,023 jal sites vs 19 BIOS A0 thunks — finds no malloc/free/calloc/realloc thunk present at all, and InitHeap's only caller is crt0 at 0x8001F5CC; the game uses its own vs_main_initHeap 0x80043F74 with an arena at 0x8010C000+0xF2000, above the image). So the overlap is inert stock-crt0 boilerplate, on real hardware as here — but the CONSEQUENCE is a gap: this game cannot demonstrate psxport's BIOS heap working or broken, which downgrades issue #3 from "live defect here" to "faithfulness defect, latent here". Asserted by --selftest so it cannot quietly stop being true.
  (3) the platform HLE windows (.hle) were retagged out of RE-01 to the new RE-08 — leaving them here would have made a done RE-01 imply a done HLE.
  (4) gp has no independent confirmation *in code*: measured over the 83,968-word (335,872-byte) loaded image, there are ZERO gp-relative load/stores in code — 5 candidate encodings exist in the whole image and all 5 are inside DATA (four in a byte ramp in segment 2's libgte .rodata at 0x80040B08..0x80040B20, one at 0x8002FB34 in segment 1's .data). An earlier note said "4 candidate encodings, all 4 inside byte-ramp DATA tables" — remeasured, it is 5 and one of them is not in a byte ramp; the conclusion is unchanged. What HAS changed is that gp is no longer witnessed only by crt0's lui/addiu pair: the SN link record's __data+__datalen == 0x80033674 independently agrees.
- notes: FRAMEWORK DEFECT found while measuring this step, recorded in docs/issues/0003: the old `crt0_setup` supplied `a0` but omitted `a1` when dispatching libcInit. Here libcInit is BIOS A0:0x39 InitHeap and psxport's own HLE implements it as heapInit(a0,a1) (runtime/recomp/hle.cpp:355), so the arena would have been created with size 0. The guest crt0 provably passes the size in a1 (0x8001F5A0 subu $a1,$a1,$a0 -> 0x001BBE50, live into the jal at 0x8001F5CC). **Fixed upstream 2026-08-12:** the shared `crt0_apply` now writes `w.reg(5, p.a1)` beside `a0`, and `tests/test_crt0_boot_group.cpp` catches its removal. SEVERITY CORRECTED 2026-08-12: it was recorded as making "every heapAlloc return 0" for THIS game, which overstated it — nothing in this image can call BIOS malloc (gap (2) above has the census), so here the wrong-size arena was inert. ALSO CORRECTED: the 22-line disassembly block in game_config.cpp was RETYPED, not pasted — three of its raw words did not match the executable (0x8001F548 read 24427836 for a real 24423678, 0x8001F588/8C read 002420c0/002420c2 for real 000420c0/000420c2) while being presented as the audit trail CLAUDE.md rule 1 requires. It is now GENERATED by `re_crt0.py --emit-citations` and gated by `--gate-citations`; a retyped word cannot survive.

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

## platform


### RE-08 — platform HLE windows: the hardware-sync primitives GameConfig.hle installs into
- status: todo
- deps: RE-01
- evidence: Nothing measured. Split OUT of RE-01 on 2026-08-12 when RE-01's crt0 group became re-verified: game_config.cpp's .hle group was tagged RE-01 but is not consumed by crt0_setup, so leaving it there would have made a done RE-01 imply a done HLE.
- where: game/core/game_config.cpp (.hle = {})
- gap: ZERO means 'install nothing', which is the honest state: initBuiltins() registers no handler and says so, and a run that needs one hangs in the guest's real spin loop. The windows are zero too, so register_() refuses everything — this game has not stated its memory map, and a window guessed from another game's map is how a handler lands on an unrelated function. What IS known from RE-01: the executable reaches the BIOS through tail-jump thunks (libcInit 0x80026864 = 'addiu $t2,$zero,0xa0 / jr $t2 / addiu $t1,$zero,0x39'), and there are two more such thunks immediately after it (t1=0x44, t1=0x70), so a thunk TABLE exists around 0x80026864 and is the place to start.
- notes: Needs a booting substrate to observe which spin primitives are actually reached; do not pre-populate from another port's window list.

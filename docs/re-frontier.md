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

## THE STATE OF THIS PORT, 2026-08-21: resident VBlank works; asynchronous CD is next

`RE-01` (crt0/boot), `RE-02` (resident seed set/substrate), and `RE-03` (all non-empty `.PRG` load
bases) are `re-verified`. The emitter's mandatory PS-EXE entry root plus one measured Sony
`HookEntryInt` return PC expand from 261 discovered seeds to 744 resident functions. `main` remains
empty; `main_reentry` contains only `0x8001FAD0`. The built port executes the measured
crt0 plan, handles InitHeap, enters guest main at `0x80042C38`, and, against pinned psxport
`9f1bb927`, completes `_initRand`. RE-04 now owns blocking `DsControlB` at `0x80025BE4`; a bounded run completes
`_diskReset`'s Pause and Setmode. RE-09 now supplies the measured libapi DMA callback table: the real
run dispatches `0x8001DE94` from DMA4 slot `0x80032138` and clears the old `0x8001355C` SPU wait.
RE-10 now preserves Sony's resident VBlank semantics: the host schedules display fields at the
selected video standard, while intact guest handler `0x8001FFEC` increments counter `0x80032114` and
dispatches the eight-entry callback table. The real run returns from `VSync`, configures the GPU
standard, then enters `_loadMenuSound`'s first asynchronous `vs_main_diskLoadFile`. The watchdog stack
is that file-read polling loop calling `vs_main_gametimeUpdate -> VSync`; it is not evidence of a
failed field clock or reached frame loop. There is neither a recompilation miss
nor an unimplemented-BIOS fatal, and there is no gameplay claim.

The resident substrate now executes the RE-01 plan through guest main. That does not mean gameplay
boots: platform HLE and CD/overlay loading remain later frontier steps. The earlier fail-fast at the
unimplemented `rand` leaf exposed a generic framework gap; psxport `be03593f` resolves it without a
Vagrant seed or generated-code change.

**The one thing that IS measured is the SUPPLY, not the port** — see `docs/references.md`. A CC0
matching decompilation (rood-reverse) targets byte-identical copies of all 21 code images on this
disc, verified 21/21 by `tools/verify_decomp_targets.py`. That changes where RE labour comes from; it
does not fill a single field on its own, because a borrowed address is a REFERENCE until this repo
measures it against this executable.

## boot

### RE-01 — crt0 / boot layout: the GameConfig boot group for SLUS_010.40
- status: re-verified
- deps:
- evidence: MEASURED 2026-08-12 by EXECUTING crt0 on the extracted SLUS_010.40 (sha1 fababcfd4325d42f350d95b3472874affeb0e48c), not by reading a reference: `python3 tools/re_crt0.py` interprets from the PS-EXE header's own entry PC to crt0's second call (52,051 instructions) and reports every store, load and call, each with its disassembly line. Boot group: bssZeroLo=0x80033678 bssZeroHi=0x800401A8 (the clear loop's own footprint — 13,004 word stores) · stackTopBase=0x80049138 (_ramsize=0x00200000) stackTopBase2=0x8004913C (_stacksize=0x00004000) · heapBase=0x800401A8 · heapSizePtr=0x80030FB8 (crt0 writes 0x001BBE50) heapBasePtr=0x80030FB4 · gp=0x80033674 · libcInit=0x80026864 (a BIOS A0:0x39 InitHeap thunk, not a linked routine) · gameMain=0x80042C38 (rood-reverse: vs_main_exec; a `break` follows the jal, so main never returns) · crt0=0x8001F544. Derived: sp=fp=0x801FFFF8, which is NEITHER the header s_addr (0x801FFFF0) NOR SYSTEM.CNF STACK (0x801FFF00) — crt0 computes it from _ramsize. Independent cross-checks: (a) the header has b_addr=b_size=0 so no declared .bss exists and the loop is the ONLY source for the range; (b) [0x80033678,0x800401A8) is 52,016 bytes and all-zero in the loaded image while the 120 bytes immediately below hold 44 non-zero bytes, so the low bound is a real boundary rather than an arbitrary address; (c) THE SN LINKER'S OWN RECORD, kept as initialised data at 0x80030FBC by the SN startup object and therefore independent of crt0's instruction stream, gives __text 0x80010AA4+0x1EA90 -> 0x8002F534 = __data, __data+0x4140 -> 0x80033674 = the measured gp, and __bss 0x80033680+0xCB28 -> 0x800401A8 = the measured bssZeroHi — a genuinely second source for two of the eleven values, asserted by the tool; (d) rood-reverse's independent symbol names agree as labels (__ra_temp, _ramsize, _stacksize, __heapbase, __heapsize, InitHeap, __SN_ENTRY_POINT). Gates, REBUILT 2026-08-12 after the shipped values turned out to be unchecked: `re_crt0.py --check-config` parses game/core/game_config.cpp's eleven kXxx constants AND the designated initialisers that bind them to GameConfig fields and DIFFS THEM AGAINST THE MEASUREMENT, and `--gate-citations` regenerates the file's disassembly block from the bytes and fails on any difference. The tool no longer keeps a copy of the answer (its FIXTURE_EXPECT table is deleted) — the shipping file is the fixture, which is what workspace PROTOCOL.md's "THE SHIPPED VALUE MUST BE COMPARED TO THE MEASURED ONE" requires. `re_crt0.py --selftest` = 24 assertions, 0 failed, of which 15 are negatives: 6 corpus/binary mutations that must REFUSE (nopped clear loop, unknown opcode, entry that returns, broken header magic, entry outside text, missing file) and 9 hand-edits of the SHIPPING FILE that must be REPORTED (kHeapSizePtr +4, kLibcInit -> a real nop, a right-valued constant bound to the wrong field, a deleted constant, a retyped citation word, a deleted citation line, the whole block removed). `re_crt0.py --gate-config` compiles game_config.cpp pristine (must pass) and with 5 plausible mutations (each must fail a named static_assert) = 6/6. SABOTAGE-PROVEN the same day on the real file, not just in the selftest: kHeapSizePtr->0x80030FBC + kLibcInit->0x8001F564 made --check-config exit 1 naming both ("SHIPPED 0x80030FBC (via kHeapSizePtr) != MEASURED 0x80030FB8"); retyping 0x8001F548's word to 24427836 made --gate-citations exit 1 naming line 71; both green again on restore.
- where: game/core/game_config.cpp (crt0/boot group, all 11 fields; a GENERATED disassembly citation block; 6 static_asserts over the relations the measurement established — kept, but NOT the shipped-vs-measured check, since `hi - lo == 0x46B20` holds just as well when both values are wrong) + tools/re_crt0.py (the instrument AND the shipped-vs-measured gate)
- gap: **CORRECTED 2026-08-12 — this field said "NONE for the crt0 group itself" and that was not earned.** The eleven VALUES stand (and are now gated against the bytes, and gp/bssZeroHi have gained the independent SN-link-record witness), but three real gaps were being hidden by that word:
  (1) RE-02 now executes this boot group through guest main. This verifies the boot application path,
  but does not broaden RE-01 into a gameplay claim.
  (2) **THE HEAP CRT0 DECLARES IS NOT FREE RAM, and an earlier reading of it was wrong.** The static_assert kHeapBase == kBssZeroHi carried the rationale "the heap starts where .bss ends", which reads as "the heap is free memory". Measured: this executable concatenates THREE separately-linked segments, 0x800401A8 is the end of the FIRST one's .bss (confirmed by the SN link record, which describes only 0x80010AA4..0x800401A8), and the arena [0x800401AC,0x801FBFFC) overlaps the loaded image over [0x800401AC,0x80062000) = 138,836 bytes of which 45,761 are non-zero — including gameMain 0x80042C38 and the _ramsize/_stacksize globals themselves. Resolved, not left dangling: the BIOS heap is NEVER allocated from (census over the whole image — 2,023 jal sites vs 19 BIOS A0 thunks — finds no malloc/free/calloc/realloc thunk present at all, and InitHeap's only caller is crt0 at 0x8001F5CC; the game uses its own vs_main_initHeap 0x80043F74 with an arena at 0x8010C000+0xF2000, above the image). So the overlap is inert stock-crt0 boilerplate, on real hardware as here — but the CONSEQUENCE is a gap: this game cannot demonstrate psxport's BIOS heap working or broken, which downgrades issue #3 from "live defect here" to "faithfulness defect, latent here". Asserted by --selftest so it cannot quietly stop being true.
  (3) the platform HLE windows (.hle) were retagged out of RE-01 to the new RE-08 — leaving them here would have made a done RE-01 imply a done HLE.
  (4) gp has no independent confirmation *in code*: measured over the 83,968-word (335,872-byte) loaded image, there are ZERO gp-relative load/stores in code — 5 candidate encodings exist in the whole image and all 5 are inside DATA (four in a byte ramp in segment 2's libgte .rodata at 0x80040B08..0x80040B20, one at 0x8002FB34 in segment 1's .data). An earlier note said "4 candidate encodings, all 4 inside byte-ramp DATA tables" — remeasured, it is 5 and one of them is not in a byte ramp; the conclusion is unchanged. What HAS changed is that gp is no longer witnessed only by crt0's lui/addiu pair: the SN link record's __data+__datalen == 0x80033674 independently agrees.
- notes: FRAMEWORK DEFECT found while measuring this step, recorded in docs/issues/0003: the old `crt0_setup` supplied `a0` but omitted `a1` when dispatching libcInit. Here libcInit is BIOS A0:0x39 InitHeap and psxport's own HLE implements it as heapInit(a0,a1) (runtime/recomp/hle.cpp:355), so the arena would have been created with size 0. The guest crt0 provably passes the size in a1 (0x8001F5A0 subu $a1,$a1,$a0 -> 0x001BBE50, live into the jal at 0x8001F5CC). **Fixed upstream 2026-08-12:** the shared `crt0_apply` now writes `w.reg(5, p.a1)` beside `a0`, and `tests/test_crt0_boot_group.cpp` catches its removal. SEVERITY CORRECTED 2026-08-12: it was recorded as making "every heapAlloc return 0" for THIS game, which overstated it — nothing in this image can call BIOS malloc (gap (2) above has the census), so here the wrong-size arena was inert. ALSO CORRECTED: the 22-line disassembly block in game_config.cpp was RETYPED, not pasted — three of its raw words did not match the executable (0x8001F548 read 24427836 for a real 24423678, 0x8001F588/8C read 002420c0/002420c2 for real 000420c0/000420c2) while being presented as the audit trail CLAUDE.md rule 1 requires. It is now GENERATED by `re_crt0.py --emit-citations` and gated by `--gate-citations`; a retyped word cannot survive.

### RE-02 — recompiler seed set for SLUS_010.40
- status: re-verified
- deps: RE-01
- evidence: The framework emitter was run on the owned, SHA-verified SLUS_010.40 with this game's seed file and no overlay directory. Its root contract is `{exe.entry} | explicit main seeds | explicit main_reentry seeds | pointer/table discoveries`; the measured PS-EXE entry is `0x8001F544`. Natural `main` seeds remain empty. Correct HookEntryInt delivery exposed a genuine mid-function miss at `0x8001FAD0`: `tools/re_vblank.py` derives Sony libetc owner `0x8001FA68`, its `setjmp` call at `0x8001FAC8`, buffer `0x80031084`, saved return PC `0x8001FAD0`, and HookEntryInt call at `0x8001FAF0`. The missing-seed negative `scratch/logs/re05-reentry.log` fails exactly there. With that one `main_reentry`, the emitter reports `261 seeds -> 744 recompiled after jal discovery` and generates both `gen_func_8001FAD0` and its dispatcher case; `scratch/logs/re05-final-irq-dma.log` executes it without a recompilation miss. This falsifies C007's older empty-both-lists claim. The earlier `recMainLo/Hi=0` failure remains a separately proven routing-range defect, removed by configuring the PS-EXE physical text range `[0x00010000,0x00062000)` rather than adding a seed.
- where: game/recomp_seeds.json (empty natural main list plus one measured main_reentry) + tools/re_vblank.py (saved-PC instrument/gate) + game/core/game_config.cpp (physical main routing range) + game/core/recomp_register.cpp (generated registry) + generated/ (gitignored emitter output)
- gap: This is the verified resident bootstrap frontier, not a gameplay claim. Overlay modules are not in this smallest substrate. Blocking `_diskReset`, boot SPU DMA completion, and resident VBlank waits now advance; RE-04's asynchronous read/ready-callback path is the next runtime prerequisite. RE-05 has measured the later overlay-owned presenter contract without claiming it executes. Future `[recomp-MISS]` failures may extend the explicit lists only with their runtime rationale.
- notes: Reproduce from a provisioned executable with `mkdir -p generated && PSXPORT_SHARDS=8 python3 "${PSXPORT_DIR:-external/psxport}/tools/recomp/emit.py" scratch/bin/vagrant/SLUS_010.40 generated/recompiled.c --seeds game/recomp_seeds.json`, then configure/build normally. Generated code remains gitignored and must never be edited.

## overlays

### RE-03 — load base for each of the 21 .PRG images
- status: re-verified
- deps:
- evidence: MEASURED 2026-08-14 by `tools/re_overlay.py` on the owned disc: 22 code-image directory entries = boot executable + 21 `.PRG`; `MENU/MENUA.PRG` is exactly 0 bytes and therefore has no code/base; all 20 non-empty `.PRG` images are verified. M2 independently derives placement from each image's own absolute `jal` targets × non-leaf function-entry offsets: BATTLE/TITLE/ENDING = `0x80068800`; INITBTL/SCREFF2/MAINMENU = `0x800F9800`; MENU0-5,7-9,B-F = `0x80102800`. Margins are printed per image (minimum accepted: MENU1 and SCREFF2, 2.00x; maximum: TITLE, 12.71x), with zero undecided. M3 parses each rood-reverse PRG config, first requires OUR extracted image's SHA-1 to equal that config's SHA-1, then compares M2's answer with its independent `vram`: 20 checked, 20 identity matches, 20 address agreements, 0 missing/mismatch/extra. Resident executable M1 independently finds all three values in four contiguous words at `0x80010000..0x8001000C`, though only 1/14 candidate call sites yields a disc descriptor; the other 13 are reported as unresolved rather than used to name files. `--selftest`: 7/7 PASS, 0 SKIP — PS-EXE-header truth, shifted-image answer moves by -4, destroyed entries refuse, one-byte image mutation fails SHA before address, +4 reference-vram mutation fails address after SHA, bad LBA rejected/good accepted, and +4 shipping slot plus +4 BATTLE seed are both named by `--check-config`. `--check-config`: 24/24, comparing the three shipped `GameConfig` slots plus all 20 explicit seed mappings back to this measurement.
- where: tools/re_overlay.py (instrument and shipping gate) + game/recomp_seeds.json (20 explicit overlay_bases) + game/core/game_config.cpp (3 overlaySlots)
- gap: The mappings are complete. The resident substrate stalls in an earlier asynchronous sound-data read before an overlay loader is observed; runtime rewriting is outside this static instrument's reach. That is a runtime integration gap, not an unmeasured module/base.
- notes: Three slots serve 20 non-empty modules; the twenty-first `.PRG`, MENUA, is 0 bytes and correctly absent from the seed map. M1's 13 unresolved candidate sites remain explicit coverage limits and are not inputs to the per-file verdict.

## cd

### RE-04 — CD load chokepoints and the loader's contract
- status: re-partial
- deps: RE-01
- evidence: `tools/re_cd.py` scans the owned SHA-verified PS-EXE and uniquely derives `_diskReset 0x80044A60 -> DsControlB 0x80025BE4 -> DsCommand 0x80023B34 / DsSync 0x8002411C`, plus the low-level `CD_cw 0x80021470` and `CD_sync 0x80020F28` ABI shapes. Its selftest destroys the CD_cw shape and shifts the shipping owner +4; both refuse with named denominators. `vagrant_cd_contract_test` compiles the owner's exact classifier, accepts all 9 declared IDs, and refuses query, read, and unknown IDs. Low-level-only ownership was falsified because queued libds completion remained IRQ-driven. The corrected override retains the generated DsControlB body, validates the control-command class, and reuses psxport's native controller semantics. `scratch/logs/re04-owner-run.log` records Pause and Setmode, then advances beyond `_diskReset` to a later watchdog under `0x8001355C` without a recompilation miss or BIOS fatal.
- where: game/core/game_config.cpp (cdInit, cdCommand, cdSync, cdReadPrim, cdFileLoad, cdAsyncRead, …)
- gap: Blocking control is owned, not the whole CD subsystem. The live boundary now proves which missing class is next: `_loadMenuSound` enters `vs_main_diskLoadFile 0x8004493C`, whose state machine calls `vs_main_gametimeUpdate` until the async `DsPacket` read/ready-callback path completes. That completion never arrives. Async `DsCommand`/`DsPacket`, callbacks, query-result payloads, sector reads, filesystem loads, and XA remain guest-owned; the owner refuses those classes instead of fabricating results.
- notes: This game streams from the disc heavily (ENDING/ENDING.XA alone is 68 MB, plus MOV/, MUSIC/, SE/), so the CD path is unusually load-bearing here compared with the other ports in this workspace. The user preference is synchronous ownership where semantics allow it; this identified polling loop is the first concrete candidate.

## frame

### RE-05 — guest-owned frame/present contract
- status: re-partial
- deps: RE-01,RE-10
- evidence: `tools/re_frame.py` measures three SHA-bound retail overlays without taking a presenter address as input. TITLE has one complete page-flip/submit shape at `0x80071A68`; BATTLE has one at `0x8007629C`. Both read/toggle/write resident parity `0x8005E210`, index DRAWENV `0x8005E0D0` and DISPENV `0x8005E188`, call DrawSync and `vs_main_gametimeUpdate`, then PutDispEnv/PutDrawEnv/DrawOTag in that order. BATTLE's unique caller `0x8008A3A0` indexes resident OT-pointer array `0x80055C80`, clears `0x800` entries at selected block+0x10, and submits its reverse end at +0x1FFC. INITBTL uniquely allocates two `0x2088` OT blocks into that array; BATTLE's room loader uniquely allocates two `0x20000` packet pools into pointer array `0x8005E0C0`. The bases are guest-heap results and therefore not fixed across runs. `--check-config --selftest` is 4/4: shipping zeros pass; destroying TITLE's sole DrawOTag or BATTLE's pool-allocation shape produces zero matches with the searched denominator; setting a fixed OT base is refused by name.
- where: tools/re_frame.py (instrument + shipping gate) + game/core/game_config.cpp (legacy fixed-layout fields deliberately zero)
- gap: The presenter protocol and BATTLE buffer ownership are measured, but no live overlay call is reached: RE-04's asynchronous CD read/ready-callback path stalls inside `_loadMenuSound` before TITLE.PRG is loaded. TITLE's caller-provided OT allocation is not yet classified, and no game-owned runtime seam may be installed until overlay emission/routing and a reached-call gate exist.
- notes: This falsifies the old implied plan to fill psxport's fixed `otRegionBase/Stride` and `packetPoolBase/Stride` then enter its Tomba-shaped native loop. Vagrant's guest owns the page flip and uses heap-allocated per-parity buffers. Native presentation at every host VBlank was deliberately not added: at the current CD stall it would merely keep presenting the same loading state, suppress the watchdog, and turn the default launcher into an infinite poll while changing no guest state.

### RE-06 — pad driver buffers
- status: re-verified
- deps: RE-01
- evidence: `tools/re_pad.py` scans the owned SHA-verified PS-EXE without an address input and finds
  exactly one two-slot setup shape: `_sysInit` materialises `0x8005DFF0`, derives the second buffer
  at +34, and calls `PadInitDirect 0x8002DCC4` with those two pointers. The callee preserves a0/a1
  in s1/s2, materialises driver state `0x8003FCC0`, and stores them at +0x30/+0x120, independently
  deriving pointer table `0x8003FCF0` with stride 240. `--check-config` compares all four shipping
  constants and field bindings to the bytes; `--selftest` is 3/3 and proves both a destroyed call
  shape (0 matches over 83,948 candidates) and a +4 shipped-buffer edit are rejected.
- where: `tools/re_pad.py` -> `game/core/game_config.cpp` (`padSlot0Buf`, `padSlot1Buf`,
  `padSlotPtrTable`, `padSlotPtrStride`)
- gap: The addresses are complete, but the current resident boot has no owned frame loop calling
  `Pad::serviceFrame`; this step supplies the delivery destination, not live interactive gameplay.
- notes: `padDriverFn` stays zero deliberately: psxport does not read that legacy field. The runtime
  writes through the pointer table and falls back to the two fixed buffers. The matching decomp's
  `vs_main_padBuffer` name and `char[2][34]` type corroborate the byte-derived result but are not an
  input to it.

## ownership

### RE-07 — native ownership seeded from the matching decomp
- status: todo
- deps: RE-01, RE-02
- evidence:
- where: game/ (no native body exists yet)
- gap: The resident substrate now provides the `gen` comparison leg. The first native body still needs a measured reached target and a byte/SBS gate; nothing may be imported merely because the reference names it — an imported body with no live gate is a hack with a citation.
- notes: rood-reverse is ~55-63% matched overall (its own decomp.dev badges; not measured here — and the psxport port's axis is SBS RAM parity, not object identity, so the two percentages are not comparable). Widescreen source lead only: BATTLE/BATTLE.PRG's matching reference resets `SetGeomOffset(160,112)` every frame, initializes the battle view through `func_800760CC(0x140,0xF0,projectionDistance,...)`, and changes projection via `vs_battle_setProjectionDistance`. `projectionDistance` also changes during camera transitions. A future wide implementation must target that world-camera path, not globally replace `SetGeomOffset`/`SetGeomScreen`: menu, title, and other overlay calls have their own 2D/UI intent. This has no shipping address or runtime confirmation until RE-02/RE-07 exist.

## platform


### RE-08 — platform HLE windows: the hardware-sync primitives GameConfig.hle installs into
- status: todo
- deps: RE-01
- evidence: Nothing measured. RE-09 moved the resident boundary to Sony `VSync`, whose sampled helper loops on guest global `0x80032114`; it is still not an I/O-read loop and therefore is not evidence for a `GameConfig::hle` window. Split OUT of RE-01 on 2026-08-12 when RE-01's crt0 group became re-verified: game_config.cpp's .hle group was tagged RE-01 but is not consumed by crt0_setup, so leaving it there would have made a done RE-01 imply a done HLE.
- where: game/core/game_config.cpp (.hle = {})
- gap: ZERO means 'install nothing', which is the honest state: initBuiltins() registers no handler and says so, and a run that needs one hangs in the guest's real spin loop. The windows are zero too, so register_() refuses everything — this game has not stated its memory map, and a window guessed from another game's map is how a handler lands on an unrelated function. What IS known from RE-01: the executable reaches the BIOS through tail-jump thunks (libcInit 0x80026864 = 'addiu $t2,$zero,0xa0 / jr $t2 / addiu $t1,$zero,0x39'), and there are two more such thunks immediately after it (t1=0x44, t1=0x70), so a thunk TABLE exists around 0x80026864 and is the place to start.
- notes: The no-present stack is now classified as the async-CD polling loop, not an I/O-register read loop. It supplies no evidence for an HLE window; do not pre-populate from another port's window list.

### RE-09 — boot-time SPU DMA completion callback route
- status: re-verified
- deps: RE-01
- evidence: tools/re_spu_transfer.py uniquely derives StartSound 0x80013938 -> writer 0x800134D0 -> waiter 0x8001355C, state 0x800377F0, completion 0x8001347C, Sony libspu channel-4 adapter 0x8001E594, active low-level DMA owner 0x80020280, and callback table 0x80032128 from SHA-verified SLUS_010.40. Its 3/3 selftest destroys the adapter and shifts the shipped table +4. The real default launcher logs DMA4 dispatch of 0x8001DE94 from slot 0x80032138 and advances to a later VSync watchdog.
- where: tools/re_spu_transfer.py -> game/core/game_config.cpp (dmaCallbackTable)
- gap: SPU transfer completion is resolved. RE-10 now owns the later Sony VSync/VBlank boundary; no frame or gameplay is claimed by this step.
- notes: The first candidate 0x80031050 was falsified by a live slot watch; it is a different callback table. The instrument now proves startIntrDMA returns 0x80020280 and bootstrap stores it in the public DMACallback vector before accepting 0x80032128.

### RE-10 — resident VBlank counter delivery through Sony VSync
- status: re-verified
- deps: RE-09
- evidence: tools/re_vblank.py uniquely derives Sony VSync 0x8001F6C4, wait helper 0x8001F83C, counter 0x80032114, startIntrVSync 0x8001FF94, guest handler 0x8001FFEC, callback table 0x800320F4, registrar 0x80020058, callback-system wrapper 0x8001F904, public VSyncCallback 0x8001F964, bootstrap 0x8001FAFC, setjmp buffer 0x80031084, restored PC 0x8001FAD0, and HookEntryInt 0x80026954 from the SHA-verified executable. Its 4/4 both-answer selftest destroys the handler increment, shifts the shipped handler +4, and deletes the restored-PC seed. The game-owned override super-calls intact startIntrVSync, then registers psxport's video-standard-derived field clock; every field dispatches intact guest handler 0x8001FFEC, so guest code owns the counter and all eight callbacks. Against pinned psxport `9f1bb927`, scratch/logs/re05-pinned-final-irq-dma.log proves the complete runtime answer: the custom exception exit executes without falling through into initialization, DMA4 callbacks remain armed and dispatch, counter 0x80032114 advances from 0 through 173 during the bounded run, and the watchdog moves downstream to asynchronous CD with no recompilation miss or BIOS fatal.
- where: tools/re_vblank.py + game/sync/vblank.cpp + game/sync/vblank.h + game/core/game_hooks.cpp
- gap: Resident VBlank delivery is resolved. The current watchdog is downstream in `_loadMenuSound`'s asynchronous CD polling loop. RE-05 has measured the later overlay frame owner statically, but no gameplay or overlay loading is claimed.
- notes: The root cause was not an HLE read window: startIntrVSync installed a guest interrupt handler that increments the counter, but the static runtime had no display interrupt/field-delivery source, so that intact handler never ran. The solution contains no host counter increment, fixed 60 Hz literal, or guessed HLE window; the framework only schedules fields at gpu_field_rate_millihz(c), and the original handler performs every guest-visible write.

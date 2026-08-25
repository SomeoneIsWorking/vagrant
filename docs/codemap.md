# Codemap — what's where, what's done, what's missing

The orientation map: consult it at the START of a task to avoid re-deriving structure, and update it in
the SAME commit that lands or changes a subsystem. A stale map is worse than none — a subsystem is
marked done only when VERIFIED on real data, never to look better.

Companions: `docs/re-frontier.md` (the ordered RE steps: real vs hack), `docs/references.md` (the CC0
matching decomp and exactly what it does and does not buy), `docs/info/` (claims + instruments),
`docs/issues/` (what has been tried and ruled out).

The host boundary follows Dusklight's current composition pattern: a thin process entry delegates to
the runtime, and input conversion, render-pass production, and heap semantics remain cohesive peers.
For this port `VagrantRuntime` composes per-Core products through `VagrantContext`; no new behavior is
added to the legacy `GameConfig` bag.

**Status vocabulary:** ✅ verified on real data · 🟡 partial (gap named) · 🔬 in progress ·
⬜ not started · ❓ unresolved question · ➖ not applicable to this game · 🔴 regressed.

## Read this before anything else: the honest state, 2026-08-25

**This repo has verified TITLE splashes and live 24-bit intro frames, not a rendered game.** Provisioning, the inherited title runtime,
registries, and the matching CC0 reference are joined by seven measured groups: crt0/boot (RE-01), a
resident substrate rooted at the PS-EXE entry plus Sony's measured interrupt reentry
(RE-02), and all 20 non-empty `.PRG`
overlay mappings into three slots (RE-03), plus the two libpad buffers and driver pointer table
(RE-06), boot SPU DMA completion (RE-09), resident VBlank delivery (RE-10), and TITLE extraction/emission/routing (RE-11). `vagrant_port`
executes crt0 and guest main, completes `_initRand` and `_diskReset`, then dispatches the measured
DMA4 callback. The old `0x8001355C` wait clears; the measured guest VBlank handler advances counter
`0x80032114`, letting Sony `VSync` return and GPU/DMA setup continue. The honest boundary is now
four `_loadMenuSound` WAVE reads plus the 271-sector TITLE.PRG read. Deterministic guest-cycle drive
pacing and ReadN status `0x22` let the intact guest VBlank callback release libds Busy state, dispatch
each queued Pause, and finish all five loads. Resident `jal 0x80042BD8` then routes into the emitted
TITLE function `0x80071334` and reaches its GPU/image and CD work. RE-12 measures immediate sprite
leaf `0x8006A778` and gives `VagrantRuntime` a per-Core semantic producer; the real-disc default run
presents a legible Square Electronic Arts publisher splash from guest-uploaded VRAM. The test-only
disabled-producer control remains black and emits no second splash present. RE-13 measures TITLE's
MDEC callback, completion field, 24-halfword slices, and 320x224 RGB24 scanout. Its retained-super
producer presents coherent live guest-decoded intro frames; disabling only that producer still
completes 4,000 DMA1 outputs and reaches 24-bit mode but emits no same-index `present_200`. RE-14 now
services the measured high-byte-first Pad contract once per guest VBlank, proves Start skip and the
real `VSync(1)` wait, and presents the guest-built 15-bit TITLE menu at 241,809/691,200 nonblack
pixels. RE-07 lands the FIRST decomp-seeded native body (2026-08-24): the game's own allocator
initialiser `vs_main_initHeap 0x80043F74` runs as readable C++ (`vagrant::heap::initHeap`), proven
installed+reached+byte-exact by a live mirror-verify pass that a deliberate sabotage turns RED. The
RE-15 proves the former `0x800798A4` miss is BATTLE's real entry after TITLE returns. One bounded
replay run enters generated BATTLE `0x800798A4` and INITBTL `0x800FA35C`. The emitter defects behind
its next boundaries are fixed upstream (psxport `0339b459` + `073d7a62`: cross-overlay call seeds,
mask-stride dispatch recovery, iterative case-label pruning, dispatch-base classification), and the
replay now runs past both former fail-fasts deep into BATTLE initialization; the live boundary is
issue #23 (`0x800B182C`, a dispatch base carried across `jr ra` fragments). Normal movie completion,
XA/STR teardown, later menu interaction, other overlays, and gameplay remain open.

Do not read "RE-01 is done" as "the game works". The eleven addresses `crt0_setup` consumes are
measured rather than guessed, **and — since 2026-08-12 — checked by code against the
executable rather than by eye**: `tools/re_crt0.py --check-config` diffs the shipped constants in
`game/core/game_config.cpp` against what it measures, and `--gate-citations` regenerates that file's
disassembly block from the bytes. Before that, the tool held its own copy of the answer and the .cpp
held a second hand-typed one with nothing comparing them, so both gates passed with two constants
sabotaged. RE-02 now executes this boot group through guest main. The defect found while measuring
(issue #3: `crt0_setup`
formerly omitted `a1` for BIOS InitHeap) is fixed in the shared framework; it was **latent for this
game** because no code in this image can call BIOS `malloc`, so Vagrant Story cannot demonstrate the
fix without first gaining a substrate.

## The two halves

| | |
|---|---|
| `external/psxport/` | the PSX-generic framework (recorded pin `bc8c8897`): MIPS→C recompiler, runtime substrate, GTE/SPU/MDEC/CD/GPU backends, SDK HLE, SBS differential harness, SDL_GPU renderer. **Not ours** — fix framework bugs upstream in the workspace dev clone, never in this shared checkout. |
| `game/`, `tools/`, `generated/` | this port: the seam, the RE, the provisioning, and (eventually) the recompiled substrate. |
| `external/rood-reverse/` | a CC0 **matching decompilation** of this exact executable — a read-only REFERENCE, never built or linked here. See `docs/references.md`. |

## Subsystems

| subsystem | where | status | notes |
|---|---|---|---|
| Disc resolution | `tools/resolve_disc.py` | ✅ | One implementation of CLI arg > `$PSXPORT_VAGRANT_DISC` > `.env` > a `*.chd` in the repo root; refuses (exit 2) naming all four sources rather than returning empty, and refuses when a configured path does not exist instead of falling through to a different disc. `run.sh` and `extract_exe.py` both go through it. |
| Disc → executable provisioning | `tools/extract_exe.py`, `tools/discdump.py` | ✅ | Extracts `SLUS_010.40` (337,920 B) with psxport's own `discdump`, prints the PS-EXE header, and checks the SHA-1 against the vendored decomp's stated target. Verified end to end 2026-08-12. Says explicitly when it CANNOT check (decomp submodule absent) rather than passing quietly. |
| Disc → overlay provisioning | `tools/extract_overlays.py` | ✅ | Extracts reached TITLE, BATTLE, and INITBTL images into emitter-facing `.BIN` names, verifies all three SHA-1 identities against exact matching decomp targets, and refuses hash mismatches or any unowned `.BIN` in the emitter directory. The 5-case unit gate proves matching and refusal answers. The other 17 non-empty overlays remain outside the emitted inventory. |
| Decomp-target verification | `tools/verify_decomp_targets.py` | ✅ | 21/21 code images on this disc match the SHA-1 rood-reverse decompiles against; the one uncovered image is the 0-byte `MENUA.PRG`. Prints its denominators and blind spots every run; `--selftest` proves it can report a MISMATCH. |
| Static recompilation | `tools/ensure_recomp.py`, `game/recomp_seeds.json` → `generated/` | ✅ | Against psxport `aa0b2067`, current emission contains 882 resident functions plus 137 TITLE, 1,974 BATTLE, and 12 INITBTL functions. The provisioner hashes the resident executable, all three exact overlay images, seeds, recompiler sources, and explicit recompiler version; completeness requires all descriptors plus reached TITLE `0x80071334`, BATTLE `0x800798A4`, and INITBTL `0x800FA35C` entries. The unit negative deletes the BATTLE entry and is refused. Generated code is gitignored. |
| Overlay load-base RE | `tools/re_overlay.py` → `game/recomp_seeds.json`, `game/core/game_config.cpp` | ✅ | 20/20 non-empty `.PRG` images independently place themselves by `jal`/entry-offset mode and agree with SHA-bound rood-reverse link addresses; the 0-byte MENUA has no base. Three verified slots, 20 explicit seed mappings. TITLE, BATTLE, and INITBTL are now emitted and live-routed at their measured bases; the other 17 non-empty images remain deliberately un-emitted. |
| Framework seam — measured legacy facts | `game/core/game_config.cpp`, `game/core/legacy_game_interface.h` | 🟡 | Explicit compatibility debt behind `VagrantRuntime`, not the title API. **The crt0/boot group is MEASURED and GATED (RE-01, C004), the physical recompiled-main range is measured from the PS-EXE header (RE-02), the three overlay slots are MEASURED and GATED (RE-03), pad delivery is MEASURED and GATED (RE-06), and the active DMA callback table is MEASURED and GATED (RE-09, C011).** RE-05 also gates legacy fixed-frame fields to zero because the measured game uses dynamic heap pointers (C013). At framework pin `bc8c8897`, Vagrant remains deliberately legacy-backed: `LegacyGameRuntimeAdapter` projects the measured static guest-VRAM picture bit into the required runtime policy. No title-owned transition policy exists until the startup/movie/menu ownership transitions are classified as one verified state machine. Delete groups as psxport gains narrow typed fact interfaces; do not grow the bag. |
| Boot / crt0 RE | `tools/re_crt0.py` → `game/core/game_config.cpp` | ✅ | Executes crt0 from the owned image and gates all 11 boot fields plus the two PS-EXE-derived physical routing bounds. `--selftest`: 24 assertions, 0 failed, including negative mutations that zero `recMainLo` or extend `recMainHi`; `--gate-config`: pristine compile plus 5 static-assert mutations. The live substrate corroborates InitHeap and guest-main dispatch. |
| Framework seam — legacy callbacks | `game/core/game_hooks.cpp`, `game/core/legacy_game_interface.h` | 🟡 | Only unmigrated neutral/fail-fast compatibility callbacks remain. Boot and override slots are null and gated by `vagrant_runtime_test`; new behavior belongs on `VagrantRuntime`. Native frame, scheduler, and developer-warp paths remain unstood-up and fail fast. |
| Framework seam — recomp registry | `game/core/recomp_register.cpp` | ✅ | Installs the actual generated main dispatcher/index/override setter and the generated three-module TITLE/BATTLE/INITBTL table. The content-signature router refuses a different image in the same fixed slot; no guessed overlay setter or memset fast-path is wired. |
| Inherited title runtime | `game/core/vagrant_runtime.{h,cpp}`, `game/core/vagrant_context.h` → `vagrant::VagrantRuntime` | ✅ | Process-lifetime derived owner of the direct-native project default, measured guest-main dispatch, CD/VBlank override composition, and per-Core Pad/TITLE splash/movie/menu products. Explicit user/harness render selections remain higher CVar layers. It derives the bounded adapter only while generic framework algorithms consume legacy facts/callbacks; its focused test proves install identity/context and that behavior no longer lives in `GameHooks`. |
| CD/libds contract | `game/cd/ds_control.cpp`, `game/cd/ds_control_contract.h`, `tests/test_ds_control_contract.cpp`, `tools/re_cd.py`, `tools/re_async_cd.py` | 🟡 | The runtime owns measured blocking `DsControlB` through the generic synchronous controller and retains the generated body. The standalone shipping-classifier test accepts all 9 supported control IDs and refuses query, read, and unknown IDs. The executable-backed async instrument proves the final callback-to-Pause route and the guest VBlank ReadN transition. Pinned runtime evidence proves the shared controller paces sectors in guest cycles and reports status `0x22` while reading: the intact guest decodes `CdlStatRead`, leaves Busy state, dispatches Pause, and sees its completion status return to `0x02`. The run completes four WAVE loads and TITLE.PRG before an overlay dispatch miss. Later CD/XA and streaming modes remain unverified. |
| Pad delivery RE | `tools/re_pad.py` → `game/input/pad_facts.h`, `game/input/pad_delivery.{h,cpp}` | ✅ | The unique `_sysInit` call shape independently derives slot buffers `0x8005DFF0`/`0x8005E012`; `PadInitDirect` derives driver table `0x8003FCF0` at stride 240, and the unique consumer at `0x800431B0` proves `~((pad[2] << 8) | pad[3])` (C009). The per-Core product calls shared `Pad::serviceFrame` once after each intact guest VBlank, then adapts only the measured byte order. Six both-answer gates cover the typed facts, delivery ownership/order, and normalization. Forced Start reaches the menu only with shipping normalization. Compatibility `GameConfig` fields merely bind the same typed facts until the framework removes that legacy seam. |
| Boot SPU DMA completion | `tools/re_spu_transfer.py` → `game/core/game_config.cpp` | ✅ | Executable-backed RE derives `StartSound` → writer/waiter/completion, Sony libspu's DMA4 adapter, the active callback-system initializer/owner, and table `0x80032128`. Its 3/3 selftest proves both refusal classes. The real run dispatches callback `0x8001DE94` from slot `0x80032138` and advances beyond the old waiter (C011). |
| Resident VBlank delivery | `tools/re_vblank.py` → `game/sync/vblank.cpp`, `game/core/vagrant_runtime.cpp`, `game/recomp_seeds.json` | ✅ | Executable-backed RE derives `VSync`/helper/counter, `startIntrVSync`, intact guest handler, its eight-entry callback table, registrar, wrapper, bootstrap, and HookEntryInt's restored setjmp PC. `VagrantRuntime` composes the owner; the game registers the existing video-standard field clock only after the guest installs its handler, and each field dispatches that intact handler. The 4/4 both-answer gate and real custom-exit/counter trace establish both outcomes (C012). |
| Guest frame/present contract | `game/render/` (`title_startup`, `title_startup_recipe`, `title_movie`, `title_menu`), `tools/re_frame.py`, `tools/re_title_startup.py`, `tools/re_title_movie.py`, `tools/re_title_menu.py` | 🟡 | SHA-bound TITLE/BATTLE bytes derive later guest presenters `0x80071A68`/`0x8007629C`, resident parity/env globals, and BATTLE's dynamic heap OT/pools. RE-12 retains the immediate splash leaf. RE-13 retains the MDEC callback and presents live 320x224 RGB24 frames. RE-14 uniquely derives TITLE's two-pass menu owner `0x8007093C` and completed-items leaf `0x800705AC`; the retained-super producer flushes guest `DrawPrim` work at VBlank through the neutral presenter. Shipping yields a readable menu; disabling only this semantic owner reproduces queue exhaustion with the same-index present absent (C022). |
| Native ownership (first decomp-seeded body) | `tools/re_heap.py` → `game/core/game_heap.{h,cpp}`, wired in `game/core/vagrant_runtime.cpp`; contract test `tests/test_game_heap.cpp` | ✅ | RE-07 (C023): the unique arena call site `0x80042B2C` derives `vs_main_initHeap 0x80043F74` and free-list heads `0x800501A8`/`0x800501B8` from the image bytes; rood-reverse labels corroborate. The CC0 body runs as readable C++ through the override registry; the real-disc gate prints `[mirror-verify] 0x80043F74 OK (pass #1)` — install+reach+byte-match in one line that a deliberate sabotage turns RED naming the divergent bytes. Instrument selftest 5/5 with denominators; hermetic Core contract test pins the 11-word effect. alloc/free stay on the substrate until their own step. |
| Process entry | `game/core/main.cpp` | 🟡 | Installs one process-lifetime `VagrantRuntime`, then executes through resident boot, five initial file reads, routed `vs_title_exec`, publisher/developer splashes, live 24-bit intro frames, Start skip, the first 15-bit title-menu picture, and BATTLE/INITBTL entry. RE-15 proves generated BATTLE `0x800798A4` and INITBTL `0x800FA35C` execute; the psxport emitter fixes (`0339b459`+`073d7a62`) carry execution deep into BATTLE initialization. The next boundary is issue #23 (dispatch base carried across `jr ra` fragments, BATTLE `0x800B182C`). |
| Build and C++ quality | `CMakeLists.txt`, `cmake/vagrant_port.cmake`, `external/psxport/tools/check_cpp_style.py` | ✅ | Clang builds `vagrant_port`; CTest covers runtime inheritance/context ownership, TITLE sprite ABI decode, CD classification, launcher orchestration, overlay provisioning/completeness, and the shared clang-format/clang-tidy gate. Generated/external trees are excluded. |
| Project launcher | `run.sh` → `bootstrap.py` → `tools/run.py`, `tools/extract_overlays.py`, `tools/ensure_recomp.py` | 🟡 | The zero-argument frozen-uv route provisions the executable plus reached TITLE, BATTLE, and INITBTL overlays from the owned disc, hash-gates regeneration, builds the product in isolated test-free trees with a capability-checked host compiler, and launches headlessly. The locked interpreter reaches every Python/CMake child; dependency refusals name exact platform commands, and `--prepare-only` stops before launch. The measured Start replay reaches BATTLE/INITBTL initialization; normal intro completion and gameplay remain open. |
| Registries | `tools/re_frontier.py` (shim), `tools/info.py`, `tools/catalog.py` | ✅ | The RE-frontier tracker is a SHIM onto the shared engine at `external/psxport/tools/port/re_frontier.py` — this repo grows no fork of it. `info.py`/`catalog.py` are copies (no hoisted engine exists for them yet); that divergence is a known cost, see below. |
| Publication audit | `tools/go_public.py` | 🟡 | Copied from the Spyro repo, then FIXED here: it printed "RESULT: clean ✓ — ready to publish" over an empty history (zero blobs scanned, exit 0) — a clean bill of health over nothing. It now prints the blob count it scanned and exits 2 when that count is zero. The copies in the other game repos still have the defect. |
| Everything else about the game | — | ⬜ | Normal intro completion, XA/STR teardown, later title-menu interaction, BATTLE initialization after `0x800E6EAC`, later CD/XA, the other overlays, gameplay, and audio playback ownership are open. Boot through a forced Start skip into the first BATTLE/INITBTL pair is the verified exception. `docs/re-frontier.md` is the ordered list. |

## Known local costs, recorded rather than hidden

- **The inherited runtime is only the first migration slice.** `VagrantRuntime` owns behavior, but
  generic crt0, overlay/range, pad, platform-HLE, disc, render-memory, and frame-policy algorithms
  still read bounded `GameConfig` facts; native frame/scheduler/UI paths still read compatibility
  callbacks. Replace these with cohesive typed interfaces, then delete each legacy group. Do not add
  another bag or one virtual getter per integer.
- **`tools/info.py` and `tools/catalog.py` are COPIES** of the Spyro repo's versions, because no hoisted engine
  exists for them yet in `external/psxport/tools/port/`. The workspace decision is that adoption is
  additive and per-tool; this repo starts a fourth copy of each, which is exactly the divergence that
  produced `re_frontier.py`'s four-times-fixed bug. Switch them to shims as soon as the engines are
  hoisted. **Both copies arrived with a green-over-nothing bug and both were fixed HERE only**
  (`catalog.py` "(no matches)" exit 0 over a missing `docs/issues/` — issue #2; `go_public.py`
  "clean ✓ — ready to publish" over zero blobs). The other repos' copies are still wrong, which is the
  hoist argument restated as a measurement.
- **`psxport_smoke` cannot be built from a consumer tree** (framework defect found here 2026-08-12):
  `external/psxport/cmake/psxport.cmake:237` names `external/psxport/tools/smoke/psxport_smoke.cpp`
  relatively, so with
  `-DPSXPORT_BUILD_SMOKE=ON` CMake looks for it under THIS repo. The agnosticism proof is therefore only
  runnable from inside the framework repo. One-line fix upstream (`${PSXPORT_ROOT}/…`); not made here,
  because a game repo may not edit the framework.

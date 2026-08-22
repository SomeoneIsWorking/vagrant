# Codemap — what's where, what's done, what's missing

The orientation map: consult it at the START of a task to avoid re-deriving structure, and update it in
the SAME commit that lands or changes a subsystem. A stale map is worse than none — a subsystem is
marked done only when VERIFIED on real data, never to look better.

Companions: `docs/re-frontier.md` (the ordered RE steps: real vs hack), `docs/references.md` (the CC0
matching decomp and exactly what it does and does not buy), `docs/info/` (claims + instruments),
`docs/issues/` (what has been tried and ruled out).

**Status vocabulary:** ✅ verified on real data · 🟡 partial (gap named) · 🔬 in progress ·
⬜ not started · ❓ unresolved question · ➖ not applicable to this game · 🔴 regressed.

## Read this before anything else: the honest state, 2026-08-22

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
completes 4,000 DMA1 outputs and reaches 24-bit mode but emits no same-index `present_200`. Full intro
completion/skip, later CD/XA, the other overlays, the title menu, and gameplay remain open (RE-14).

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
| `external/psxport/` | the PSX-generic framework (recorded pin `57a17a14`): MIPS→C recompiler, runtime substrate, GTE/SPU/MDEC/CD/GPU backends, SDK HLE, SBS differential harness, SDL_GPU renderer. **Not ours** — fix framework bugs upstream in the workspace dev clone, never in this shared checkout. |
| `game/`, `tools/`, `generated/` | this port: the seam, the RE, the provisioning, and (eventually) the recompiled substrate. |
| `external/rood-reverse/` | a CC0 **matching decompilation** of this exact executable — a read-only REFERENCE, never built or linked here. See `docs/references.md`. |

## Subsystems

| subsystem | where | status | notes |
|---|---|---|---|
| Disc resolution | `tools/resolve_disc.py` | ✅ | One implementation of CLI arg > `$PSXPORT_VAGRANT_DISC` > `.env` > a `*.chd` in the repo root; refuses (exit 2) naming all four sources rather than returning empty, and refuses when a configured path does not exist instead of falling through to a different disc. `run.sh` and `extract_exe.py` both go through it. |
| Disc → executable provisioning | `tools/extract_exe.py`, `tools/discdump.py` | ✅ | Extracts `SLUS_010.40` (337,920 B) with psxport's own `discdump`, prints the PS-EXE header, and checks the SHA-1 against the vendored decomp's stated target. Verified end to end 2026-08-12. Says explicitly when it CANNOT check (decomp submodule absent) rather than passing quietly. |
| Disc → overlay provisioning | `tools/extract_overlays.py` | ✅ | Extracts TITLE.PRG into the emitter-facing TITLE.BIN name, verifies SHA-1 `f74a76e…` against the exact matching decomp target, and refuses hash mismatches or any unowned `.BIN` in the emitter directory. The 4-case unit gate proves both answers. The other 19 non-empty overlays remain outside the emitted inventory. |
| Decomp-target verification | `tools/verify_decomp_targets.py` | ✅ | 21/21 code images on this disc match the SHA-1 rood-reverse decompiles against; the one uncovered image is the 0-byte `MENUA.PRG`. Prints its denominators and blind spots every run; `--selftest` proves it can report a MISMATCH. |
| Static recompilation | `tools/ensure_recomp.py`, `game/recomp_seeds.json` → `generated/` | ✅ | Current emission contains 799 resident functions plus 137 TITLE functions. The provisioner hashes the resident executable, exact TITLE bytes, seeds, recompiler sources, and explicit recompiler version; completeness requires the TITLE descriptor and reached `ov_title_func_80071334` entry. The unit negative deletes that entry and is refused. Generated code is gitignored. |
| Overlay load-base RE | `tools/re_overlay.py` → `game/recomp_seeds.json`, `game/core/game_config.cpp` | ✅ | 20/20 non-empty `.PRG` images independently place themselves by `jal`/entry-offset mode and agree with SHA-bound rood-reverse link addresses; the 0-byte MENUA has no base. Three verified slots, 20 explicit seed mappings. TITLE is now emitted and live-routed at its measured base; the other 19 non-empty images remain deliberately un-emitted. |
| Framework seam — measured legacy facts | `game/core/game_config.cpp`, `game/core/legacy_game_interface.h` | 🟡 | Explicit compatibility debt behind `VagrantRuntime`, not the title API. **The crt0/boot group is MEASURED and GATED (RE-01, C004), the physical recompiled-main range is measured from the PS-EXE header (RE-02), the three overlay slots are MEASURED and GATED (RE-03), pad delivery is MEASURED and GATED (RE-06), and the active DMA callback table is MEASURED and GATED (RE-09, C011).** RE-05 also gates legacy fixed-frame fields to zero because the measured game uses dynamic heap pointers (C013). Delete groups as psxport gains narrow typed fact interfaces; do not grow the bag. |
| Boot / crt0 RE | `tools/re_crt0.py` → `game/core/game_config.cpp` | ✅ | Executes crt0 from the owned image and gates all 11 boot fields plus the two PS-EXE-derived physical routing bounds. `--selftest`: 24 assertions, 0 failed, including negative mutations that zero `recMainLo` or extend `recMainHi`; `--gate-config`: pristine compile plus 5 static-assert mutations. The live substrate corroborates InitHeap and guest-main dispatch. |
| Framework seam — legacy callbacks | `game/core/game_hooks.cpp`, `game/core/legacy_game_interface.h` | 🟡 | Only unmigrated neutral/fail-fast compatibility callbacks remain. Boot and override slots are null and gated by `vagrant_runtime_test`; new behavior belongs on `VagrantRuntime`. Native frame, scheduler, and developer-warp paths remain unstood-up and fail fast. |
| Framework seam — recomp registry | `game/core/recomp_register.cpp` | ✅ | Installs the actual generated main dispatcher/index/override setter and one-module TITLE table. The content-signature router refuses a different image in the same fixed slot; no guessed overlay setter or memset fast-path is wired. |
| Inherited title runtime | `game/core/vagrant_runtime.{h,cpp}`, `game/core/vagrant_context.h` → `vagrant::VagrantRuntime` | ✅ | Process-lifetime derived owner of the direct-native project default, measured guest-main dispatch, CD/VBlank override composition, and the per-Core TITLE splash/movie producers. Explicit user/harness render selections remain higher CVar layers. It derives the bounded adapter only while generic framework algorithms consume legacy facts/callbacks; its focused test proves install identity/context and that behavior no longer lives in `GameHooks`. |
| CD/libds contract | `game/cd/ds_control.cpp`, `game/cd/ds_control_contract.h`, `tests/test_ds_control_contract.cpp`, `tools/re_cd.py`, `tools/re_async_cd.py` | 🟡 | The runtime owns measured blocking `DsControlB` through the generic synchronous controller and retains the generated body. The standalone shipping-classifier test accepts all 9 supported control IDs and refuses query, read, and unknown IDs. The executable-backed async instrument proves the final callback-to-Pause route and the guest VBlank ReadN transition. Pinned runtime evidence proves the shared controller paces sectors in guest cycles and reports status `0x22` while reading: the intact guest decodes `CdlStatRead`, leaves Busy state, dispatches Pause, and sees its completion status return to `0x02`. The run completes four WAVE loads and TITLE.PRG before an overlay dispatch miss. Later CD/XA and streaming modes remain unverified. |
| Pad delivery RE | `tools/re_pad.py` → `game/core/game_config.cpp` | ✅ | The unique `_sysInit` call shape independently derives slot buffers `0x8005DFF0`/`0x8005E012`; `PadInitDirect`'s own a0/a1 stores derive driver pointer table `0x8003FCF0` at stride 240 (C009). The instrument gates all four shipping constants and bindings; its negatives destroy the call shape and shift a shipped buffer. Input can be delivered once a frame owner calls `Pad::serviceFrame`; this does not claim such a frame loop exists. |
| Boot SPU DMA completion | `tools/re_spu_transfer.py` → `game/core/game_config.cpp` | ✅ | Executable-backed RE derives `StartSound` → writer/waiter/completion, Sony libspu's DMA4 adapter, the active callback-system initializer/owner, and table `0x80032128`. Its 3/3 selftest proves both refusal classes. The real run dispatches callback `0x8001DE94` from slot `0x80032138` and advances beyond the old waiter (C011). |
| Resident VBlank delivery | `tools/re_vblank.py` → `game/sync/vblank.cpp`, `game/core/vagrant_runtime.cpp`, `game/recomp_seeds.json` | ✅ | Executable-backed RE derives `VSync`/helper/counter, `startIntrVSync`, intact guest handler, its eight-entry callback table, registrar, wrapper, bootstrap, and HookEntryInt's restored setjmp PC. `VagrantRuntime` composes the owner; the game registers the existing video-standard field clock only after the guest installs its handler, and each field dispatches that intact handler. The 4/4 both-answer gate and real custom-exit/counter trace establish both outcomes (C012). |
| Guest frame/present contract | `game/render/` (`title_startup`, `title_startup_recipe`, `title_movie`), `tools/re_frame.py`, `tools/re_title_startup.py`, `tools/re_title_movie.py` | 🟡 | SHA-bound TITLE/BATTLE bytes derive later guest presenters `0x80071A68`/`0x8007629C`, resident parity/env globals, and BATTLE's dynamic heap OT/pools. RE-12 derives and retains the immediate splash leaf. RE-13 derives the MDEC callback `0x8006F174`, completion word `0x800DEDDC`, 24-halfword slices, and 320x224 RGB24 display; its retained-super semantic producer presents coherent live guest-decoded intro frames. Full intro completion and the menu transition remain RE-14. |
| Process entry | `game/core/main.cpp` | 🟡 | Installs one process-lifetime `VagrantRuntime`, then executes through resident boot, five initial file reads, routed `vs_title_exec`, publisher/developer splashes, and live 24-bit intro frames. Full movie completion, title menu, and gameplay are not observed. |
| Build and C++ quality | `CMakeLists.txt`, `cmake/vagrant_port.cmake`, `external/psxport/tools/check_cpp_style.py` | ✅ | Clang builds `vagrant_port`; CTest covers runtime inheritance/context ownership, TITLE sprite ABI decode, CD classification, launcher orchestration, overlay provisioning/completeness, and the shared clang-format/clang-tidy gate. Generated/external trees are excluded. |
| Project launcher | `run.sh` → `tools/run.py`, `tools/extract_overlays.py`, `tools/ensure_recomp.py` | 🟡 | The zero-argument route provisions both executable and TITLE from the owned disc, hash-gates regeneration, builds with verified Clang, and launches headlessly. It renders the splash sequence and live 24-bit intro frames; intro completion and the later title sequence remain open. |
| Registries | `tools/re_frontier.py` (shim), `tools/info.py`, `tools/catalog.py` | ✅ | The RE-frontier tracker is a SHIM onto the shared engine at `external/psxport/tools/port/re_frontier.py` — this repo grows no fork of it. `info.py`/`catalog.py` are copies (no hoisted engine exists for them yet); that divergence is a known cost, see below. |
| Publication audit | `tools/go_public.py` | 🟡 | Copied from the Spyro repo, then FIXED here: it printed "RESULT: clean ✓ — ready to publish" over an empty history (zero blobs scanned, exit 0) — a clean bill of health over nothing. It now prints the blob count it scanned and exits 2 when that count is zero. The copies in the other game repos still have the defect. |
| Everything else about the game | — | ⬜ | Full intro completion/skip, title menu, later CD/XA, the other overlays, gameplay, and audio playback ownership are open. Boot through live guest-decoded 24-bit intro frames is the verified exception. `docs/re-frontier.md` is the ordered list. |

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

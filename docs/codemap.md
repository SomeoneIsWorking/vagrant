# Codemap — what's where, what's done, what's missing

The orientation map: consult it at the START of a task to avoid re-deriving structure, and update it in
the SAME commit that lands or changes a subsystem. A stale map is worse than none — a subsystem is
marked done only when VERIFIED on real data, never to look better.

Companions: `docs/re-frontier.md` (the ordered RE steps: real vs hack), `docs/references.md` (the CC0
matching decomp and exactly what it does and does not buy), `docs/info/` (claims + instruments),
`docs/issues/` (what has been tried and ruled out).

**Status vocabulary:** ✅ verified on real data · 🟡 partial (gap named) · 🔬 in progress ·
⬜ not started · ❓ unresolved question · ➖ not applicable to this game · 🔴 regressed.

## Read this before anything else: the honest state, 2026-08-21

**This repo has a verified resident bootstrap, not gameplay.** Provisioning, the framework seam,
registries, and the matching CC0 reference are joined by six measured groups: crt0/boot (RE-01), a
744-function resident substrate rooted at the PS-EXE entry plus Sony's measured interrupt reentry
(RE-02), and all 20 non-empty `.PRG`
overlay mappings into three slots (RE-03), plus the two libpad buffers and driver pointer table
(RE-06), boot SPU DMA completion (RE-09), and resident VBlank delivery (RE-10). Against pinned psxport `9f1bb927`, `vagrant_port`
executes crt0 and guest main, completes `_initRand` and `_diskReset`, then dispatches the measured
DMA4 callback. The old `0x8001355C` wait clears; the measured guest VBlank handler advances counter
`0x80032114`, letting Sony `VSync` return and GPU/DMA setup continue. The honest boundary is now
`_loadMenuSound`'s first `vs_main_diskLoadFile`: its asynchronous libds state never completes, and
the watchdog samples the polling loop's `vs_main_gametimeUpdate -> VSync`. Async CD, reads, XA,
overlay execution, live presentation, and gameplay remain open. The later TITLE/BATTLE presenter
contract is measured statically; it is not claimed reached.

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
| `external/psxport/` | the PSX-generic framework (recorded pin `9f1bb927`): MIPS→C recompiler, runtime substrate, GTE/SPU/MDEC/CD/GPU backends, SDK HLE, SBS differential harness, SDL_GPU renderer. **Not ours** — fix framework bugs upstream in the workspace dev clone, never in this shared checkout. |
| `game/`, `tools/`, `generated/` | this port: the seam, the RE, the provisioning, and (eventually) the recompiled substrate. |
| `external/rood-reverse/` | a CC0 **matching decompilation** of this exact executable — a read-only REFERENCE, never built or linked here. See `docs/references.md`. |

## Subsystems

| subsystem | where | status | notes |
|---|---|---|---|
| Disc resolution | `tools/resolve_disc.py` | ✅ | One implementation of CLI arg > `$PSXPORT_VAGRANT_DISC` > `.env` > a `*.chd` in the repo root; refuses (exit 2) naming all four sources rather than returning empty, and refuses when a configured path does not exist instead of falling through to a different disc. `run.sh` and `extract_exe.py` both go through it. |
| Disc → executable provisioning | `tools/extract_exe.py`, `tools/discdump.py` | ✅ | Extracts `SLUS_010.40` (337,920 B) with psxport's own `discdump`, prints the PS-EXE header, and checks the SHA-1 against the vendored decomp's stated target. Verified end to end 2026-08-12. Says explicitly when it CANNOT check (decomp submodule absent) rather than passing quietly. |
| Decomp-target verification | `tools/verify_decomp_targets.py` | ✅ | 21/21 code images on this disc match the SHA-1 rood-reverse decompiles against; the one uncovered image is the 0-byte `MENUA.PRG`. Prints its denominators and blind spots every run; `--selftest` proves it can report a MISMATCH. |
| Static recompilation | `tools/ensure_recomp.py`, `game/recomp_seeds.json` → `generated/` | ✅ | Resident bootstrap verified: the emitter's mandatory PS-EXE entry root, one executable-derived `main_reentry` (`0x8001FAD0`), and pointer/table discovery yield 261 seeds and 744 functions. `tools/re_vblank.py` derives the reentry from Sony's setjmp/HookEntryInt path and rejects its omission; the forced negative misses exactly there. The provisioner hashes the executable, seeds, recompiler sources, and explicit recompiler version, and refuses an incomplete manifest. The real port then reaches async CD without a recompilation miss or BIOS fatal. Generated code is gitignored. |
| Overlay load-base RE | `tools/re_overlay.py` → `game/recomp_seeds.json`, `game/core/game_config.cpp` | ✅ | 20/20 non-empty `.PRG` images independently place themselves by `jal`/entry-offset mode and agree with SHA-bound rood-reverse link addresses; the 0-byte MENUA has no base. Three verified slots, 20 explicit seed mappings. `--selftest` 7/7 with no skips; `--check-config` 24/24. Runtime overlay-loader observation awaits RE-04 because the resident substrate stalls in an earlier async sound-data read. |
| Framework seam — config | `game/core/game_config.cpp` | 🟡 | Compiles. **The crt0/boot group is MEASURED and GATED (RE-01, C004), the physical recompiled-main range is measured from the PS-EXE header (RE-02), the three overlay slots are MEASURED and GATED (RE-03), pad delivery is MEASURED and GATED (RE-06), and the active DMA callback table is MEASURED and GATED (RE-09, C011).** RE-05 also gates the legacy fixed-frame fields to zero because the measured game uses dynamic heap pointers (C013). Other guest-address groups remain `0` under RE-04/08. |
| Boot / crt0 RE | `tools/re_crt0.py` → `game/core/game_config.cpp` | ✅ | Executes crt0 from the owned image and gates all 11 boot fields plus the two PS-EXE-derived physical routing bounds. `--selftest`: 24 assertions, 0 failed, including negative mutations that zero `recMainLo` or extend `recMainHi`; `--gate-config`: pristine compile plus 5 static-assert mutations. The live substrate corroborates InitHeap and guest-main dispatch. |
| Framework seam — hooks | `game/core/game_hooks.cpp` | 🟡 | Compiles. Installs the measured blocking-CD and resident-VBlank owners. Neutral bodies remain where "nothing is owned" is the correct semantic; fail-fast `abort()` bodies guard every framework path this port has not stood up. `bootInit` refuses rather than dispatching `gameMain == 0`. |
| Framework seam — recomp registry | `game/core/recomp_register.cpp` | ✅ | Installs the actual generated main dispatcher/index/override setter and empty generated overlay table. No guessed overlay setter or memset fast-path is wired. |
| Blocking libds control | `game/cd/ds_control.cpp`, `game/cd/ds_control_contract.h`, `tests/test_ds_control_contract.cpp` | 🟡 | The runtime owns measured `DsControlB` through the generic synchronous controller and retains the generated body. The standalone shipping-classifier test accepts all 9 supported control IDs and refuses query, read, and unknown IDs. Async commands, callbacks, result payloads, reads, and XA remain unowned. |
| Pad delivery RE | `tools/re_pad.py` → `game/core/game_config.cpp` | ✅ | The unique `_sysInit` call shape independently derives slot buffers `0x8005DFF0`/`0x8005E012`; `PadInitDirect`'s own a0/a1 stores derive driver pointer table `0x8003FCF0` at stride 240 (C009). The instrument gates all four shipping constants and bindings; its negatives destroy the call shape and shift a shipped buffer. Input can be delivered once a frame owner calls `Pad::serviceFrame`; this does not claim such a frame loop exists. |
| Boot SPU DMA completion | `tools/re_spu_transfer.py` → `game/core/game_config.cpp` | ✅ | Executable-backed RE derives `StartSound` → writer/waiter/completion, Sony libspu's DMA4 adapter, the active callback-system initializer/owner, and table `0x80032128`. Its 3/3 selftest proves both refusal classes. The real run dispatches callback `0x8001DE94` from slot `0x80032138` and advances beyond the old waiter (C011). |
| Resident VBlank delivery | `tools/re_vblank.py` → `game/sync/vblank.cpp`, `game/core/game_hooks.cpp`, `game/recomp_seeds.json` | ✅ | Executable-backed RE derives `VSync`/helper/counter, `startIntrVSync`, intact guest handler, its eight-entry callback table, registrar, wrapper, bootstrap, and HookEntryInt's restored setjmp PC. The game registers the existing video-standard field clock only after the guest installs its handler; each field dispatches that intact handler, which remains the sole owner of counter/callback semantics. The 4/4 both-answer gate and real custom-exit/counter trace establish both outcomes (C012). |
| Guest frame/present contract | `tools/re_frame.py` → `game/core/game_config.cpp` | 🟡 | SHA-bound TITLE and BATTLE bytes uniquely derive guest presenters `0x80071A68`/`0x8007629C`, resident parity/env globals, BATTLE's OT submit owner, and its guest-heap allocations: two 0x2088 OT blocks and two 0x20000 packet pools. This proves the legacy fixed-base frame fields must remain zero; the 4/4 both-answer gate enforces it. Runtime ownership is not wired because async CD has not loaded either overlay. |
| Process entry | `game/core/main.cpp` | 🟡 | Built and executed through crt0, guest main, `_initRand`, `_diskReset` Pause/Setmode, boot SPU DMA, resident VBlank, and GPU-standard setup. The current honest boundary is the first asynchronous WAVE data read inside `_loadMenuSound`; no gameplay/overlay loading is observed. |
| Build and C++ quality | `CMakeLists.txt`, `cmake/vagrant_port.cmake`, `external/psxport/tools/check_cpp_style.py` | ✅ | Clang builds `vagrant_seam`; `vagrant_cd_contract_test` exercises the exact CD classifier. The normal CTest pass reuses psxport's shared checker with this repo's tracked `.clang-format`/`.clang-tidy`: all first-party C/C++ is format- and size-checked, and all compile-backed first-party C++ TUs are linted through CMake's real compile database. Generated/external trees are excluded. |
| Project launcher | `run.sh` → `tools/run.py`, `tools/ensure_recomp.py` | 🟡 | The shell is a four-line stable dispatch. Python owns framework/reference provisioning, disc identity, hash-checked recomp freshness, verified Clang configuration, incremental `vagrant_port` build, and launch. Its no-argument path is tested to route to the current target, pin the still-frameless bootstrap to headless operation, and stop on refusal. The target clears resident VSync waits, then reaches the first async-CD poll before TITLE presentation; that boundary is stated before launch. |
| Registries | `tools/re_frontier.py` (shim), `tools/info.py`, `tools/catalog.py` | ✅ | The RE-frontier tracker is a SHIM onto the shared engine at `external/psxport/tools/port/re_frontier.py` — this repo grows no fork of it. `info.py`/`catalog.py` are copies (no hoisted engine exists for them yet); that divergence is a known cost, see below. |
| Publication audit | `tools/go_public.py` | 🟡 | Copied from the Spyro repo, then FIXED here: it printed "RESULT: clean ✓ — ready to publish" over an empty history (zero blobs scanned, exit 0) — a clean bill of health over nothing. It now prints the blob count it scanned and exits 2 when that count is zero. The copies in the other game repos still have the defect. |
| Everything else about the game | — | ⬜ | Async CD/read/XA, live frame integration, renderer, audio playback ownership, and other native ownership: **not started.** Boot, blocking libds control, SPU DMA completion, resident VBlank delivery, the measured pad delivery seam, and the static guest-frame contract are the exceptions described above. `docs/re-frontier.md` is the ordered list. |

## Known local costs, recorded rather than hidden

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

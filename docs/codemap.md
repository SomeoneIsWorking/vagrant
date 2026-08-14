# Codemap — what's where, what's done, what's missing

The orientation map: consult it at the START of a task to avoid re-deriving structure, and update it in
the SAME commit that lands or changes a subsystem. A stale map is worse than none — a subsystem is
marked done only when VERIFIED on real data, never to look better.

Companions: `docs/re-frontier.md` (the ordered RE steps: real vs hack), `docs/references.md` (the CC0
matching decomp and exactly what it does and does not buy), `docs/info/` (claims + instruments),
`docs/issues/` (what has been tried and ruled out).

**Status vocabulary:** ✅ verified on real data · 🟡 partial (gap named) · 🔬 in progress ·
⬜ not started · ❓ unresolved question · ➖ not applicable to this game · 🔴 regressed.

## Read this before anything else: the honest state, 2026-08-14

**This repo has a verified resident bootstrap, not gameplay.** Provisioning, the framework seam,
registries, and the matching CC0 reference are joined by three measured groups: crt0/boot (RE-01), a
743-function resident substrate rooted at the PS-EXE entry (RE-02), and all 20 non-empty `.PRG`
overlay mappings into three slots (RE-03). Against psxport `be03593f`, `vagrant_port` executes crt0
and guest main, completes `_initRand`, then aborts at the no-frame watchdog. The sampled backtrace is
`OtAttr::trackStoreSlow -> Core::mem_w32` beneath generated guest functions, not proof of a specific
hardware-sync primitive. There is no recompilation miss or unimplemented-BIOS fatal; overlays and
gameplay remain beyond that boundary.

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
| `external/psxport/` | the PSX-generic framework (recorded gitlink `be03593f`): MIPS→C recompiler, runtime substrate, GTE/SPU/MDEC/CD/GPU backends, SDK HLE, SBS differential harness, SDL_GPU renderer. **Not ours** — fix framework bugs upstream in the workspace dev clone, never in this submodule. |
| `game/`, `tools/`, `generated/` | this port: the seam, the RE, the provisioning, and (eventually) the recompiled substrate. |
| `external/rood-reverse/` | a CC0 **matching decompilation** of this exact executable — a read-only REFERENCE, never built or linked here. See `docs/references.md`. |

## Subsystems

| subsystem | where | status | notes |
|---|---|---|---|
| Disc resolution | `tools/resolve_disc.py` | ✅ | One implementation of CLI arg > `$PSXPORT_VAGRANT_DISC` > `.env` > a `*.chd` in the repo root; refuses (exit 2) naming all four sources rather than returning empty, and refuses when a configured path does not exist instead of falling through to a different disc. `run.sh` and `extract_exe.py` both go through it. |
| Disc → executable provisioning | `tools/extract_exe.py`, `tools/discdump.py` | ✅ | Extracts `SLUS_010.40` (337,920 B) with psxport's own `discdump`, prints the PS-EXE header, and checks the SHA-1 against the vendored decomp's stated target. Verified end to end 2026-08-12. Says explicitly when it CANNOT check (decomp submodule absent) rather than passing quietly. |
| Decomp-target verification | `tools/verify_decomp_targets.py` | ✅ | 21/21 code images on this disc match the SHA-1 rood-reverse decompiles against; the one uncovered image is the 0-byte `MENUA.PRG`. Prints its denominators and blind spots every run; `--selftest` proves it can report a MISMATCH. |
| Static recompilation | `game/recomp_seeds.json` → `generated/` | ✅ | Resident bootstrap verified: the emitter's mandatory PS-EXE entry root plus pointer/table discovery yields 260 seeds and 743 functions with both explicit executable lists empty. Against psxport `be03593f`, `vagrant_port` executes measured crt0/InitHeap and guest main, completes `_initRand`, then reaches the no-frame watchdog without a recompilation miss or BIOS fatal. Generated code is gitignored. |
| Overlay load-base RE | `tools/re_overlay.py` → `game/recomp_seeds.json`, `game/core/game_config.cpp` | ✅ | 20/20 non-empty `.PRG` images independently place themselves by `jal`/entry-offset mode and agree with SHA-bound rood-reverse link addresses; the 0-byte MENUA has no base. Three verified slots, 20 explicit seed mappings. `--selftest` 7/7 with no skips; `--check-config` 24/24. Runtime loader observation awaits RE-04 because the resident substrate reaches the no-frame watchdog before a loader is observed. |
| Framework seam — config | `game/core/game_config.cpp` | 🟡 | Compiles. **The crt0/boot group is MEASURED and GATED (RE-01, C004), the physical recompiled-main range is measured from the PS-EXE header (RE-02), and the three overlay slots are MEASURED and GATED (RE-03).** Other guest-address groups remain `0` under RE-04/05/06/08. |
| Boot / crt0 RE | `tools/re_crt0.py` → `game/core/game_config.cpp` | ✅ | Executes crt0 from the owned image and gates all 11 boot fields plus the two PS-EXE-derived physical routing bounds. `--selftest`: 24 assertions, 0 failed, including negative mutations that zero `recMainLo` or extend `recMainHi`; `--gate-config`: pristine compile plus 5 static-assert mutations. The live substrate corroborates InitHeap and guest-main dispatch. |
| Framework seam — hooks | `game/core/game_hooks.cpp` | ⬜ | Compiles. Neutral bodies where "nothing is owned" is the correct semantic; fail-fast `abort()` bodies for every framework path this port has not stood up. `bootInit` refuses rather than dispatching `gameMain == 0`. |
| Framework seam — recomp registry | `game/core/recomp_register.cpp` | ✅ | Installs the actual generated main dispatcher/index/override setter and empty generated overlay table. No guessed overlay setter or memset fast-path is wired. |
| Process entry | `game/core/main.cpp` | 🟡 | Built and executed through measured crt0, InitHeap, guest main, and `_initRand`. The current honest boundary is the no-frame watchdog, sampled in `OtAttr::trackStoreSlow -> Core::mem_w32`; no gameplay/overlay loading is observed. |
| Build | `CMakeLists.txt`, `cmake/vagrant_port.cmake` | ✅ | Bare clone boundary: `vagrant_seam` builds without copyrighted/provisioned inputs; `vagrant_port` is absent until the owner provisions the executable and emits gitignored `generated/`. After that explicit step it compiles and links the 743-function resident substrate. `PSXPORT_DIR` defaults to the pinned submodule and can select the framework dev clone. |
| Play launcher | `run.sh` | 🟡 | The USER's; agents must never run it. After explicit provisioning/emission it builds and runs the resident substrate to the current no-frame watchdog; this is not a gameplay claim. |
| Registries | `tools/re_frontier.py` (shim), `tools/info.py`, `tools/catalog.py` | ✅ | The RE-frontier tracker is a SHIM onto the shared engine at `external/psxport/tools/port/re_frontier.py` — this repo grows no fork of it. `info.py`/`catalog.py` are copies (no hoisted engine exists for them yet); that divergence is a known cost, see below. |
| Publication audit | `tools/go_public.py` | 🟡 | Copied from the Spyro repo, then FIXED here: it printed "RESULT: clean ✓ — ready to publish" over an empty history (zero blobs scanned, exit 0) — a clean bill of health over nothing. It now prints the blob count it scanned and exits 2 when that count is zero. The copies in the other game repos still have the defect. |
| Everything else about the game | — | ⬜ | CD, frame loop, pad, renderer, audio, native ownership: **not started.** Boot is the one exception and only at the crt0 layer (row above). `docs/re-frontier.md` is the ordered list. |

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

# Codemap — what's where, what's done, what's missing

The orientation map: consult it at the START of a task to avoid re-deriving structure, and update it in
the SAME commit that lands or changes a subsystem. A stale map is worse than none — a subsystem is
marked done only when VERIFIED on real data, never to look better.

Companions: `docs/re-frontier.md` (the ordered RE steps: real vs hack), `docs/references.md` (the CC0
matching decomp and exactly what it does and does not buy), `docs/info/` (claims + instruments),
`docs/issues/` (what has been tried and ruled out).

**Status vocabulary:** ✅ verified on real data · 🟡 partial (gap named) · 🔬 in progress ·
⬜ not started · ❓ unresolved question · ➖ not applicable to this game · 🔴 regressed.

## Read this before anything else: the honest state, 2026-08-12

**This repo is scaffolding. The port does not run and nothing about the game is reverse-engineered.**
What exists is provisioning, the framework seam (compiling, all-zero), the registries, and a vendored
CC0 matching decomp whose target images are *measured* to be byte-identical to this disc's. There is no
recompiled substrate, no `vagrant_port` binary, and no native body. Every ⬜ below is real.

## The two halves

| | |
|---|---|
| `external/psxport/` | the PSX-generic framework (submodule, pinned `0f08d2e7`): MIPS→C recompiler, runtime substrate, GTE/SPU/MDEC/CD/GPU backends, SDK HLE, SBS differential harness, SDL_GPU renderer. **Not ours** — fix framework bugs upstream in the workspace dev clone, never in this submodule. |
| `game/`, `tools/`, `generated/` | this port: the seam, the RE, the provisioning, and (eventually) the recompiled substrate. |
| `external/rood-reverse/` | a CC0 **matching decompilation** of this exact executable — a read-only REFERENCE, never built or linked here. See `docs/references.md`. |

## Subsystems

| subsystem | where | status | notes |
|---|---|---|---|
| Disc resolution | `tools/resolve_disc.py` | ✅ | One implementation of CLI arg > `$PSXPORT_VAGRANT_DISC` > `.env` > a `*.chd` in the repo root; refuses (exit 2) naming all four sources rather than returning empty, and refuses when a configured path does not exist instead of falling through to a different disc. `run.sh` and `extract_exe.py` both go through it. |
| Disc → executable provisioning | `tools/extract_exe.py`, `tools/discdump.py` | ✅ | Extracts `SLUS_010.40` (337,920 B) with psxport's own `discdump`, prints the PS-EXE header, and checks the SHA-1 against the vendored decomp's stated target. Verified end to end 2026-08-12. Says explicitly when it CANNOT check (decomp submodule absent) rather than passing quietly. |
| Decomp-target verification | `tools/verify_decomp_targets.py` | ✅ | 21/21 code images on this disc match the SHA-1 rood-reverse decompiles against; the one uncovered image is the 0-byte `MENU/MENUA.PRG`. Prints its denominators and blind spots every run; `--selftest` proves it can report a MISMATCH. |
| Static recompilation | `game/recomp_seeds.json` → `generated/` | ⬜ | **Not started, and blocked on RE.** The seed file is empty and the 21 `.PRG` load bases are unknown (RE-02, RE-03). `emit.py` refuses a missing overlay base by design; a guessed one emits a whole module at wrong addresses. |
| Framework seam — config | `game/core/game_config.cpp` | ⬜ | Compiles; every guest address is `0` with the frontier step named. The only non-zero values are port facts, not RE: `discEnvVar`, `cardEnvVar`/`cardDefaultPath`, `paceQuota = 1`, `windowTitle`, `preserveVramBackdrop = 1`. The PS-EXE header facts (entry `0x8001F544`, text `0x80010000+0x52000`, sp `0x801FFFF0`) are recorded as `static constexpr` + a `static_assert`, deliberately NOT wired into the boot group, which the framework consumes as a group. |
| Framework seam — hooks | `game/core/game_hooks.cpp` | ⬜ | Compiles. Neutral bodies where "nothing is owned" is the correct semantic; fail-fast `abort()` bodies for every framework path this port has not stood up. `bootInit` refuses rather than dispatching `gameMain == 0`. |
| Framework seam — recomp registry | `game/core/recomp_register.cpp` | ⬜ | Deliberately UNWRITTEN and excluded from the compiling target — it is the one TU that names `generated/` symbols. It `#error`s under `VAGRANT_HAVE_SUBSTRATE` (which the port target defines) so a substrate cannot appear without someone writing the real registry. |
| Process entry | `game/core/main.cpp` | 🟡 | Compiles. Framework bring-up in the standard order (GTE/MDEC/SPU/GPU/CD/HLE/pad), then `native_boot_run`. Never executed: there is no binary to run yet. |
| Build | `CMakeLists.txt`, `cmake/vagrant_port.cmake` | 🟡 | `psxport` (framework lib) and `vagrant_seam` (OBJECT lib over the seam TUs — the gate that runs today) configure and build from a bare clone. `vagrant_port` is configured ONLY when `generated/rec_sources.cmake` exists, with a loud configure-time STATUS saying why it does not. `PSXPORT_DIR` defaults to the submodule. |
| Play launcher | `run.sh` | 🟡 | The USER's; agents must never run it. Does every step that is real today and then STOPS with exit 3, naming RE-02/RE-03 as what blocks the recompile. |
| Registries | `tools/re_frontier.py` (shim), `tools/info.py`, `tools/catalog.py` | ✅ | The RE-frontier tracker is a SHIM onto the shared engine at `external/psxport/tools/port/re_frontier.py` — this repo grows no fork of it. `info.py`/`catalog.py` are copies (no hoisted engine exists for them yet); that divergence is a known cost, see below. |
| Publication audit | `tools/go_public.py` | 🟡 | Copied from `spyro/tools/`, then FIXED here: it printed "RESULT: clean ✓ — ready to publish" over an empty history (zero blobs scanned, exit 0) — a clean bill of health over nothing. It now prints the blob count it scanned and exits 2 when that count is zero. The copies in the other game repos still have the defect. |
| Everything about the game itself | — | ⬜ | Boot, CD, frame loop, pad, renderer, audio, native ownership: **not started.** `docs/re-frontier.md` is the ordered list. |

## Known local costs, recorded rather than hidden

- **`tools/info.py` and `tools/catalog.py` are COPIES** of `spyro/tools/`, because no hoisted engine
  exists for them yet in `external/psxport/tools/port/`. The workspace decision is that adoption is
  additive and per-tool; this repo starts a fourth copy of each, which is exactly the divergence that
  produced `re_frontier.py`'s four-times-fixed bug. Switch them to shims as soon as the engines are
  hoisted. **Both copies arrived with a green-over-nothing bug and both were fixed HERE only**
  (`catalog.py` "(no matches)" exit 0 over a missing `docs/issues/` — issue #2; `go_public.py`
  "clean ✓ — ready to publish" over zero blobs). The other repos' copies are still wrong, which is the
  hoist argument restated as a measurement.
- **`psxport_smoke` cannot be built from a consumer tree** (framework defect found here 2026-08-12):
  `external/psxport/cmake/psxport.cmake:237` names `tools/smoke/psxport_smoke.cpp` relatively, so with
  `-DPSXPORT_BUILD_SMOKE=ON` CMake looks for it under THIS repo. The agnosticism proof is therefore only
  runnable from inside the framework repo. One-line fix upstream (`${PSXPORT_ROOT}/…`); not made here,
  because a game repo may not edit the framework.

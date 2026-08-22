# Vagrant Story — a PC-native port (first TITLE splash stage)

A PC-native port of **Vagrant Story** (PS1, USA, `SLUS_010.40`) built on the
[psxport](https://github.com/SomeoneIsWorking/psxport) static-recompilation framework, vendored here as
`external/psxport`.

## Status: TITLE's first publisher splash renders; no title menu or gameplay

Created 2026-08-12. An owner-provisioned, gitignored resident + TITLE substrate now builds and runs. It
executes measured crt0 and guest main, completes `_initRand`, and now completes `_diskReset`'s Pause
and Setmode through blocking libds control ownership. It also completes `StartSound`'s DMA4 transfers
through the measured libapi callback table. The resident VBlank route is now measured too: the host
supplies video-standard display-field timing, while the intact guest handler at `0x8001FFEC` advances
Sony's counter and dispatches its eight callbacks. The bounded run advances through `VSync` into GPU
setup and completes four asynchronous WAVE reads plus the 271-sector TITLE.PRG read. The controller
paces each sector at the measured 2x-drive period in guest cycles and returns ReadN status `0x22`,
so the intact guest VBlank callback releases libds Busy state and each final callback's queued Pause
dispatches normally. TITLE.PRG is SHA-verified against the exact matching decomp target, emitted at
its measured base, and routed: resident `jal 0x80042BD8` now executes `0x80071334` (`vs_title_exec`).
RE-12 now derives TITLE's immediate sprite leaf `0x8006A778`, retains its generated super-call, and
directly presents the live guest-uploaded VRAM texture at guest VBlank. The owned-disc default run
renders a legible Square Electronic Arts publisher splash at 29,499/691,200 non-black pixels; a
test-only disabled-producer control retains guest execution but produces no second present. The
honest boundary is later: after those splash loops TITLE switches to 24-bit and enters its
intro/MDEC/FMV spine without another native presentation (RE-13). What exists:

- disc → executable provisioning from **your own** disc image (nothing game-derived is in this repo),
- a process-lifetime derived `VagrantRuntime` that owns the direct-native render default, boot, and
  override behavior; measured
  `GameConfig` facts and unmigrated neutral/fail-fast `GameHooks` remain bounded compatibility debt,
- seven measured RE groups: crt0/boot (RE-01), the resident substrate (RE-02), all 20
  non-empty `.PRG` load-base mappings into three overlay slots (RE-03), and the libpad delivery buffers
  plus driver pointer table (RE-06), the boot SPU DMA callback route (RE-09), and resident VBlank
  delivery (RE-10), and reproducible TITLE extraction/emission/routing (RE-11). RE-05 also measures the later overlay-owned presenters and proves their
  heap-allocated OT/packet buffers cannot be encoded by the legacy fixed-layout GameConfig fields.
  These facts are gated back to the owned images; the first direct-native TITLE sprite producer is
  likewise measured and gated by `tools/re_title_startup.py`,
- the project registries (`docs/re-frontier.md`, `docs/codemap.md`, `docs/info/`, `docs/issues/`),
- a vendored CC0 **matching decompilation** of this exact executable, `external/rood-reverse`, whose
  target images are *measured* to be byte-identical to the ones on this disc (21/21).

`docs/codemap.md` is the honest inventory; `docs/re-frontier.md` is the ordered RE chain. RE-13 is the
next frame step: measure TITLE's 24-bit intro/MDEC path through its next native presentation without
turning the first-splash owner into a generic guest renderer.

## Getting started

**Do NOT use `git clone --recurse-submodules` or `git submodule update --init --recursive` on this
tree.** Both ABORT partway: `external/psxport/vendor/beetle-psx` nests a URL-less
`deps/lightning/gnulib`, and a recursive operation dies on it *after* cloning beetle and *before*
reaching `vendor/lucent` — leaving lucent's worktree empty with every file staged-deleted, and cmake
then failing on a missing `CMakeLists.txt`. Measured 2026-08-11; see
`external/psxport/docs/workspace/KNOWN-DEFECT-sync-submodules.md`. Init the vendors ONE AT A TIME,
non-recursively, exactly as `psxport/scripts/bootstrap-workspace.sh` does:

```sh
git clone <this repo> && cd vagrant
git submodule update --init external/psxport external/rood-reverse
for sm in vendor/beetle-psx vendor/lucent; do                    # one at a time, NEVER --recursive
  git -C external/psxport submodule update --init "$sm"
  git -C "external/psxport/$sm" reset --hard -q HEAD             # repairs a half-checkout
done
git -C external/psxport/vendor/beetle-psx submodule update --init deps/libchdr   # CHD disc access
cp .env.example .env && $EDITOR .env                # point it at your own disc image (.env is gitignored)
python3 tools/extract_exe.py                        # extract + identity-check SLUS_010.40
python3 tools/extract_overlays.py                   # extract + identity-check TITLE.PRG
python3 tools/verify_decomp_targets.py              # does the vendored decomp target our bytes? (21/21)
cmake -S . -B build -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build --target vagrant_seam vagrant_runtime_test vagrant_cd_contract_test -j"$(nproc)"
ctest --test-dir build --output-on-failure
python3 tools/re_frontier.py next                   # what to work on
```

The CTest command also runs psxport's shared non-mutating C++ quality gate: `clang-format` checks
every tracked first-party C/C++ file, while `clang-tidy` checks every compile-backed first-party
translation unit through CMake's real `compile_commands.json`. Generated, external, build, and
scratch trees are excluded.

`./run.sh` is the default project launcher. With no arguments it uses the disc configured through
`PSXPORT_VAGRANT_DISC`, `.env`, or a root-level CHD; an explicit CHD path is also accepted. It
identity-checks the executable and TITLE overlay, only re-emits when their hashed inputs changed,
builds with Clang, and launches `vagrant_port`. Today that current target is still the honest
headless TITLE-bootstrap boundary described above, not gameplay. The launcher will grow a window
when the port owns a real frame loop; until then, headless execution keeps the watchdog on the measured
guest boundary rather than host surface setup. The normal one-command verification is:

```sh
ctest --test-dir build --output-on-failure
```

## Requirements

cmake ≥ 3.21, pkg-config, SDL3, zlib, zstd, python3, Clang/clang-format/clang-tidy.

## Legal

**No game content is distributed here.** The disc image, the executable extracted from it and the
recompiled substrate derived from it are all yours and are gitignored. `tools/go_public.py` audits the
full history for disc-derived material and machine-specific paths.

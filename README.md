# Vagrant Story — a PC-native port (TITLE menu stage)

A PC-native port of **Vagrant Story** (PS1, USA, `SLUS_010.40`) built on the
[psxport](https://github.com/SomeoneIsWorking/psxport) static-recompilation framework, resolved at
`external/psxport` by `tools/psxport_sync.py`.

## Status: a forced Start skip reaches and renders the first TITLE menu; no gameplay

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
test-only disabled-producer control retains guest execution but produces no second splash present.
RE-13 derives the intact TITLE libpress/MDEC output callback, completion field, slice width, and RGB24
display dimensions. Its retained-super producer presents live guest-decoded VRAM at VBlank; a
shipping real-disc `present_200` is coherent and 678,339/691,200 pixels are non-black. The
producer-disabled negative still completes 4,000 DMA1 outputs and reaches the same 24-bit mode but
has no `present_200`. RE-14 measures Vagrant's high-byte-first pad consumer and TITLE's two-pass menu
owner. The derived runtime services the shared pad once per intact guest VBlank, applies only the
measured packet-byte adaptation, and retains the generated `_drawTitleMenuItems` body. A recorded
Start press exits the intro, the intact title code switches to 15-bit 512x224, and the neutral
presenter displays the readable Vagrant Story/New Game/Continue/Sound menu. Disabling only the menu
producer retains the transition but reproduces the 65,536-item queue fail-fast with the matching
present absent. Normal movie completion, XA/STR teardown, later menu interaction, and gameplay remain
open. RE-07 also establishes the first matching-decomp ownership slice: native
`vs_main_initHeap` is measured from the retail executable and mirror-verifies byte-exact against its
retained generated body on the live boot path. What exists:

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
  measured and gated by `tools/re_title_startup.py`; the live TITLE movie producer is measured and
  gated by `tools/re_title_movie.py`; the pad-delivery and menu-pass owners are gated by
  `tools/re_pad.py` and `tools/re_title_menu.py`; the first native heap body is gated by
  `tools/re_heap.py` and the live mirror verifier,
- the project registries (`docs/re-frontier.md`, `docs/codemap.md`, `docs/info/`, `docs/issues/`),
- a vendored CC0 **matching decompilation** of this exact executable, `external/rood-reverse`, whose
  target images are *measured* to be byte-identical to the ones on this disc (21/21).

`docs/codemap.md` is the honest inventory; `docs/re-frontier.md` is the ordered RE chain. The next
reached code boundary is missing TITLE function `0x800798A4`. Normal movie completion and XA/STR
teardown remain independently unverified; a forced skip is not evidence for either.

## Getting started

**Do NOT use `git clone --recurse-submodules` or `git submodule update --init --recursive`.** The
framework is no longer a game-repo submodule, and beetle-psx still contains a URL-less nested gitlink
that makes recursive initialization fail. Resolve the framework through its one authoritative tool;
it links the shared workspace checkout when present or creates a private clone at `psxport.pin` and
initializes only the required vendors:

```sh
git clone <this repo> && cd vagrant
python3 tools/psxport_sync.py --auto
git submodule update --init external/rood-reverse
cp .env.example .env && $EDITOR .env                # point it at your own disc image (.env is gitignored)
python3 tools/extract_exe.py                        # extract + identity-check SLUS_010.40
python3 tools/extract_overlays.py                   # extract + identity-check TITLE.PRG
python3 tools/verify_decomp_targets.py              # does the vendored decomp target our bytes? (21/21)
cmake -S . -B build -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build -j"$(nproc)"
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
builds with Clang, and launches `vagrant_port`. Today that current target is the honest headless TITLE
menu frontier described above, not gameplay. The launcher will grow a window after later title/game
execution is owned; until then, headless execution keeps the watchdog on the measured guest boundary
rather than host-surface setup. The normal one-command verification is:

```sh
ctest --test-dir build --output-on-failure
```

## Requirements

cmake ≥ 3.21, pkg-config, SDL3, zlib, zstd, python3, Clang/clang-format/clang-tidy.

## Legal

**No game content is distributed here.** The disc image, the executable extracted from it and the
recompiled substrate derived from it are all yours and are gitignored. `tools/go_public.py` audits the
full history for disc-derived material and machine-specific paths.

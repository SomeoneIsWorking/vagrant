# Vagrant Story — working rules for THIS repo

A PC-native port of **Vagrant Story (PS1, USA, `SLUS_010.40` / SLUS-01040)** built on the
[psxport](https://github.com/SomeoneIsWorking/psxport) static-recompilation framework
(`external/psxport`). psxport recompiles the game's MIPS code to C and supplies the PSX platform layer;
this repo supplies the game — the seam, the RE, and the native reimplementations.

**The framework rules are NOT restated here. Read `external/psxport/CLAUDE.md`** — it is the authority
for how a game consumes psxport: the CVar ladder, the seam, `generated/` being sacrosanct, RE-first,
diagnostics through `lucent`, the registries, and never editing `external/psxport`. The workspace map is
`external/psxport/docs/workspace/WORKSPACE.md`; the multi-agent protocol is `…/PROTOCOL.md`; the
methodology is `…/docs/porting-a-new-psx-game.md`.

## THE STATE OF THIS PORT: a forced Start skip reaches BATTLE initialization

Created 2026-08-12. Seven groups are re-verified and one frame group is measured-partial: the
**crt0/boot group** (`RE-01`, `tools/re_crt0.py`), the resident recompiled substrate (`RE-02`), all
20 non-empty `.PRG` overlay mappings into three slots (`RE-03`, `tools/re_overlay.py`), libpad
delivery buffers and their pointer table (`RE-06`, `tools/re_pad.py`), the boot SPU DMA callback
route (`RE-09`, `tools/re_spu_transfer.py`), resident VBlank delivery (`RE-10`,
`tools/re_vblank.py`), and the overlay-owned presenter/dynamic-buffer contract (`RE-05`,
`tools/re_frame.py`), plus SHA-bound TITLE extraction/emission/routing (`RE-11`,
`tools/extract_overlays.py`). The gitignored substrate emits 882 resident functions plus 137 TITLE,
1,974 BATTLE, and 12 INITBTL functions, builds `vagrant_port`, executes crt0 and guest main, and
completes `_initRand`. RE-04 owns blocking `DsControlB` (`0x80025BE4`); the run completes
`_diskReset` Pause and Setmode, dispatches DMA4 completion, advances through the measured guest
VBlank handler, and completes four asynchronous WAVE reads plus the 271-sector TITLE.PRG read.
Deterministic guest-cycle CD pacing and ReadN status `0x22` let the intact guest libds state machine
leave Busy and dispatch each final callback's queued Pause. Resident `jal 0x80042BD8` now routes into
TITLE target `0x80071334` (`vs_title_exec`) and reaches its real GPU/image and CD work.

RE-12 now owns the first direct-native picture. `tools/re_title_startup.py` derives TITLE's immediate
sprite leaf `0x8006A778`, its static packet `0x800DED28`, and the publisher/developer owner and two
live calls from the SHA-bound retail overlay. `VagrantRuntime` installs the retained-super override;
a per-Core producer decodes its semantic ABI and presents the intact guest-uploaded VRAM texture at
guest VBlank. The owned-disc default run renders the legible “Published by Square Electronic Arts
L.L.C.” splash at 29,499/691,200 non-black pixels. A separately compiled test-only disabled-producer
control retains the guest super-call but produces only a black initial present and no second present.

RE-13 now owns the next picture boundary. `tools/re_title_movie.py` derives the MDEC output callback,
`MovieData::frameComplete`, 24-halfword slice width, and 480-halfword by 224-line RGB24 display from
the SHA-bound retail overlay. The retained-super callback observes completion only after the guest
has uploaded the final slice; the per-Core producer presents the live guest VRAM scanout at VBlank.
The shipping real-disc run produces coherent animated intro frames, including `present_200` at
678,339/691,200 non-black pixels. A producer-disabled build still completes 4,000 DMA1 outputs and
reaches the same 24-bit mode but emits no `present_200`.

RE-14 measures the high-byte-first pad consumer and TITLE's two-pass menu owner. A per-Core input
product services the shared host/replay pad once per intact guest VBlank and applies only the measured
packet-byte adaptation. A recorded Start press exits the intro; intact title code crosses its
`VSync(1)` wait, switches to 15-bit 512x224, and builds a readable Vagrant
Story/New Game/Continue/Sound screen. `TitleMenuProducer` retains the generated
`_drawTitleMenuItems` body and owns only the completed-pass fence. Disabling only that producer keeps
the guest transition but reproduces the 65,536-item queue fail-fast with the matching present absent.
Normal movie completion, XA/STR teardown, later menu interaction, and gameplay remain unverified.

RE-15 corrects the old `0x800798A4` classification: after TITLE returns, resident code loads BATTLE
and INITBTL, then calls BATTLE's `vs_battle_exec`. The one bounded replay run executes generated
BATTLE `0x800798A4` and INITBTL `0x800FA35C`; its next concrete boundary is BATTLE `0x800E6EAC`,
which INITBTL calls directly but the emitter currently retains only as a preceding BATTLE body's local
label. Issue #22 owns that generic cross-overlay entry-demotion defect; do not add a Vagrant-only seed.

RE-07 owns the first decomp-seeded native body: `tools/re_heap.py` derives `vs_main_initHeap`
`0x80043F74` and its two free-list heads from the retail executable, and the readable CC0-derived body
is paired with the retained generated function through the override registry. The live mirror gate
proves it installed, ran, and byte-matched; a deliberate capacity sabotage turns that same gate red.
Allocator operations and every other decomp body remain on the substrate until separately measured.

RE-05 independently measures the later overlay-owned presenters and dynamic OT/pool contract. XA,
the other 17 non-empty overlays, later native graphics production, and every other
unmeasured guest-address group in
`game/core/game_config.cpp` stay `0` with their open steps named in `docs/re-frontier.md`. A framework
defect found while measuring crt0 (issue #3) would give a BIOS
`InitHeap` a zero-size heap; measured 2026-08-12, that is **latent here** — no code in this image can
call BIOS `malloc` (issue #3 has the census), so this game can neither exhibit the bug nor demonstrate
its fix. If something here looks like it works, check `docs/codemap.md` — the honest inventory is short.

The framework seam is inherited: one process-lifetime `vagrant::VagrantRuntime` owns the
direct-native project default, measured guest-main dispatch, and CD/VBlank override composition. It derives
`LegacyGameRuntimeAdapter` only while generic psxport algorithms still consume measured
`GameConfig` groups and unmigrated neutral/fail-fast callbacks. `game/core/legacy_game_interface.h`
names that debt; new behavior belongs on the derived runtime, not in `GameHooks`.

Host ownership follows Dusklight's current boundary rather than its platform details: the thin entry
point delegates to a composed runtime, while input conversion, render-pass ownership, and game-heap
semantics remain separate owners. Here `VagrantRuntime` composes per-Core `PadDelivery` and TITLE
producers through `VagrantContext`; it does not absorb their implementations or grow `GameConfig`.

`./run.sh` is the stable project launcher. With no arguments it resolves the framework and the disc,
identity-checks and hash-provisions the resident executable plus reached TITLE, BATTLE, and INITBTL overlays, configures both CMake
trees with the user's `CC`/`CXX` (or the host `cc`/`c++`), builds `vagrant_port`, and launches that
current target. Compiler acceptance is capability-based and has no compiler identity allow/deny
policy. It does not claim gameplay
or a finished title sequence: RE-13 records live 24-bit intro/MDEC frames, RE-14 owns only the
measured Start-skip transition to the first menu picture, and RE-15 owns entry into the first
BATTLE/INITBTL pair. The shell file is
deliberately only a Python dispatch; all policy lives
in `tools/run.py`, entered through the frozen `uv.lock` environment and propagated to every Python
subprocess and CMake configure. The isolated player build trees configure with testing disabled; the
launcher never invokes CTest or builds a test target. `--prepare-only` exercises provisioning and the
product build without starting the game. Missing native tools/libraries are refused with the exact
Homebrew, APT, DNF, winget, or vcpkg command for the detected platform. An explicit CHD path overrides the normal
`PSXPORT_VAGRANT_DISC`/`.env`/drop-in resolution order. The current bootstrap target is explicitly
headless: it has no frame loop or gameplay window yet, and entering the window presentation path would
make the watchdog diagnose host-surface setup instead of the measured guest boundary.

What DOES build today, and is the gate for a change to the seam:

```sh
cmake -S . -B build -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build -j$(nproc)
ctest --test-dir build --output-on-failure
```

`vagrant_seam` is an OBJECT library over the shared game sources: derived runtime, bounded legacy
facts/callbacks, process entry, and the `DsControlB` owner. It proves those sources still satisfy the pinned framework's seam without
requiring generated code. `vagrant_cd_contract_test` compiles the owner's exact classifier and checks
every accepted ID plus query/read/unknown refusals. When `generated/rec_sources.cmake` exists,
`vagrant_port` is the resident+TITLE substrate gate. The overlay-input CTest proves the matching and
refusal sides of SHA provisioning and generated-entry completeness. Another CTest entry runs psxport's shared
`tools/check_cpp_style.py` against this repo: it format-checks all tracked first-party C/C++ and uses
CMake's real compile database for `clang-tidy`; generated and external code are excluded. **A change
to a MEASURED constant in
`game_config.cpp` must also pass its source instrument: `python3 tools/re_crt0.py --selftest` for the
boot group, or `python3 tools/re_overlay.py --selftest && python3 tools/re_overlay.py --check-config`
for overlay slots/seeds, `python3 tools/re_spu_transfer.py --check-config --selftest` for the DMA4
callback route, `python3 tools/re_vblank.py --check-source --selftest` for resident VBlank
delivery, `python3 tools/re_frame.py --check-config --selftest` for the overlay-owned presentation
contract and deliberately-zero fixed-layout fields, or
`python3 tools/re_title_startup.py --check-source --selftest` for the first TITLE sprite contract,
`python3 tools/re_title_movie.py --check-source --selftest` for the TITLE RGB24 movie contract,
`python3 tools/re_title_menu.py --check-source --selftest` for the completed menu-pass owner,
`python3 tools/re_pad.py --check-config --selftest` for display-field delivery and byte order, or
`python3 tools/re_heap.py --check-source --selftest` for the native allocator initialiser.
These diff shipped values back to the owned bytes. Compiling is not
enough: the `static_assert`s only check the constants' internal RELATIONS, and `hi - lo == 0x46B20` holds
just as well when both values are wrong — which is exactly how a reviewer moved `kHeapSizePtr` +4 and
pointed `kLibcInit` at an unrelated nop with every gate green (workspace `PROTOCOL.md`, "THE SHIPPED
VALUE MUST BE COMPARED TO THE MEASURED ONE"). `vagrant_port` is not configured at
all until `generated/rec_sources.cmake` exists, and CMake says so loudly at configure time.

## Start here, every task

```sh
python3 tools/re_frontier.py next            # which RE step is actually ready to work
python3 tools/info.py brief <words>          # what's already proven — and does it still hold?
python3 tools/catalog.py search <symptom>    # has this been hit (or ruled out) before?
```

Believe these over your instinct about what is known. End the task by writing back what you proved,
what you disproved, and any tool you caught lying. `tools/re_frontier.py` is a SHIM onto the shared
engine in `external/psxport/tools/port/`; do not grow a local copy of it.

## The thing that makes this title different: a CC0 MATCHING decomp of this exact executable

`external/rood-reverse` (submodule, CC0-1.0) is a byte-matching decompilation of SLUS-01040. **Measured
2026-08-12: all 21 code images it targets are byte-identical to the ones on our disc**
(`tools/verify_decomp_targets.py`, 21/21; the only uncovered image is the 0-byte `MENU/MENUA.PRG`). So
its 2,299 lines of `symbol_addrs.txt` name OUR addresses with no translation, and CC0 means we may take
**code and ideas** freely.

Three rules for using it, and they are the whole reason this section exists:

1. **A borrowed address is a HYPOTHESIS until measured against these bytes.** Where a reference and a
   measurement disagree, the measurement wins — the standing workspace rule. Nothing in
   `game_config.cpp` is filled in from it, and nothing may be filled in without the disassembly line
   that justifies it pasted alongside (the shape `spider1/game/core/game_config.cpp` uses). RE-01 is the
   worked example: `tools/re_crt0.py` EXECUTES crt0 on our bytes and cites every value, and the decomp's
   names (`__ra_temp`, `_ramsize`, `InitHeap`, `vs_main_exec`) appear in the file only as corroborating
   labels. Prefer that shape — a tool that re-measures on demand — over pasting even a correct number.
2. **Never paste an overlay load base from it.** RE-03 is the completed example: M2 derives each base
   from the owned module's own `jal` targets and entry offsets; M3 first SHA-binds that module to its
   rood config and only then compares `vram`. All 20 non-empty modules agree at three slots, and the
   shipping files are gated by `--check-config`. A bare config `vram` remains inadmissible evidence.
3. **Its decomp.dev percentage is not our percentage.** Theirs is `objdiff` object identity; this port's
   axis is SBS byte-exact RAM parity. Neither implies the other, and quoting one as evidence about the
   other is how a port looks finished while nothing is gated.

Why it matters structurally: psxport's override registry wants `(addr, native, gen)` triples whose
native body byte-matches the substrate body, and a matching decomp is a **pre-verified supply of exactly
that**. RE-07 now proves that pipeline for one measured, reached body (`vs_main_initHeap`); it does not
grant blanket ownership of the rest. Importing another body without its own reach and mirror gate
would still be a hack with a citation attached. Full detail: `docs/references.md`.

## Vagrant-Story-specific facts (measured 2026-08-12 — the whole list, nothing inferred)

- **One boot executable, no boot stub.** `SYSTEM.CNF` reads `BOOT = cdrom:\SLUS_010.40;1`,
  `STACK = 801fff00`, `TCB = 4`, `EVENT = 16`. So psxport's stub stage is unused, as in spyro/spider1.
- **`SLUS_010.40`** is 337,920 bytes, SHA-1 `fababcfd4325d42f350d95b3472874affeb0e48c`. PS-EXE header:
  entry `pc0 = 0x8001F544`, text `0x80010000 + 0x52000`, `s_addr = 0x801FFFF0`, `gp0 = 0`, and
  `d_size = b_addr = b_size = 0` — one flat loaded image, so the loader clears no `.bss` and sets no
  `gp`; both are crt0's job.
- **crt0 is MEASURED (RE-01):** a stock SN crt0 at the entry point that clears
  `[0x80033678,0x800401A8)` (52,016 B), computes `sp = fp = 0x801FFFF8` from the `_ramsize` global
  (**not** from `s_addr` or SYSTEM.CNF's `STACK` — those are the BIOS shell's and get overwritten), sets
  `gp = 0x80033674`, calls BIOS `A0:0x39 InitHeap(0x800401AC, 0x001BBE50)` via the thunk at
  `0x80026864`, then `jal 0x80042C38` (`vs_main_exec`) followed by a `break`, so main never returns.
  Reproduce with `python3 tools/re_crt0.py`; the eleven `GameConfig` values are in
  `game/core/game_config.cpp` and are GATED against the bytes by `--check-config`.
- **`SLUS_010.40` IS THREE SEPARATELY-LINKED SEGMENTS in one flat image, and this is the fact most
  likely to mislead you.** Measured (zero/non-zero profile; rood-reverse's splat config supplies the
  labels and agrees to the byte): segment 1 `[0x80010000,0x800401A8)` ending in the `.sbss+.bss` that
  crt0 clears · segment 2 (libgte) `[0x80040210,0x80041D68)` · segment 3 (`main`)
  `[0x80041D68,0x80062000)`, whose own `.bss` `[0x8004FF88,0x80062000)` **crt0 never clears** — the
  verbatim load supplies the zeros, which is why `b_size = 0` works. Consequences: `heapBase`
  (`0x800401A8`) is the end of segment 1's `.bss`, **not** the end of the image, so the BIOS arena crt0
  declares overlaps 138,836 bytes of loaded code and data including `gameMain` itself; and the SN
  linker's own record at `0x80030FBC` describes segment 1 ONLY (`__bss + __bsslen -> 0x800401A8`,
  `__data + __datalen -> 0x80033674 = gp`), which makes it an independent witness for two of the eleven
  values. Do not read "the heap starts where .bss ends" as "the heap is free RAM"; that mistake was
  made here and corrected.
- **The BIOS heap is never allocated from.** Census over the whole image (2,023 `jal` sites vs 19 BIOS
  A0 thunks): no `malloc`/`free`/`calloc`/`realloc` A0 thunk exists in the image at all, and
  `InitHeap`'s only caller is crt0. The game uses its own allocator (rood-reverse: `vs_main_initHeap`
  `0x80043F74`, arena `0x8010C000 + 0xF2000`, above the image). That is why the overlapping arena is
  not a contradiction, and why issue #3 is latent here.
- **21 `.PRG` images on the disc** — `BATTLE/BATTLE.PRG` (577,828 B), `TITLE/TITLE.PRG`,
  `ENDING/ENDING.PRG`, `BATTLE/INITBTL.PRG`, `GIM/SCREFF2.PRG` and 16 `MENU/*.PRG` (one of which,
  `MENUA.PRG`, is 0 bytes). **RE-03 is measured:** BATTLE/TITLE/ENDING load at `0x80068800`;
  INITBTL/SCREFF2/MAINMENU at `0x800F9800`; the other 14 non-empty MENU modules at `0x80102800`.
  `tools/re_overlay.py` verifies all 20 from their own bytes plus SHA-bound rood configs; the 0-byte
  MENUA has no code/base. The resident substrate reaches the async sound-data read before an overlay
  loader is observed, so the tool has not observed a running overlay loader.
- **Top-level disc directories:** `BATTLE BG EFFECT ENDING EVENT GIM MAP MENU MOV MUSIC OBJ SE SMALL
  SOUND TITLE`, plus `SLUS_010.40`, `SYSTEM.CNF`, `DBGFNT.TIM` in the root (5,180 files listed).
- **It is a heavy streamer.** `ENDING/ENDING.XA` alone is 68 MB, plus `MOV/`, `MUSIC/`, `SE/`. The CD
  path is more load-bearing here than in the other ports in this workspace — expect RE-04 to matter early.
- **The executable links stock Sony libraries**, per the decomp's own section map: libcd (`SYS`, `BIOS`,
  `C_011`), libetc (`VSYNC`, `INTR`, `INTR_DMA`), libgpu, libspu, libpad (`PADENTRY`), libds, libc.
  That says which SHAPES to look for; it says nothing about where they are in this image.

Everything else about this game — the loader contract beyond its three static slot words, the later
menu/game frame loop, OT/packet-pool dance, scene model, and platform HLE windows — is **unknown**.
The libpad destinations, packet byte order, and VBlank delivery owner are measured through the first
menu picture; later interaction semantics are not. Do
not let a plausible-sounding sentence in a doc elsewhere stand in for it.

## The rules that bite hardest here

**Never guess a guest address or an overlay load base.** While the compatibility adapter exists, an un-RE'd `GameConfig` field stays `0` with a
TODO naming the frontier step. Zero is honest and psxport fails fast on it; a plausible wrong value
breaks boot in a way that reads as a framework bug. This repo has a *tempting* supply of addresses
sitting in `external/rood-reverse` — that is precisely why the rule is stated twice.

**`VagrantRuntime` is the title authority.** `main.cpp` constructs and installs one process-lifetime
instance; runtime behavior moves there through virtual overrides, not new `GameHooks` callbacks.
`GameConfig`/`GameHooks` are private compatibility tables referenced only by
`vagrant::legacy::{measuredConfig,compatibilityHooks}`. Delete fields as psxport gains narrow typed
fact interfaces; do not replace the bag with one virtual getter per integer.

**Work the step `re_frontier.py next` names, not a downstream one.** The cardinal sin on a port is
faking a step's output before its RE is done; it makes a broken port look finished.

**Provision from your own disc; commit nothing derived from it.** Resolution order (one
implementation, `tools/resolve_disc.py`): CLI arg > `$PSXPORT_VAGRANT_DISC` > `.env` > a `*.chd` in the
repo root. `.env` is gitignored because the path is machine-specific; `.env.example` is the template.
`python3 tools/extract_exe.py` does the extraction and identity-checks the result.
`tools/go_public.py` audits the full history for disc images, extracted executables and `/home/<user>`
paths — run it before this repo is ever published.

**Everything transient goes in the gitignored `scratch/`, split by kind** (`scratch/bin/`,
`scratch/raw/`, `scratch/logs/`). **Never `/tmp`** — a small RAM-backed tmpfs on this machine; diagnose
"disk quota exceeded" with `quota -s`, not `df`.

## Where the framework source comes from — `external/psxport` is the shared tree

`external/psxport` is **not a submodule** (2026-08-16): it is a SYMLINK to the workspace's shared
framework clone (`$PSX/psxport`) when one exists, or a private clone at this repo's `psxport.pin` on a
fresh machine. `tools/psxport_sync.py --auto` (called by `run.sh`) establishes whichever applies. A
framework edit made through either path is the SAME directory, live in every port at once — commit and
push framework work in `psxport/`, never here. `psxport.pin` records the framework commit this game
was built and VERIFIED against; `tools/psxport_sync.py --bump` updates it, and the gate's `--check`
fails when the framework you built against is not the recorded one.

Build against in-progress framework work:

```sh
cmake -S . -B build -DPSXPORT_DIR=/path/to/psxport      # or just ./run.sh — it resolves external/psxport
```

`PSXPORT_DIR` defaults to `external/psxport`, so a bare clone of this repo builds standalone — keep it
that way.

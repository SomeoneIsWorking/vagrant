# Vagrant Story — working rules and dynarec plan for this repository

This repository ports **Vagrant Story** (PS1 USA, `SLUS_010.40` / SLUS-01040). It is one
title-specific native/Lightrec consumer of the shared `external/psxport` framework and may use the
CC0 `external/rood-reverse` matching decompilation as a measured source aid.

## Current product contract

The product is one native/Lightrec hybrid:

- verified title-owned C++ implements deliberately native functions and subsystems;
- a per-`Core` Lightrec executor translates every remaining instruction on demand from the
  authenticated resident executable or currently loaded `.PRG` image; and
- native `superCall` executes the original guest body through that dynarec while suppressing only
  the current override for that call.

The gameplay target must not link, select, or fall back to an interpreter. An interpreter may exist
only in a separately selected test/diagnostic target. Unsupported guest behavior fails with the exact
guest PC instead of changing engines silently.

The repository has not implemented or verified this Lightrec gameplay product yet. Break-first
removal is complete: the offline translator inputs, generated guest corpus, static registry, old
process/runtime adapter, and generated-super registration glue are absent. The default launcher and
CMake product now fail at one named boundary: Vagrant Story has no adapter to psxport's dynarec-only
executor. The measured native owners and old execution evidence below remain migration inputs, not
current dynarec status or a runnable fallback.

Read `external/psxport/CLAUDE.md` for shared framework rules and
`../../shared/jit-common/docs/migration.md` for the portfolio migration contract.

## Project authorities

`docs/project-goals.md` owns durable product intent. `docs/project-state.md` owns factual capability
coverage and current focus. `docs/issues/` owns atomic work, `docs/codemap.md` owns placement, and
`docs/re-frontier.md` owns the ordered binary-evidence chain. `tools/info.py` indexes evidence
claims and instrument trust. This file owns the title-specific execution plan and invariants; it does
not promote old static execution evidence into dynarec evidence.

Start every non-trivial task with:

```sh
uv run --frozen python tools/info.py brief <words>
uv run --frozen python tools/re_frontier.py next
uv run --frozen python tools/catalog.py search <symptom>
```

## Migration sequence

1. Keep the removed static execution path absent; `tools/check_structure.py` mechanically rejects its
   registries, dispatch symbols, generated corpus, product stderr writes, and product environment reads.
2. Integrate the maintained, pinned Lightrec revision in psxport. Lightrec owns translated blocks,
   executable memory, and its cache; Vagrant Story must not grow a second CPU engine or a title-local
   cache.
3. Map the identity-checked resident executable and `.PRG` images as runtime input. A fresh checkout
   provisions only authenticated game data and redistributable runtime metadata; it must not create
   guest source or object code.
4. Give each `Core` its own executor and override state. psxport synchronizes CPU state, memory,
   exceptions, HLE/device callbacks, and bounded exits at host work, frame suspension, interrupt, and
   thread-exit boundaries.
5. Key executable identity by image/module generation plus guest address. Overlay loads, guest writes,
   DMA, savestate restore, and override install/remove/change invalidate every affected translated
   block or captured call decision.
6. Compose the preserved finite phase owners, frame driver, CD owners, title producers, input owner,
   and native heap implementation in a new title adapter. Image-scoped registration belongs in that
   adapter; domain behavior does not move into the executor.
7. Pass the TITLE discriminator below, then expand along reached control flow to representative
   interactive BATTLE gameplay.

## First implementation discriminator

From the exact `SLUS_010.40` image, the native/Lightrec gameplay product must complete
**1,000/1,000 host-owned TITLE fields** with the required native CD override active and valid VSync
ownership: no guest-VSync call, query, or advancement may escape the measured native field boundary.
The gate must prove:

- nonzero Lightrec block execution and no interpreter symbols or engine selector in the gameplay
  product;
- the native CD override is installed and reached for the retail libds/controller mismatch rather
  than bypassed by fixture data;
- one reached resident override, one reached TITLE override, and an override-bypassing `superCall`
  through Lightrec;
- TITLE image generation changes invalidate affected translated blocks, with a controlled unchanged-
  generation negative;
- the `VagrantFrameDriver` ledger reconciles 1,000/1,000 fields with zero dropped layers and no
  guest-VSync violation; and
- CPU, memory, interrupt, timing, CD, and relevant device state at the bounded checkpoint agree with
  an independent emulator or separately built test oracle.

Logos, movie frames, the menu, or 1,000 TITLE fields alone do not complete the migration. The
representative-gameplay gate must continue through New Game, BATTLE and INITBTL into a genuinely
interactive gameplay scene, exercise input, room/world rendering, streaming CD behavior, audio,
pause/menu transitions, and sustained frame progression on each released host architecture.
Enhancements remain off for the faithful baseline; semantic native BATTLE rendering, widescreen, and
interpolated presentation are separate observable gates.

## Preserved binary and behavior facts

These facts remain valid migration inputs; they are not evidence that the dynarec is implemented.

### Exact image and matching decompilation

- `SYSTEM.CNF` boots `SLUS_010.40` directly with `STACK = 801fff00`, `TCB = 4`, and `EVENT = 16`;
  there is no boot stub.
- `SLUS_010.40` is 337,920 bytes with SHA-1
  `fababcfd4325d42f350d95b3472874affeb0e48c`. Its PS-EXE header has entry `0x8001F544`, text
  `0x80010000 + 0x52000`, `s_addr = 0x801FFFF0`, `gp0 = 0`, and zero `d_size`, `b_addr`, and
  `b_size`.
- crt0 clears `[0x80033678,0x800401A8)`, derives `sp = fp = 0x801FFFF8`, sets
  `gp = 0x80033674`, calls BIOS InitHeap through `0x80026864` with
  `(0x800401AC,0x001BBE50)`, then calls `vs_main_exec 0x80042C38` and cannot return normally.
- The flat executable contains three separately linked segments:
  `[0x80010000,0x800401A8)`, libgte `[0x80040210,0x80041D68)`, and main
  `[0x80041D68,0x80062000)`. Main's `.bss` `[0x8004FF88,0x80062000)` arrives zeroed from the
  image rather than from crt0.
- The crt0 BIOS heap nominally overlaps later loaded code, but the executable contains no BIOS
  allocator thunk use. The game owns arena `0x8010C000 + 0xF2000`; measured native initializer
  `vs_main_initHeap 0x80043F74` remains a title override.
- The CC0 `external/rood-reverse` project byte-matches all 21 code images it targets and supplies
  2,299 address labels. A decomp label is still a hypothesis until a title tool verifies it against
  this exact image. Its decomp percentage is object identity, not port or runtime parity.

### Overlay identity and streaming

- The disc contains 21 `.PRG` images. Twenty are non-empty code images; `MENU/MENUA.PRG` is zero
  bytes and has no code/base.
- BATTLE, TITLE, and ENDING reuse `0x80068800`; INITBTL, SCREFF2, and MAINMENU reuse
  `0x800F9800`; the other 14 non-empty MENU modules reuse `0x80102800`. Runtime block and override
  identity therefore cannot be guest address alone.
- TITLE.PRG is copied from LBA 256000, size `0x87800`, to `0x80068800`; its routed entry is
  `vs_title_exec 0x80071334`.
- Vagrant Story is a heavy streamer. The initial four menu-sound reads, TITLE transfer, intro STR/XA,
  and later room/audio streams make CD completion and image-generation invalidation load-bearing
  runtime contracts.

### Native phase, CD, and VSync ownership

- `VagrantRuntime::bootInit` returns at `vs_main_exec 0x80042C38`; `VagrantFrameDriver` owns
  finite fields and guest VSync `0x8001F6C4` is fatal. Native owners already span `_sysInit`, TITLE
  loading, `_diskReset`, four menu-sound files, TITLE.PRG, both publisher/developer splash loops, and
  the full `_saveFileExists`/`gametimeUpdate` caller.
- The required CD ownership begins with blocking `DsControlB 0x80025BE4` and exact native handling
  for retail waits that require asynchronous controller callbacks the current synchronous host CD
  model cannot produce. Preserve the measured command postconditions; do not bypass the state
  machine with a timer or phase write.
- `NativeFile` owns finite authenticated disc extents. `TitleMemcardInit` replaces the exact
  interrupt-driven transfers for SPMCIMG and contiguous MCDATA/MCMAN with reads
  `(85144,0x1C000)` and `(85200,0x2000)`, while preserving allocation, pointer/image state, upload,
  reset policy, and eight-event lifecycle.
- Exact-pin PID 3213121 completed 1,000/1,000 finite fields through both splash loops and the
  save-file check with no guest-VSync violation. Exact-pin PID 3309285 then copied both memcard
  extents, completed the save check, and reached `_initIntroMovie`; its lower-right texture strip was
  not a valid intro picture. Those behaviors are the target checkpoint, not Lightrec proof. See
  project-state item S003, RE-18 through RE-23, and issues 0033–0035 for their evidence scope.

### TITLE and BATTLE boundaries

- TITLE's immediate sprite leaf is `0x8006A778` and its static packet is `0x800DED28`. The two
  364-field splash loops present publisher and SQUARESOFT art through the finite title owner.
- The MDEC output callback completes a 24-halfword slice into a 480-halfword by 224-line RGB24
  display. Its producer may publish only after the final guest upload.
- Natural movie return `0` and Start/right return `1` converge at `0x8006FC0C`; the sole caller
  ignores the result and enters common title/menu initialization.
- The measured high-byte-first pad delivery and two-pass menu owner lead to the readable Vagrant
  Story/New Game/Continue/Sound screen. Historical black captures after Cross were later BATTLE/loading
  fields and are not menu evidence.
- After TITLE returns, resident code loads BATTLE and INITBTL and reaches BATTLE
  `vs_battle_exec 0x800798A4` plus INITBTL `0x800FA35C`. These addresses remain runtime targets;
  the old emitted-body execution is not dynarec evidence.
- BATTLE's presenter is `0x8007629C`, dynamic-OT submit owner `0x8008A3A0`, viewport initializer
  `0x800760CC`, projection word `0x8005E248`, and projection setter `0x8007CCF0`. Its measured
  convention is 320x240 input, 320x224 draw, and GTE center `(160,112)`.
- The BATTLE completed-field fence is not a semantic native world producer. Native world work must
  read named pre-GTE camera/object/material/animation/model state; post-projection OT or packet replay
  cannot ground widescreen or interpolation.

## Title-specific engineering rules

- Reverse-engineer first. A borrowed decomp address, magic offset, unnamed field, unknown structure,
  or load base must be checked against the SHA-bound title bytes before it can ship.
- Keep `VagrantRuntime` as the framework-facing title owner. It composes `VagrantFrameDriver`,
  `ResidentPhase`, `TitleSplashPhase`, `TitleSaveCheck`, `TitleMemcardInit`, `PadDelivery`, the
  TITLE producers, CD owners, and BATTLE peers; it does not absorb their implementations.
- Native overrides require a named ownership reason and a positive reach check. They preserve the
  guest ABI and may call the original only through the scoped Lightrec `superCall` contract.
- A skip or shortened wait is a complete lifecycle transition with the same state/resource
  postconditions, never a timer fast-forward or phase write.
- Guest-rendered 4:3 is the faithful baseline. Widescreen changes projection/viewport/scissor and any
  proven culling owner; interpolation consumes explicit previous/current semantic state and never
  mutates guest RAM.
- Diagnostics print denominators and a meaningful negative, refuse missing corpora, and prove both
  answers through the shipping seam they assess.

## Provisioning and shared framework

Game assets are never committed or packaged. Resolve the disc in the existing order: explicit CLI
argument, `PSXPORT_VAGRANT_DISC`, `.env`, then an unambiguous repo-root `*.chd`; validate the exact
executable and every loaded overlay before mapping it. Packaged first run will use the platform file
picker and persist the validated selection in OS user data.

`external/psxport` resolves to the one shared writable psxport checkout in this workspace or to a
private clone at `psxport.pin` in a standalone checkout. Framework execution, cache, memory, HLE, or
invalidation work belongs in psxport; Vagrant identity, native ownership, and title behavior stay
here. Build outputs belong under `build/`; bounded logs and captures belong under the stable
gitignored `scratch/` children, never `/tmp`.

# Vagrant Story codemap

This map answers which subsystem owns each responsibility, where it lives, and where related work
belongs. Capability status is authoritative in `docs/project-state.md`; epic intent is in
`docs/project-goals.md`; atomic work is in `docs/issues/`; ordered binary evidence is in
`docs/re-frontier.md`. The framework side lives in `external/psxport/docs/codemap.md`.

## Architecture

`vagrant::Application` is the process composition owner: the only place that knows the ORDER the
machine becomes a product. It composes cohesive per-Core owners and implements none of them.

```text
run.sh -> bootstrap.py -> tools/run.py -> tools/launcher/runtime_boundary.py
       -> vagrant_port (game/main.cpp) -> vagrant::runApplication
       -> vagrant::Application -> VagrantRuntime (installed before the Game)
                               -> resident image admission + publication
                               -> vagrant::installResidentNativeOwners
                               -> psx::Machine{game} -> control channel + product frame loop
                                                          -> psx::frame::FieldTurn (per-field services)
                                                          -> vagrant::VagrantFrameDriver (the finite field)

every per-Core title owner hangs off vagrant::VagrantContext, reached ONLY through vagrant::contextOf(Core&)
```

Two rules hold everywhere below:

- **`vagrant::dynarec` is the only module that spells an `ExecutionBudget`, resolves an image identity,
  or chooses a dispatch form.** Every other title file reaches guest execution through it.
- **`vagrant::contextOf(Core&)` is the only accessor for a Core's title products.** It is the single
  place that refuses a Core with no `VagrantContext`, and its diagnostic names the composition defect.

## Subsystems by directory

### `game/` — process entry

| Namespace | Symbol | Responsibility |
|---|---|---|
| — | `main` | the shipped `main`: one call to `vagrant::runApplication`, holding no title state |
| `vagrant` | `runApplication` | interprets arguments, installs the title runtime BEFORE the `Game`, refuses an absent context or executor, and drives `Application`'s three stages |

### `game/cd/` — CD, libds and the disc (`namespace vagrant::cd`)

| File | Symbol | Responsibility |
|---|---|---|
| `cd_facts.h` | `kDsControl`, `kDsControlB`, `kCdCommand`, `kCdSync`, `kDiskState`, `kSystemState`, `kCommandDeadline`, `ownedControl` | the measured libcd/libds addresses and command classification this directory ships, with their provenance |
| `ds_control.{h,cpp}` | `handleDsControl` | the native body for the blocking `DsControlB` boundary: refuses an unowned command by name, establishes the measured libds Ready postcondition, and clears the retry deadline. It is BOUND at `cd::kDsControlB` by `execution/native_owners.cpp` — a body here that nothing installs is not an owner, and the guest's own libds wait behind it is unbounded |
| `cd_command.{h,cpp}` | `handleCdCommand` | the `CD_cw` leaf: the stock send, then the owed sync completion is recorded for the next field |
| `libds_field.{h,cpp}` | `LibDsField` (`commandSent`, `completeOwedCommand`) | the finite libds state transition formerly reached from the guest's VBlank callback, and the synchronous-`DsInit` Ready postcondition |
| `native_file.{h,cpp}` | `readNativeSectors`, `readNativeFile`, `readDiscSector`, `SectorTransfer`, `ReadSector` | acquire whole sectors and copy a measured file extent from the real disc into guest RAM; a failed read leaves guest RAM untouched |

### `game/boot/` — the boot spine (`namespace vagrant`, `vagrant::heap`, `vagrant::game_time`, `vagrant::guest`, `vagrant::resident`)

| File | Symbol | Responsibility |
|---|---|---|
| `application.{h,cpp}` | `Application`, `runApplication` | the ORDER the machine becomes a product: publish the resident image, bind peripherals, register native leaves, preflight the platform sync boundary, run the measured boot phase, enter the product loop, report the run-end census |
| `resident_image.{h,cpp}` | `readResidentImage`, `ResidentImage`, `kResidentImageName`, `kDiscEnvKey`, `kResidentFileBytes` | read the provisioned resident file whole, refuse any size but the measured one, and digest exactly the bytes about to be mapped |
| `resident_phase.{h,cpp}` | `ResidentPhase`, `ResidentCallServices`, `productionResidentCallServices`, `ResidentPhaseState` | the finite resident bootstrap and the start of TITLE reinitialisation: retail leaf order, with every measured guest field wait turned into an explicit host state; `TitleExecRunning` and `ExecTitleTailRunning` hand TITLE and the `vs_main_execTitle` tail to suspended guest calls |
| `exec_title_tail.{h,cpp}` | `ExecTitleTail` | `vs_main_execTitle` after `vs_title_exec` returns (0x80042BE0): continues the guest tail through `_loadBattlePrg` into `vs_battle_exec`, one suspended call across fields |
| `resident_facts.h` | `kCxxMain`, `kInitHeap`, `kTitlePrgLba`, `kGameTime`, `kTitleCallSite`, … | the resident addresses, offsets and load bases `ResidentPhase` ships |
| `game_time.{h,cpp}` | `game_time::advance` | the packed tick/frame/second/minute/hour transition from `vs_main_gametimeUpdate`, wherever a native field replaces it |
| `guest_rect.{h,cpp}` | `guest::writeRect` | materialise a PSX RECT in guest RAM; the one implementation of that field order |
| `game_heap.{h,cpp}` | `heap::initHeap`, `HeapHeader`, `kInitHeap`, `kArenaBase` | the measured `vs_main_initHeap` behaviour: seed heapA over the arena, leave heapB empty, preserve the ABI result registers |

### `game/execution/` — the guest-execution seam (`namespace vagrant`, `vagrant::dynarec`)

| File | Symbol | Responsibility |
|---|---|---|
| `dynarec_dispatch.{h,cpp}` | `installNativeOverride`, `callGuest`, `callReturning0..4`, `callGuestResumingToReturn`, `executeTurn`, `callOriginal`, `callOriginalResuming`, `callOriginalToReturn`, `requireGuestReturn`, `hasNativeOverride` | the entire title adapter surface over psxport's executor: the only place that spells a budget, resolves an image identity, or picks a dispatch form |
| `guest_phase.{h,cpp}` | `GuestPhase` | a suspended guest call that spans fields: begin, advance per field, abort on refusal |
| `native_owners.{h,cpp}` | `installResidentNativeOwners`, `NativeOwnerRegistration` | WHICH leaves the title owns for the resident generation, and the all-or-nothing registration bound to the generation that published them |

### `game/images/` — image residency and the cross-image call gates (`namespace vagrant`)

| File | Symbol | Responsibility |
|---|---|---|
| `overlay_images.{h,cpp}` | `OverlayImages`, `OverlayKind`, `OverlaySpec`, `OverlayLoadResult` | per-Core overlay residency: authenticate a complete input, publish it into its measured slot, and invalidate the generation it replaces |
| `title_transfer.{h,cpp}` | `readAndLoadTitle` | the completed resident-sector TITLE.PRG transfer: acquire the whole extent, then publish it as an executable image |
| `battle_transfer.{h,cpp}` | `readAndLoadBattle` | the `_loadBattlePrg` body: read BATTLE.PRG and INITBTL.PRG and publish both as executable images |
| `title_entry.{h,cpp}` | `validateTitleEntry`, `enterTitle` | admit only the measured resident-to-TITLE call, from the still-active resident generation into the just-published TITLE generation |

### `game/runtime/` — the per-Core composition root (`namespace vagrant`)

| File | Symbol | Responsibility |
|---|---|---|
| `vagrant_runtime.{h,cpp}` | `VagrantRuntime`, `ResidentHeaderFacts`, `kResidentHeader` | the title's `GameRuntime` policy: the measured guest program image, the measured `PlatformHlePlan`, the frame driver factory, and the authenticated PS-X header admission |
| `vagrant_context.{h,cpp}` | `VagrantContext`, `contextOf` | the per-Core aggregate of cohesive title owners, and the ONE accessor for it |

### `game/input/` — pad delivery (`namespace vagrant`, `vagrant::pad`)

| File | Symbol | Responsibility |
|---|---|---|
| `pad_delivery.{h,cpp}` | `PadDelivery` | service host/replay input once per native-owned field and adapt only Vagrant's measured byte order in the guest packet |
| `pad_facts.h` | `kSlot0Buffer`, `kDriverPointerTable` | the measured libpad packet addresses the delivery adapts |

### `game/render/` — render producers and the projection (`namespace vagrant`, `vagrant::gpu`, `vagrant::title_splash`, `vagrant::battle_projection`)

| File | Symbol | Responsibility |
|---|---|---|
| `battle_projection.{h,cpp}` | `BattleProjectionOwner`, `BattleProjectionPublication`, `WideBattleProjection`, `installBattleProjection`, `readPublishedArea`, `derive` | observe the guest's own viewport publication through the four resident SDK leaves, and derive (without publishing) the wide form |
| `battle_projection_facts.h` | `kSetGeomOffset`, `kSetGeomScreen`, `kSetDefDrawEnv`, `kSetDefDispEnv`, `kProjectionDistanceWord`, `wideningBlocker` | the measured publication addresses with their provenance, and the boundary that stops a widening |
| `battle_frame.{h,cpp}` | `BattleFrameProducer`, `prepareBattleField` | make a completed BATTLE guest field eligible for the frame driver's single commit |
| `title_splash.{h,cpp}` | `TitleSplashPhase`, `TitleSplashState` | the finite publisher/developer splash: each retail VSync becomes one return to the frame owner |
| `title_splash_facts.h` | `kMemset`, `kDrawImage`, `kSettings`, … | the measured TITLE.PRG addresses the splash phase ships |
| `title_startup.{h,cpp}` | `TitleStartupProducer`, `prepareTitleStartupField` | rebuild TITLE's immediate-sprite leaf from the guest ABI as native render-queue quads |
| `title_startup_recipe.{h,cpp}` | `TitleSpriteRecipe`, `PackedTitleSprite` | the pure decoder from the packed guest SPRT to semantic sprite arguments |
| `title_movie.{h,cpp}` | `TitleMovieProducer`, `prepareTitleMovieField` | publish a completed guest-decoded RGB24 movie frame from the MDEC callback boundary |
| `title_menu.{h,cpp}` | `TitleMenuProducer`, `prepareTitleMenuField` | flush each completed guest-built TITLE menu pass at the measured fence |
| `gpu_sync_facts.h` | `kTimeoutArm`, `kTimeoutDeadline`, `kTimeoutFlag` | the measured libgpu timeout-arm facts (RE-19/RE-21); the host completes GPU commands synchronously, so the arm is a declared platform service, never guest code |

### `game/save/` — memory card and save-file phases (`namespace vagrant`, `vagrant::title_memcard`, `vagrant::title_save`)

| File | Symbol | Responsibility |
|---|---|---|
| `title_memcard_init.{h,cpp}` | `TitleMemcardInit`, `TitleMemcardInitState` | the finite TITLE `_initMemcard`: exact disc reads for the extents, with allocation, pointer graph, image upload, reset policy and event lifecycle preserved. Reached from `TitleSaveCheck`, never as the guest leaf |
| `title_memcard_facts.h` | `kSpmcimgLba`, `kMcdataLba`, `kEventSpecs`, … | the measured TITLE memory-card addresses and extents |
| `title_save_check.{h,cpp}` | `TitleSaveCheck`, `TitleSaveCheckState` | the complete `_saveFileExists` stack: the `_initMemcard` poll through `TitleMemcardInit`, the game-time tail, card port/event polling, filename probe, shutdown and result |
| `title_save_facts.h` | `kStackFrameSize`, `kFilenameTemplatePointer`, … | the measured `_saveFileExists` addresses and offsets |

### `game/sync/` — the frame turn (`namespace vagrant`, `vagrant::sync`)

| File | Symbol | Responsibility |
|---|---|---|
| `frame_loop.{h,cpp}` | `VagrantFrameDriver`, `FrameServices`, `productionFrameServices`, `FieldOwner` | one finite display field: input, audio, measured producer arbitration, exactly one present, pacing, CD completion, and the finite-phase resume |
| `vsync_facts.h` | `kVSync`, `kVSyncWindowEnd`, `kVSyncQueryCounter` | the measured libetc VSync body and the field counter retail `VSync` polls |

### `game/*/**_facts.h` — measured title facts

The addresses, offsets, fields and load bases each owner ships, with their provenance (authenticated
bytes, the vendored CC0 module map, or both) and the contract they constrain. A borrowed address is a
hypothesis until it is read out of the SHA-bound image.

### `tools/`, `tests/`

| Path | Responsibility |
|---|---|
| `run.sh`, `bootstrap.py`, `tools/run.py`, `tools/launcher/` | the zero-argument product route: resolve arguments and the framework, provision the authenticated measured inputs, configure, build the one shipping executable, launch, and refuse naming the stage that failed |
| `tools/resolve_disc.py`, `tools/extract_exe.py`, `tools/extract_overlays.py`, `tools/discdump.py` | disc resolution and executable/overlay provisioning, each identity-checking what it writes |
| `tools/quality/structure.py` | mechanical retired-path, direct-diagnostic and file-size policy over the whole tree |
| `tools/verify.py` | the one gate: configure, compile coverage, every native contract, the product link, C++ policy, and the Python tests |
| `tests/` | the native contracts (CTest targets) and the launcher/provisioning Python tests |

## Who owns it

Each chain names the class and method at every hop.

### The frame turn

```text
psx::Machine::run                                        (framework; owns iteration)
  -> psx::Machine::stepFrame                              (framework)
       -> psx::frame::FieldTurn::beginField               (framework: answer a client pause/step, re-arm
                                                            the frame watchdog)
            -> vagrant::VagrantFrameDriver::stepFrame     (this title: the finite field)
                 services_.input    -> PadDelivery::serviceField
                 services_.audio    -> psxport spu_audio::frame
                 services_.titleStartup/titleMenu/battle/titleMovie -> the winning producer's present()
                 services_.present  -> psxport presentation.commit   (the ONE presentation fence)
                 services_.pace     -> framePacer.paceFrame (via core.game->framePacer)
                                     -> game.hle.irqPoll when PW_IRQ is pending
                 services_.libDs    -> cd::LibDsField::serviceField
                 services_.resumeResident -> TitleSplashPhase::advanceAfterField
                                          -> ResidentPhase::advanceAfterField
       -> psx::frame::FieldTurn::endField                 (framework: the mid-run RAM dump, then exactly
                                                            ONE queued control-channel command)
```

**Who owns the turn while a movie or a loading wait blocks.** Nothing in this title blocks one.
The intro movie is GUEST code: TITLE's own libpress path decodes and uploads each frame inside a
bounded guest turn, and `TitleMovieProducer::present` makes the completed frame eligible for the NEXT
field's single commit. A loading wait is a `ResidentPhase`/`TitleSplashPhase` state, not a call: the
measured guest VSync becomes an explicit host state and the next field's `resumeResident` resumes it.
The framework's own `psx::Fmv` is stepped rather than blocking for the same reason, and this title
does not use it. So the frame turn, the control channel and host input keep running for the whole
duration of both.

Guest code that spans fields (TITLE's menu loop, the `vs_main_execTitle` tail) runs as a `GuestPhase`: a
suspended `ResumableGuestCall` that VSync or an exhausted turn suspends and the next field resumes. The menu
producer presents only on a VSync suspension (`TitleMenu::frameCompleted`), never on an exhausted turn.

### Host input -> `Pad` -> guest pad buffer

```text
psx::input::HostInput                                     (framework: THE host input owner)
  -> psx::Pad::pollHostInput                              (framework: the ONE host pump — drains the
                                                            queue, resolves host/forced/REPL/replay)
       -> psx::Pad::serviceFrame                          (framework: per-frame resolve + write the packet)
            -> vagrant::PadDelivery::serviceField         (this title: the field boundary)
                 -> PadDelivery::normalizeButtonByteOrder (this title: Vagrant's measured high-byte-first
                                                            packet order, on the installed pointer table
                                                            or the fixed slot fallback)
```

The guest packet lands at `pad::kDriverPointerTable`-resolved buffers, falling back to
`pad::kSlot0Buffer`/`kSlot1Buffer`.

- **Movie skip**: the movie is guest code, so the guest reads the same serviced pad packet every
  field. A Start press therefore skips it through the identical host-input path, and a recorded run
  replays it.
- **Debug control channel**: `psx::frame::FieldTurn::endField` services exactly one queued command per field,
  and `DbgServer::honourPause` pumps `pollHostInput` while a run is paused, so the key that resumes it
  is seen.

### Guest draw -> presentation

```text
guest draw / VRAM upload
  -> a completed pass raises its producer's frameCompleted() (per-Core fence)
  -> vagrant::VagrantFrameDriver::stepFrame               (producer arbitration: startup, then menu,
                                                            then battle, then movie, else resident)
       -> the winning producer's present()                (flushed to the shared render queue)
            -> services_.present -> psxport presentation.commit   (the real 4:3 field)
```

- **Real field**: `presentation.commit` publishes the guest's 4:3 picture. That is the fidelity
  baseline.
- **60 fps in-between**: NOT PRESENTED for this title. The title presents 2 fields per game frame
  (30 fps) or 4 (15 fps), chosen at run time, so 60 fps is structurally impossible; interpolation
  would be a presentation decision over matching source geometry (issue 0039). `psxport` refuses
  `fps60=1` at startup for this title.
- **Widescreen**: NOT APPLIED. `BattleProjectionOwner::derive` ships and publishes nothing;
  `VagrantRuntime::guestWidescreenProjection()` is deliberately not overridden, so the framework
  resolves Standard 4:3. The horizontal projection word at `0x8005E248` is gameplay state (BATTLE
  branches on it), so the canvas would widen, never `H`.

### CD / streaming

```text
guest libds call
  -> cd::handleDsControlB                                (blocking CONTROL commands only; refuses by name)
  -> psxport's synchronous CD controller                  (the command completes before it returns)
  -> cd::LibDsField::completeSynchronousInit              (establishes the measured Ready postcondition)
       -> resident_phase calls it at DsInit

field boundary:
  -> FramePacer::paceFrame raises the real CD IRQ and arms PW_IRQ
  -> vagrant::VagrantFrameDriver::stepFrame sees PW_IRQ and calls game.hle.irqPoll
  -> cd::LibDsField::serviceField runs the finite guest field tick

bulk transfer (TITLE.PRG, menu WAVE, SPMCIMG/MCDATA):
  -> cd::readNativeSectors                                (whole sectors first, then RAM is written)
       -> cd::readNativeFile -> OverlayImages::loadTransfer -> readAndLoadTitle
```

The intro movie's STR/XA stream is still guest-owned; `TitleMovieProducer` owns only the completed
RGB24 frame's scanout boundary.

### Memory card

```text
_saveFileExists (0x8006E988, native TitleSaveCheck)
  -> TitleMemcardInit::invoke(1)                allocHeap, pointer graph, read SPMCIMG (0x14C98,0x1C000)
  -> per host field: TitleMemcardInit::invoke(0) SPMCIMG upload, read MCDATA+MCMAN (0x14CD0,0x2000),
                                               enableReset(0), 8x OpenEvent/EnableEvent -> 1
  -> _memcardEventHandler (guest 0x8006947C)    cardsInfo/cardLoad -> psxport libcard HLE delivers
                                               SwCARD EvSpIOE, so the port scan returns I/O end
  -> firstfile, then _shutdownMemcard (0x8006A6E0)
```

The libds CD-queue transfer retail uses for SPMCIMG.BIN and MCDATA.BIN+MCMAN.BIN is NOT dispatched:
its `Loaded` transition needs a CD-IRQ completion psxport's synchronous controller never raises
(issue 0044), so the extents are finite `NativeFile` reads of the same sectors. No word is written to
make a wait return, and the guest `_initMemcard` is asserted undispatched.

### Audio

```text
psx::Machine::stepFrame -> vagrant::VagrantFrameDriver::stepFrame
  -> services_.audio -> game.spu_audio.frame()           (psxport's SPU owner)
```

Title audio behaviour is entirely guest code today: `ResidentPhase` retains `_initSound`/`SetCDVolume`/
the four menu WAVE loads in retail order, and `xa_bind` plus `xa_*` are psxport's. No title-owned
audio synthesis exists yet (S014).

### Debug / control channel

```text
psx::Machine::attachControlChannel(port)                 (framework; always open on loopback)
  -> psxport dbg_server                                   (framework: the endpoint)
       -> one queued command per field, serviced by psx::frame::FieldTurn
            -> psx::Machine::stepFrame -> VagrantFrameDriver::stepFrame (guest state advances)
```

This title owns no debug command of its own yet. `PSXPORT_VAGRANT_DISC` is declared through
`VagrantRuntime::discEnvVar()`.

## Source tree

```text
game/  —  4,682 lines, 64 files
├─ boot/      1,107 lines, 13 files   the boot spine
├─ cd/          303 lines,  7 files   CD, libds and the disc
├─ execution/   404 lines,  4 files   the guest-execution seam
├─ images/      323 lines,  6 files   image residency and cross-image call gates
├─ input/        68 lines,  3 files   pad delivery
├─ render/     1,545 lines, 17 files   render producers and the projection
├─ runtime/     348 lines,  4 files   the per-Core composition root
├─ save/        373 lines,  6 files   memory card and save-file phases
└─ sync/        203 lines,  3 files   the frame turn
       main.cpp
tools/  —  1,015 lines,  7 files
tests/  —  2,945 lines, 12 files
```

Counted with `find <dir> -maxdepth 1 -type f \( -name '*.h' -o -name '*.cpp' -o -name '*.py' \)` and
`wc -l`; refresh it in the change that moves ownership.

## Where does new work go?

- Boot, overlay, ABI, camera or render constants measured from retail bytes → the owning typed
  module's `*_facts.h`, where the value carries its provenance, and the ordered evidence chain in
  `docs/re-frontier.md`.
- Execution-boundary mechanism (install a leaf, call a guest, re-enter the original) →
  `game/execution/dynarec_dispatch.{h,cpp}`, and nowhere else.
- WHICH leaves the title owns, and binding them to a generation → `game/execution/native_owners.{h,cpp}`,
  entered from the image publication boundary rather than from `registerOverrides`.
- Order of operations for the product → `game/boot/application.{h,cpp}`. It composes; it does not
  implement.
- Per-Core product state → its owner under `game/input/`, `game/render/`, `game/save/` or `game/sync/`,
  composed by `VagrantContext` and reached through `contextOf`.
- BATTLE world camera/projection/object production → the semantic BATTLE render owner described in
  `docs/battle-rendering.md`, never `BattleFrameProducer` or `BattleProjectionOwner`.
- Widescreen policy → the BATTLE guest projection publication owner. `derive()` is shipped; the
  widening is not, and that absence is what keeps the framework at 4:3.
- Interpolation → previous/current semantic snapshot ownership beside the BATTLE world producer; guest
  RAM and post-projection queue vertices are not interpolation sources.
- Framework-generic behavior → the single writable psxport checkout, not this consumer tree.
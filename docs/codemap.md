# Vagrant Story codemap

This map answers which subsystem owns each responsibility, where it lives, and where related work
belongs. Capability status is authoritative in `docs/project-state.md`; epic intent is in
`docs/project-goals.md`; atomic work is in `docs/issues/`.

## Architecture

The target host composes one title adapter over psxport's per-Core dynarec executor. Input, rendering,
synchronization, CD, save, and game semantics remain peer owners collected by `VagrantContext`.
Framework platform services stay under `external/psxport`; this repo owns Vagrant-specific facts,
title composition, RE instruments, and native game behavior.

```text
run.sh -> bootstrap.py -> tools/run.py -> tools/launcher/runtime_boundary.py
       -> vagrant_port (game/main.cpp) -> vagrant::Application
       -> vagrant::dynarec -> psxport dynarec executor -> VagrantContext
                                                    |
                                                    +-- VagrantFrameDriver
                                                    +-- PadDelivery
                                                    +-- TITLE presentation products
                                                    +-- TITLE save/memcard finite products
                                                    +-- CD owners
                                                    +-- BattleFrameProducer

verified retail inputs -> SHA-bound executable/overlay bytes -> measured facts / narrow owners
verified retail inputs -> psxport runtime image mapping -> dynarec execution
```

## Subsystems

| Subsystem | Responsibility | Current / target location | Entry point | Deep doc |
|---|---|---|---|---|
| Player launcher | Interpret arguments, resolve the framework, provision the authenticated measured inputs, configure, build the one shipping executable, launch it, and refuse with the STAGE that failed | `run.sh`, `bootstrap.py`, `tools/run.py`, `tools/launcher/runtime_boundary.py` | `bootstrap.main`, `run.main`, `provision_build_and_launch` | `README.md` |
| Retail input resolution | Apply explicit argument, environment, `.env`, then drop-in precedence and refuse missing/ambiguous assets | `tools/resolve_disc.py` | `resolve_disc` | `docs/references.md` |
| Executable/overlay provisioning | Extract and identity-check the resident executable and reached overlay images | `tools/extract_exe.py`, `tools/extract_overlays.py`, `tools/discdump.py` | each tool's `main` | `docs/references.md` |
| Dynarec title adapter | THE adapter surface over psxport's per-`Core` executor: image-scoped override installation, finite call, bounded turn, original call, and a named fatal on a call that did not return. Nothing else in this repository resolves an image identity, spells a budget, or chooses a dispatch form, so there is one answer to each | `game/core/dynarec_dispatch.{h,cpp}` | `vagrant::dynarec::installNativeOverride`, `callGuest`, `executeTurn`, `callOriginal` | `CLAUDE.md` |
| Image-scoped native leaves | WHICH leaves the title owns and the all-or-nothing registration that binds them to the generation that published them. Reached from the resident publication boundary, because `registerOverrides` runs before any image exists | `game/core/native_owners.{h,cpp}` | `vagrant::installResidentNativeOwners` | `CLAUDE.md` |
| Execution census | The boundaries this title itself crosses — override installs with their refusal reasons, override invocations by name, executable-write candidates with the ranges they overlapped, original calls, and dispatches by typed exit reason — each with the denominator that makes its zero readable. psxport's own executor counters are read from the executor, never restated | `game/core/execution_telemetry.{h,cpp}` | `vagrant::ExecutionTelemetry::report` | `docs/issues/0040` |
| Resident image admission | Read the provisioned file whole, refuse any size other than the measured one, and digest exactly the bytes about to be mapped. It deliberately does NOT re-derive the file's SHA-1: that is `tools/extract_exe.py`'s rule, and a second hash would be a second answer | `game/core/resident_image.{h,cpp}` | `vagrant::readResidentImage` | `docs/issues/0040` |
| Process composition | The one place that knows the ORDER the machine becomes a product: construct, publish the resident image, bind peripherals, register leaves, preflight the platform sync boundary, run the measured boot phase, step finite fields, report the run-end census | `game/core/application.{h,cpp}`, entered by `game/main.cpp` | `vagrant::Application::start`, `run`, `reportRunEnd` | `docs/issues/0040` |
| Image residency and entry gates | Compose authenticated resident/overlay images, typed exits, image generations, and invalidation | `game/core/vagrant_runtime.{h,cpp}` for resident admission and per-Core context lifetime; `game/core/overlay_images.{h,cpp}` for overlay residency; `game/core/title_transfer.{h,cpp}` for completed resident-sector publication; `game/core/title_entry.{h,cpp}` for the resident-to-TITLE call gate | `vagrant::VagrantRuntime::loadResidentImage`, `vagrant::VagrantRuntime::createContext`, `vagrant::readAndLoadTitle`, `vagrant::OverlayImages::loadTransfer`, `vagrant::enterTitle` | `CLAUDE.md` |
| Runtime composition | Hold cohesive per-Core title owners, the image-residency owner, and the per-Core execution census without absorbing their behavior. `vagrant::contextOf(Core&)` is the ONE accessor for a Core's title products | `game/core/vagrant_context.{h,cpp}` | `vagrant::VagrantContext`, `vagrant::contextOf` | `CLAUDE.md` |
| CD/libds behavior | Classify the measured blocking control owners, establish the libds postcondition, and copy finite resident/TITLE extents from the real disc | `game/cd/cd_facts.h`, `game/cd/ds_control.cpp`, `game/cd/libds_field.{h,cpp}`, `game/cd/native_file.{h,cpp}` | `vagrant::cd::handleDsControlB`, `vagrant::cd::LibDsField`, `readNativeFile` | `CLAUDE.md` |
| GPU/libgpu synchronization | Retain the measured hardware-timeout facts whose host GPU operation completes synchronously; keep guest VSync fatal | `game/render/gpu_sync_facts.h` | future title-adapter binding | `CLAUDE.md` |
| Resident/TITLE finite phase | Reproduce resident leaf/state order, native-own InitCARD/loading/CD waits and TITLE.PRG entry, then compose cohesive splash and save-phase owners | `game/core/resident_facts.h`, `game/core/resident_phase.{h,cpp}`, `game/render/title_splash.{h,cpp}`, `game/render/title_splash_facts.h` | `ResidentPhase::advanceAfterField`, `TitleSplashPhase::advanceAfterField` | `CLAUDE.md` |
| Packed game time | Preserve the measured tick/frame/second/minute/hour transition wherever a native field replaces resident `gametimeUpdate` | `game/core/game_time.{h,cpp}` | `vagrant::game_time::advance` | `CLAUDE.md` |
| TITLE save-file phase | Own the complete `_saveFileExists` stack, game-time tail, memory-card port/event polling, filename probe, shutdown, and result without dispatching guest field waits | `game/save/title_save_check.{h,cpp}`, `game/save/title_save_facts.h` | `TitleSaveCheck::begin`, `TitleSaveCheck::advanceAfterField` | `CLAUDE.md` |
| TITLE memory-card initialization | Replace the incompatible interrupt-driven SPMCIMG/MCDATA/MCMAN queue with exact finite disc reads while preserving allocation, pointer graph, image upload, reset policy, and event lifecycle | `game/save/title_memcard_init.{h,cpp}`, `game/save/title_memcard_facts.h` | `TitleMemcardInit::invoke` | `CLAUDE.md` |
| Pad delivery | Service host/replay input once per native-owned field and adapt only the measured retail byte order | `game/input/pad_delivery.h`, `game/input/pad_delivery.cpp`, `game/input/pad_facts.h` | `vagrant::PadDelivery::serviceField` | `CLAUDE.md` |
| Native field loop | Own one finite resident/TITLE/BATTLE field: host frame index, input, audio, measured producer arbitration, exactly one present, and pacing; declare measured guest VSync fatal | `game/sync/frame_loop.h`, `game/sync/frame_loop.cpp`, `game/sync/vsync_facts.h` | `vagrant::VagrantFrameDriver::stepFrame` | `CLAUDE.md` |
| TITLE startup picture | Decode the immediate-sprite ABI and rebuild that semantic leaf from guest-uploaded texture state | `game/render/title_startup.h`, `game/render/title_startup.cpp`, `game/render/title_startup_recipe.h`, `game/render/title_startup_recipe.cpp` | `vagrant::TitleStartupProducer` | `CLAUDE.md` |
| TITLE movie presentation | Publish completed guest-decoded RGB24 frames from the measured MDEC callback boundary | `game/render/title_movie.h`, `game/render/title_movie.cpp` | `vagrant::TitleMovieProducer` | `CLAUDE.md` |
| TITLE menu presentation | Publish each completed guest-built menu pass from the measured fence | `game/render/title_menu.h`, `game/render/title_menu.cpp` | `vagrant::TitleMenuProducer` | `CLAUDE.md` |
| BATTLE field fence | Retain the measured BATTLE presenter and prepare its completed guest-translated field for the frame driver's single commit | `game/render/battle_frame.h`, `game/render/battle_frame.cpp` | `vagrant::BattleFrameProducer` | `docs/battle-rendering.md` |
| BATTLE guest projection publication | Own the four measured resident SDK leaves the guest states its viewport through: PERFORM each leaf's measured retail effect (the GTE leaves through psxport's public GTE primitive, the two env leaves by running the ORIGINAL guest body) and then measure the publication from the coprocessor, the framework's record and the word the leaf itself just filled, derive the wide publication, and refuse rather than publish a centre-only move that would crop the field. The bodies behind those addresses are read from the authenticated bytes — the BATTLE overlay publication and the RESIDENT boot's, where the boot's own horizontal extent is a per-call `env + 4` word rather than a constant — so the derivation rests on instruction words rather than on a reconstruction. **A leaf is observed, never replaced**: the two env leaves re-enter the ORIGINAL guest body through psxport's own `psx::cpu::callOriginalToReturn` (`runtime/cpu/native_dispatch.h:96`), which ABORTS on a budget exit — correct for a 12-to-20-instruction leaf, and the reason `vs_main_initHeap` keeps its own bounded resume | `game/render/battle_projection.{h,cpp}`, with the facts and the decompilation-symbol table in `game/render/battle_projection_facts.h` | `vagrant::BattleProjectionOwner::derive`, `vagrant::BattleProjectionOwner::readPublishedArea`, `vagrant::installBattleProjection` | `docs/issues/0038-the-projection-bodies-are-read-from-bytes-now.md`, `docs/issues/0042-fallback-calls-is-zero-and-the-projection-owner-was-replacing-four-resident-leaves.md` |
| BATTLE semantic world production | Read named pre-GTE camera/object/material state and build faithful 4:3 native world geometry; own later widescreen and interpolation inputs | target: game/render/battle_world.{h,cpp}, with cohesive camera/object peers as their semantics are measured | target: `vagrant::BattleWorldProducer` | `docs/battle-rendering.md` |
| Native game heap | Implement the measured readable game-heap behavior; the future title adapter owns image-scoped registration and original calls | `game/core/game_heap.h`, `game/core/game_heap.cpp` | `vagrant::heap::initHeap` | `docs/references.md` |
| Measured title facts | The addresses, offsets, fields and load bases each owner ships, with their provenance (authenticated bytes, the vendored CC0 module map, or both) and the contract they constrain. A borrowed address is a hypothesis until it is read out of the SHA-bound image | `game/*/**_facts.h`, `game/render/battle_projection_facts.h` | the `inline constexpr` tables beside their owners | `CLAUDE.md` |
| Field cadence | Fields consumed per game frame, which decides whether an interpolated 60 fps path is in scope. MEASURED at 2 (30 fps) or 4 (15 fps) chosen at run time, never 60; the 2-vs-4 choice is PRESENTATION because every consumer scales its per-step increment by the same value that scales the field wait | `docs/issues/0039` | `docs/issues/0039` | — | `docs/issues/0039` | | `docs/issues/0039` |
| Verification | Build and run current C++ image and native-owner contracts, enforce compile coverage and C++ policy, and exercise launcher, provisioning, and structure contracts | `CMakeLists.txt`, `tests/`, `tools/verify.py`, `tools/quality/structure.py`, shared `external/psxport/tools/check_cpp_style.py` | `verify.main`, CTest and Python test mains | `README.md` |
| Atomic work | One open defect, missing capability, or blocker per file | `docs/issues/` | — | `docs/project-state.md` |
| Framework platform layer | Own Lightrec execution, PSX hardware services, rendering backend, UI, configuration, and shared presentation mechanisms | `external/psxport/` | target per-Core executor API | `external/psxport/CLAUDE.md` |

## Source tree

```text
game/  —  4,955 lines, 69 files
├─ cd/     324 lines,  8 files
├─ core/ 2,323 lines, 27 files
├─ input/   68 lines,  3 files
├─ render/ 1,665 lines, 17 files
├─ save/   364 lines,  6 files
├─ sync/   211 lines,  3 files
└─ main.cpp
tools/ —  1,938 lines,  9 files
tests/ —  2,891 lines, 12 files
```

Counted with `find <dir> -maxdepth 1 -type f \( -name '*.h' -o -name '*.cpp' -o -name '*.py' \)` and
`wc -l`; refresh it in the change that moves ownership. The `codemap.py tree` invocation this
note used to name does not exist in this repository, so the numbers were being carried by hand.

## Where does new work go?

- Boot, overlay, ABI, camera, or render constants measured from retail bytes → the owning typed
  module's `*_facts.h`, where the value carries its provenance.
- Execution-boundary mechanism (install a leaf, call a guest, re-enter the original) →
  `game/core/dynarec_dispatch.{h,cpp}`. Never spell an `ExecutionBudget` or resolve an image
  identity anywhere else; `vagrant::dynarec` is the only place that may.
- WHICH leaves the title owns, and binding them to a generation → `game/core/native_owners.{h,cpp}`,
  entered from the image publication boundary rather than from `registerOverrides`.
- A new execution counter → `game/core/execution_telemetry.{h,cpp}`, with the denominator it is read
  against.
- Order of operations for the product → `game/core/application.{h,cpp}`. It composes; it does not
  implement. Image residency belongs to `game/core/overlay_images.{h,cpp}`, resident-to-TITLE call
  admission to `game/core/title_entry.{h,cpp}`, and everything else to its cohesive peer subsystem.
- Per-Core product state → its owner under `game/input/`, `game/render/`, `game/save/`, or `game/sync/`, composed by
  `VagrantContext`.
- BATTLE world camera/projection/object production → the semantic BATTLE render owner described in
  `docs/battle-rendering.md`, never `BattleFrameProducer` or the legacy callback bag.
- Widescreen policy → the BATTLE guest projection publication owner for the horizontal centre and
  clip; fixed 2D layers keep their own policies. `VagrantRuntime::guestWidescreenProjection()` stays
  UNOVERRIDDEN, and the reason is the guest's DISPLAY RESOLUTION through `SetDefDispEnv` rather than
  the 256 in the display `screen` rect — the bytes REFUTED that being a clip (issue 0038 corrects
  0037's reason, not its outcome). `derive()` is shipped; the widening is not, and the absence is what
  keeps the framework at 4:3.
- Interpolation → previous/current semantic snapshot ownership beside the BATTLE world producer;
  guest RAM and post-projection queue vertices are not interpolation sources.
- Framework-generic behavior → the single writable psxport checkout, not this consumer tree.

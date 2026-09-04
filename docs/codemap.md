# Vagrant Story codemap

This map answers which subsystem owns each responsibility, where it lives, and where related work
belongs. Capability status is authoritative in `docs/project-state.md`; epic intent is in
`docs/project-goals.md`; atomic work is in `docs/issues/`; ordered binary evidence is in
`docs/re-frontier.md`.

## Architecture

The target host composes one title adapter over psxport's per-Core dynarec executor. Input, rendering,
synchronization, CD, save, and game semantics remain peer owners collected by `VagrantContext`.
Framework platform services stay under `external/psxport`; this repo owns Vagrant-specific facts,
title composition, RE instruments, and native game behavior.

```text
run.sh -> bootstrap.py -> tools/run.py -> missing title/dynarec adapter boundary

target: title adapter -> psxport dynarec executor -> VagrantContext
                                                    |
                                                    +-- VagrantFrameDriver
                                                    +-- PadDelivery
                                                    +-- TITLE presentation products
                                                    +-- TITLE save/memcard finite products
                                                    +-- CD owners
                                                    +-- BattleFrameProducer

verified retail inputs -> tools/re_* instruments -> measured facts / narrow owners
verified retail inputs -> psxport runtime image mapping -> dynarec execution
```

## Subsystems

| Subsystem | Responsibility | Current / target location | Entry point | Deep doc |
|---|---|---|---|---|
| Player launcher | Handle help and expose the one explicit unavailable-product boundary until the dynarec adapter exists | `run.sh`, `bootstrap.py`, `tools/run.py`, `tools/launcher/runtime_boundary.py` | `bootstrap.main`, `run.main`, `require_product` | `README.md` |
| Retail input resolution | Apply explicit argument, environment, `.env`, then drop-in precedence and refuse missing/ambiguous assets | `tools/resolve_disc.py` | `resolve_disc` | `docs/references.md` |
| Executable/overlay provisioning | Extract and identity-check the resident executable and reached overlay images | `tools/extract_exe.py`, `tools/extract_overlays.py`, `tools/discdump.py` | each tool's `main` | `docs/references.md` |
| Dynarec title adapter | Compose the authenticated resident/overlay images, typed exits, image generations, invalidation, and image-scoped native handlers against psxport | composition root: `game/core/vagrant_context.h`; split into a dedicated title-adapter module when the shared API lands | target: `vagrant::TitleAdapter` | `CLAUDE.md` |
| Process composition | Load typed configuration, construct the title adapter and peer owners, and enter the bounded product loop | boundary: `tools/launcher/runtime_boundary.py`; future C++ application owner beside the title adapter | target: `vagrant::Application` | `CLAUDE.md` |
| Runtime composition | Hold cohesive per-Core title owners without absorbing their behavior | `game/core/vagrant_context.h` | `vagrant::VagrantContext` | `CLAUDE.md` |
| CD/libds behavior | Classify the measured blocking control owners, establish the libds postcondition, and copy finite resident/TITLE extents from the real disc | `game/cd/cd_facts.h`, `game/cd/ds_control.cpp`, `game/cd/libds_field.{h,cpp}`, `game/cd/native_file.{h,cpp}` | `vagrant::cd::handleDsControlB`, `vagrant::cd::LibDsField`, `readNativeFile` | `docs/re-frontier.md` |
| GPU/libgpu synchronization | Retain the measured hardware-timeout facts whose host GPU operation completes synchronously; keep guest VSync fatal | `game/render/gpu_sync_facts.h` | future title-adapter binding | `docs/re-frontier.md` |
| Resident/TITLE finite phase | Reproduce resident leaf/state order, native-own InitCARD/loading/CD waits and TITLE.PRG entry, then compose cohesive splash and save-phase owners | `game/core/resident_facts.h`, `game/core/resident_phase.{h,cpp}`, `game/render/title_splash.{h,cpp}`, `game/render/title_splash_facts.h` | `ResidentPhase::advanceAfterField`, `TitleSplashPhase::advanceAfterField` | `docs/re-frontier.md` |
| Packed game time | Preserve the measured tick/frame/second/minute/hour transition wherever a native field replaces resident `gametimeUpdate` | `game/core/game_time.{h,cpp}` | `vagrant::game_time::advance` | `docs/re-frontier.md` |
| TITLE save-file phase | Own the complete `_saveFileExists` stack, game-time tail, memory-card port/event polling, filename probe, shutdown, and result without dispatching guest field waits | `game/save/title_save_check.{h,cpp}`, `game/save/title_save_facts.h` | `TitleSaveCheck::begin`, `TitleSaveCheck::advanceAfterField` | `docs/re-frontier.md` |
| TITLE memory-card initialization | Replace the incompatible interrupt-driven SPMCIMG/MCDATA/MCMAN queue with exact finite disc reads while preserving allocation, pointer graph, image upload, reset policy, and event lifecycle | `game/save/title_memcard_init.{h,cpp}`, `game/save/title_memcard_facts.h` | `TitleMemcardInit::invoke` | `docs/re-frontier.md` |
| Pad delivery | Service host/replay input once per native-owned field and adapt only the measured retail byte order | `game/input/pad_delivery.h`, `game/input/pad_delivery.cpp`, `game/input/pad_facts.h` | `vagrant::PadDelivery::serviceField` | `docs/re-frontier.md` |
| Native field loop | Own one finite resident/TITLE/BATTLE field: host frame index, input, audio, measured producer arbitration, exactly one present, and pacing; declare measured guest VSync fatal | `game/sync/frame_loop.h`, `game/sync/frame_loop.cpp`, `game/sync/vsync_facts.h` | `vagrant::VagrantFrameDriver::stepFrame` | `docs/re-frontier.md` |
| TITLE startup picture | Decode the immediate-sprite ABI and rebuild that semantic leaf from guest-uploaded texture state | `game/render/title_startup.h`, `game/render/title_startup.cpp`, `game/render/title_startup_recipe.h`, `game/render/title_startup_recipe.cpp` | `vagrant::TitleStartupProducer` | `docs/re-frontier.md` |
| TITLE movie presentation | Publish completed guest-decoded RGB24 frames from the measured MDEC callback boundary | `game/render/title_movie.h`, `game/render/title_movie.cpp` | `vagrant::TitleMovieProducer` | `docs/re-frontier.md` |
| TITLE menu presentation | Publish each completed guest-built menu pass from the measured fence | `game/render/title_menu.h`, `game/render/title_menu.cpp` | `vagrant::TitleMenuProducer` | `docs/re-frontier.md` |
| BATTLE field fence | Retain the measured BATTLE presenter and prepare its completed guest-translated field for the frame driver's single commit | `game/render/battle_frame.h`, `game/render/battle_frame.cpp` | `vagrant::BattleFrameProducer` | `docs/battle-rendering.md` |
| BATTLE semantic world production | Read named pre-GTE camera/object/material state and build faithful 4:3 native world geometry; own later widescreen and interpolation inputs | target: game/render/battle_world.{h,cpp}, with cohesive camera/object peers as their semantics are measured | target: `vagrant::BattleWorldProducer` | `docs/battle-rendering.md` |
| Native game heap | Implement the measured readable game-heap behavior; the future title adapter owns image-scoped registration and original calls | `game/core/game_heap.h`, `game/core/game_heap.cpp` | `vagrant::heap::initHeap` | `docs/references.md` |
| RE instruments | Measure shipping facts from SHA-bound executable/overlay bytes and gate every shipped constant/owner against its source | `tools/re_crt0.py`, `tools/re_overlay.py`, `tools/re_frame.py`, `tools/re_title_natural.py`, and peer `tools/re_*.py` | each tool's `measure` / `main` | `docs/re-frontier.md` |
| Verification | Exercise the launcher refusal, provisioning policy, structure rules, measured contracts, and later dynarec integration through hermetic positive/refusal cases | `tests/`, `tools/verify.py`, `tools/quality/structure.py` | `verify.main`, Python test mains | `CLAUDE.md` |
| Project registries | Query proof, instrument trust, atomic issues, and ordered RE dependencies | `tools/info.py`, `tools/catalog.py`, `tools/re_frontier.py`, `docs/info/`, `docs/issues/`, `docs/re-frontier.md` | each tool's `main` | — |
| Framework platform layer | Own Lightrec execution, PSX hardware services, rendering backend, UI, configuration, and shared presentation mechanisms | `external/psxport/` | target per-Core executor API | `external/psxport/CLAUDE.md` |

## Source tree

```text
game/  —  2,321 lines, 44 files
├─ cd/     270 lines, 8 files
├─ core/   747 lines, 10 files
├─ input/   68 lines, 3 files
├─ render/ 675 lines, 14 files
├─ save/   362 lines, 6 files
└─ sync/   199 lines, 3 files
tools/ — 10,271 lines, 33 files
tests/ —    921 lines, 8 files
```

Refresh this annotated tree with
`codemap.py tree game tools tests --depth 2 --min-lines 1` when source ownership moves.

## Where does new work go?

- Boot, overlay, ABI, camera, or render constants measured from retail bytes → the narrow matching
  `tools/re_*.py` instrument first, then the owning typed module.
- New runtime orchestration → split a dedicated title-adapter module from
  `game/core/vagrant_context.h` when the shared API lands; implementation stays in its cohesive peer
  subsystem.
- Per-Core product state → its owner under `game/input/`, `game/render/`, `game/save/`, or `game/sync/`, composed by
  `VagrantContext`.
- BATTLE world camera/projection/object production → the semantic BATTLE render owner described in
  `docs/battle-rendering.md`, never `BattleFrameProducer` or the legacy callback bag.
- Widescreen policy → the BATTLE semantic world camera/projection owner; fixed 2D layers keep their
  own policies.
- Interpolation → previous/current semantic snapshot ownership beside the BATTLE world producer;
  guest RAM and post-projection queue vertices are not interpolation sources.
- Framework-generic behavior → the single writable psxport checkout, not this consumer tree.

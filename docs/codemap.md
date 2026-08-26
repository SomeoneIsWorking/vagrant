# Vagrant Story codemap

This map answers which subsystem owns each responsibility, where it lives, and where related work
belongs. Capability status is authoritative in `docs/project-state.md`; epic intent is in
`docs/project-goals.md`; atomic work is in `docs/issues/`; ordered binary evidence is in
`docs/re-frontier.md`.

## Architecture

The host shape follows Dusklight's composition boundary: the process entry installs one runtime,
the runtime composes cohesive per-Core products, and input, rendering, synchronization, CD, and game
semantics remain peer owners. Framework platform services stay under `external/psxport`; this repo
owns Vagrant-specific facts, runtime composition, RE instruments, and native game behavior.

```text
run.sh -> bootstrap.py -> tools/run.py
                              |
game/core/main.cpp -> VagrantRuntime -> VagrantContext
                              |             |
                              |             +-- PadDelivery
                              |             +-- TITLE presentation products
                              |             +-- BattleFrameProducer
                              |
                              +-- CD / VBlank override owners
                              +-- native game overrides

verified retail inputs -> tools/re_* instruments -> measured facts / narrow owners
verified retail inputs -> psxport emitter -> generated/ substrate (derived, never edited)
```

## Subsystems

| Subsystem | Responsibility | Current / target location | Entry point | Deep doc |
|---|---|---|---|---|
| Player launcher | Resolve the framework and disc, provision derived inputs, configure/build the current product, and launch it | `run.sh`, `bootstrap.py`, `tools/run.py` | `bootstrap.main`, `run.main` | `README.md` |
| Retail input resolution | Apply explicit argument, environment, `.env`, then drop-in precedence and refuse missing/ambiguous assets | `tools/resolve_disc.py` | `resolve_disc` | `docs/references.md` |
| Executable/overlay provisioning | Extract and identity-check the resident executable and reached overlay images | `tools/extract_exe.py`, `tools/extract_overlays.py`, `tools/discdump.py` | each tool's `main` | `docs/references.md` |
| Generated substrate orchestration | Hash verified inputs and emitter version, regenerate when required, and enforce reached entries | `tools/ensure_recomp.py`, `game/recomp_seeds.json`, `game/core/recomp_register.cpp` | `ensure_recomp.main`, generated registry install | `docs/re-frontier.md` |
| Process composition | Install one process-lifetime game runtime and enter the measured resident boot | `game/core/main.cpp` | `main` | `CLAUDE.md` |
| Runtime composition | Own direct-runtime/render-capability policy, typed guest image facts, override registration, and per-Core product lifetime | `game/core/vagrant_runtime.h`, `game/core/vagrant_runtime.cpp`, `game/core/vagrant_context.h` | `vagrant::VagrantRuntime` | `CLAUDE.md` |
| Legacy compatibility seam | Project measured static facts and unmigrated callbacks into psxport's bounded adapter; no new behavior belongs here | `game/core/game_config.cpp`, `game/core/game_hooks.cpp`, `game/core/legacy_game_interface.h` | `vagrant::legacy::measuredConfig`, `vagrant::legacy::compatibilityHooks` | `docs/re-frontier.md` |
| CD/libds behavior | Classify the measured blocking control owner and compose native drive semantics while retaining guest state-machine effects | `game/cd/ds_control.cpp`, `game/cd/ds_control_contract.h` | `vagrant_cd_register_overrides` | `docs/re-frontier.md` |
| Pad delivery | Service host/replay input once per guest field and adapt only the measured retail byte order | `game/input/pad_delivery.h`, `game/input/pad_delivery.cpp`, `game/input/pad_facts.h` | `vagrant::PadDelivery::service` | `docs/re-frontier.md` |
| Guest field timing | Register and dispatch the measured resident VBlank handler, then arbitrate completed presentation products | `game/sync/vblank.h`, `game/sync/vblank.cpp` | `vagrant_vblank_turn` | `docs/re-frontier.md` |
| TITLE startup picture | Decode the immediate-sprite ABI and rebuild that semantic leaf from guest-uploaded texture state | `game/render/title_startup.h`, `game/render/title_startup.cpp`, `game/render/title_startup_recipe.h`, `game/render/title_startup_recipe.cpp` | `vagrant::TitleStartupProducer` | `docs/re-frontier.md` |
| TITLE movie presentation | Publish completed guest-decoded RGB24 frames from the measured MDEC callback boundary | `game/render/title_movie.h`, `game/render/title_movie.cpp` | `vagrant::TitleMovieProducer` | `docs/re-frontier.md` |
| TITLE menu presentation | Publish each completed guest-built menu pass from the measured fence | `game/render/title_menu.h`, `game/render/title_menu.cpp` | `vagrant::TitleMenuProducer` | `docs/re-frontier.md` |
| BATTLE field fence | Retain the measured BATTLE presenter and publish its completed guest-translated field at guest VBlank | `game/render/battle_frame.h`, `game/render/battle_frame.cpp` | `vagrant::BattleFrameProducer` | `docs/battle-rendering.md` |
| BATTLE semantic world production | Read named pre-GTE camera/object/material state and build faithful 4:3 native world geometry; own later widescreen and interpolation inputs | target: game/render/battle_world.{h,cpp}, with cohesive camera/object peers as their semantics are measured | target: `vagrant::BattleWorldProducer` | `docs/battle-rendering.md` |
| Native game heap | Implement measured readable game-heap behavior and register retained substrate supers | `game/core/game_heap.h`, `game/core/game_heap.cpp` | `vagrant::heap::initHeap` | `docs/references.md` |
| RE instruments | Measure shipping facts from SHA-bound executable/overlay bytes and gate every shipped constant/owner against its source | `tools/re_crt0.py`, `tools/re_overlay.py`, `tools/re_frame.py`, `tools/re_title_natural.py`, and peer `tools/re_*.py` | each tool's `measure` / `main` | `docs/re-frontier.md` |
| Verification | Exercise shipping seams, launcher/provisioning policy, measured contracts, and C++ quality through hermetic positive/refusal cases | `tests/`, `CMakeLists.txt`, `cmake/vagrant_port.cmake` | CTest targets and Python test mains | `CLAUDE.md` |
| Project registries | Query proof, instrument trust, atomic issues, and ordered RE dependencies | `tools/info.py`, `tools/catalog.py`, `tools/re_frontier.py`, `docs/info/`, `docs/issues/`, `docs/re-frontier.md` | each tool's `main` | — |
| Framework platform layer | Own MIPS execution, PSX hardware services, rendering backend, UI, configuration, and shared presentation mechanisms | `external/psxport/` | `GameRuntime` / `psxport_install_game` seam | `external/psxport/CLAUDE.md` |

## Source tree

```text
game/  —  1,642 lines, 27 files
├─ cd/      74 lines, 2 files
├─ core/   838 lines, 10 files
├─ input/   69 lines, 3 files
├─ render/ 575 lines, 10 files
└─ sync/     86 lines, 2 files
tools/ — 9,080 lines, 25 files
tests/ —   593 lines, 6 files
```

Refresh this annotated tree with
`codemap.py tree game tools tests --depth 2 --min-lines 1` when source ownership moves.

## Where does new work go?

- Boot, overlay, ABI, camera, or render constants measured from retail bytes → the narrow matching
  `tools/re_*.py` instrument first, then the owning typed module.
- New runtime orchestration → `game/core/vagrant_runtime.cpp`; implementation stays in its cohesive
  peer subsystem.
- Per-Core product state → its owner under `game/input/`, `game/render/`, or `game/sync/`, composed by
  `VagrantContext`.
- BATTLE world camera/projection/object production → the semantic BATTLE render owner described in
  `docs/battle-rendering.md`, never `BattleFrameProducer` or the legacy callback bag.
- Widescreen policy → the BATTLE semantic world camera/projection owner; fixed 2D layers keep their
  own policies.
- Interpolation → previous/current semantic snapshot ownership beside the BATTLE world producer;
  guest RAM and post-projection queue vertices are not interpolation sources.
- Framework-generic behavior → the single writable psxport checkout, not this consumer tree.

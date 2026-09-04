# RE frontier — Vagrant Story

This ledger orders binary evidence needed by the native/dynarec hybrid. It does not describe an
offline code-generation workflow. Historical run observations remain evidence, but they do not
claim that a current executable exists.

The break-first migration removed the old product before replacement. The sole implementation
boundary is now: authenticate and map the resident executable and each loaded PRG image into
psxport's dynarec-only executor, then register the retained semantic native owners against the
correct image generation. No interpreter is permitted during gameplay; interpretation may exist
only in isolated tests.

Statuses: `re-verified`, `re-partial`, `in-progress`, `todo`, `skip-by-design`, `blocked`.

## Boot and image identity

### RE-01 — authenticated resident executable and crt0 layout
- status: re-verified
- deps:
- evidence: The owned `SLUS_010.40` has SHA-1 `fababcfd4325d42f350d95b3472874affeb0e48c`,
  entry `0x8001F544`, and loaded range `[0x80010000,0x80062000)`. Prior executable-backed
  measurement established bss `[0x80033678,0x800401A8)`, computed stack `0x801FFFF8`, gp
  `0x80033674`, inert BIOS heap declaration at `0x800401A8`, libc init `0x80026864`, and game main
  `0x80042C38`. `tools/re_crt0.py` now owns only authenticated image inspection shared by the other
  RE instruments.
- where: `tools/extract_exe.py`, `tools/re_crt0.py`, `docs/references.md`
- gap: The future title adapter must apply the measured boot contract through psxport's dynarec
  entry path.

### RE-02 — resident runtime mapping and entry
- status: todo
- deps: RE-01
- evidence: The exact resident image identity, load range, and entry are verified by RE-01.
- where: intended title adapter named in `docs/codemap.md`
- gap: Map the authenticated image, enter `0x8001F544`, and prove all gameplay guest execution is
  dynarec-only.

### RE-03 — load bases for all PRG images
- status: re-verified
- deps: RE-01
- evidence: `tools/re_overlay.py` verifies 20 non-empty PRGs by owned-byte self-consistency and
  SHA-bound independent metadata. BATTLE/TITLE/ENDING load at `0x80068800`;
  INITBTL/SCREFF2/MAINMENU at `0x800F9800`; MENU0-5,7-9,B-F at `0x80102800`; `MENUA.PRG` is empty.
- where: `tools/re_overlay.py`, `tools/extract_overlays.py`, `tests/test_overlay_inputs.py`
- gap: Runtime image generation, replacement, and cache invalidation belong to the dynarec adapter.

## Resident services

### RE-04 — CD load chokepoints and loader contract
- status: re-partial
- deps: RE-01
- evidence: `tools/re_cd.py` derives `_diskReset 0x80044A60`, `DsControlB 0x80025BE4`,
  `DsCommand 0x80023B34`, `DsSync 0x8002411C`, `CD_cw 0x80021470`, and `CD_sync 0x80020F28`.
  `tools/re_async_cd.py` retains measured queue/callback evidence. `game/cd/` retains cohesive native
  semantic owners without an execution-engine registry.
- where: `game/cd/`, `tools/re_cd.py`, `tools/re_async_cd.py`
- gap: Later XA/streaming modes and dynarec/native-override composition remain unverified.

### RE-05 — authored frame and presentation contract
- status: re-partial
- deps: RE-03
- evidence: `tools/re_frame.py` derives TITLE presenter `0x80071A68`, BATTLE presenter
  `0x8007629C`, resident parity `0x8005E210`, dynamic OT pointer array `0x80055C80`, and dynamic
  packet-pool pointer array `0x8005E0C0`. The retained frame owner has one presentation fence.
- where: `game/sync/frame_loop.cpp`, `game/render/`, `tools/re_frame.py`
- gap: Reconnect the frame owner at the dynarec/native boundary and reverify real output.

### RE-06 — pad driver buffers and byte order
- status: re-verified
- deps: RE-01
- evidence: `tools/re_pad.py` derives both buffers, the driver pointer table and stride, and the
  high-byte-first button normalization used by `game/input/pad_delivery.cpp`.
- where: `game/input/`, `tools/re_pad.py`
- gap: Runtime delivery awaits the dynarec adapter.

### RE-07 — retained semantic native owners
- status: re-partial
- deps: RE-02
- evidence: Cohesive owners remain for frame timing, input delivery, CD/file boundaries, title
  splash/movie/menu completion, battle presentation, heap initialization, save checks, and card
  initialization. Their guest-address facts are independently measured.
- where: `game/cd/`, `game/core/`, `game/input/`, `game/render/`, `game/save/`, `game/sync/`
- gap: Register each owner through one image-scoped psxport native-override adapter and prove its
  ordinary dynarec path as the comparison oracle.

### RE-08 — platform/HLE leaf inventory
- status: re-partial
- deps: RE-01
- evidence: Typed fact headers retain exact VSync, CD, GPU-sync, pad, and resident addresses.
- where: `game/sync/vsync_facts.h`, `game/cd/cd_facts.h`, `game/render/gpu_sync_facts.h`,
  `game/core/resident_facts.h`
- gap: Only demonstrated hardware/service boundaries may become native leaves; all ordinary game
  instructions remain dynarec-owned.

### RE-09 — SPU DMA completion route
- status: re-verified
- deps: RE-01
- evidence: `tools/re_spu_transfer.py` derives DMA callback table `0x80032128`, DMA channel 4, and
  the StartSound-to-waiter/callback chain from the authenticated executable.
- where: `tools/re_spu_transfer.py`, `game/core/resident_facts.h`
- gap: Reverify callback delivery after dynarec composition.

### RE-10 — retail VBlank/VSync route
- status: re-verified
- deps: RE-01
- evidence: `tools/re_vblank.py` derives VSync `0x8001F6C4`, handler `0x8001FFEC`, counter
  `0x80032114`, callback table `0x800320F4`, and interrupt return PC `0x8001FAD0`.
- where: `tools/re_vblank.py`, `game/sync/vsync_facts.h`
- gap: Historical direct handler dispatch is not retained; dynarec execution and native frame
  ownership must establish equivalent lifecycle invariants.

## TITLE and BATTLE evidence

### RE-11 — TITLE image provisioning and identity
- status: re-partial
- deps: RE-03
- evidence: `TITLE.PRG` is 554,568 bytes, SHA-1
  `f74a76e6215edebf607d0c2af56481050edb139a`, loads at `0x80068800`, and enters at `0x80071334`.
- where: `tools/extract_overlays.py`, `tests/test_overlay_inputs.py`
- gap: Map/enter/replace the image through psxport and prove invalidation.

### RE-12 — TITLE publisher/developer splash producer
- status: re-partial
- deps: RE-11
- evidence: `tools/re_title_startup.py` derives sprite leaf `0x8006A778`, packet
  `0x800DED28`, and producer `0x8006F54C`; `game/render/title_startup.cpp` retains the native
  completed-field owner.
- where: `tools/re_title_startup.py`, `game/render/title_startup.cpp`
- gap: Reverify presentation through the dynarec/native composition.

### RE-13 — TITLE 24-bit intro/MDEC producer
- status: re-partial
- deps: RE-12
- evidence: `tools/re_title_movie.py` retains the exact DCT callback and frame-completion facts;
  `game/render/title_movie.cpp` retains only the native presentation boundary.
- where: `tools/re_title_movie.py`, `game/render/title_movie.cpp`
- gap: XA/STR progress and natural completion require dynarec runtime proof.

### RE-14 — TITLE menu completed-pass producer
- status: re-partial
- deps: RE-12
- evidence: `tools/re_title_menu.py` identifies the menu-item completion boundary and
  `game/render/title_menu.cpp` retains its native owner.
- where: `tools/re_title_menu.py`, `game/render/title_menu.cpp`
- gap: Prove authored transition and menu output without bypassing lifecycle callbacks.

### RE-15 — first BATTLE image identities and entries
- status: re-partial
- deps: RE-03
- evidence: Exact BATTLE and INITBTL bytes, bases, and historical reach remain recorded by the
  extraction and frame instruments.
- where: `tools/extract_overlays.py`, `tools/re_frame.py`, `tests/test_overlay_inputs.py`
- gap: Runtime map/entry/invalidation and image-scoped native registration are missing.

### RE-16 — natural movie-end transition
- status: re-partial
- deps: RE-13, RE-14
- evidence: Historical traces reached the common TITLE menu path; the relevant state and producer
  facts remain in the TITLE instruments and issue 0026.
- where: `tools/re_title_natural.py`, `docs/issues/0026-menu-black-after-natural-movie-end.md`
- gap: Reverify the complete transition on the dynarec product.

### RE-17 — BATTLE completed-field ownership
- status: re-partial
- deps: RE-15
- evidence: The presenter, viewport, projection, dynamic OT, and packet-pool ownership are measured
  in `tools/re_frame.py`; `game/render/battle_frame.cpp` retains the native boundary.
- where: `tools/re_frame.py`, `game/render/battle_frame.cpp`
- gap: Native world production and live parity remain unverified.

## Finite native-owner evidence retained for the hybrid

### RE-18 — finite resident/TITLE/BATTLE frame owner
- status: re-partial
- deps: RE-05, RE-10
- evidence: `game/sync/frame_loop.cpp` owns explicit per-field service order and one presentation
  commit; focused C++ tests retain its previously measured contract.
- where: `game/sync/frame_loop.cpp`, `tests/test_vagrant_runtime.cpp`
- gap: It is currently disconnected until the title adapter exists.

### RE-19 — finite system initialization and TITLE loading phase
- status: re-partial
- deps: RE-18
- evidence: `tools/re_resident.py`, typed facts, and `game/core/resident_phase.cpp` retain the finite
  owner boundaries recovered from the retail executable.
- where: `tools/re_resident.py`, `game/core/resident_phase.cpp`, `game/core/resident_facts.h`
- gap: Connect only after the dynarec entry boundary exists; do not recreate a second runtime.

### RE-20 — native CD command and finite menu-sound loads
- status: re-partial
- deps: RE-04, RE-19
- evidence: Exact CD facts and native file/command owners remain under `game/cd/`.
- where: `game/cd/`, `tools/re_cd.py`, `tools/re_async_cd.py`
- gap: Validate override ABI, failure paths, and ordinary dynarec comparison.

### RE-21 — TITLE GPU timeout arm
- status: re-partial
- deps: RE-08, RE-19
- evidence: `game/render/gpu_sync_facts.h` retains the measured timeout arm/deadline/flag facts.
- where: `game/render/gpu_sync_facts.h`, `tools/re_resident.py`
- gap: Runtime behavior awaits the dynarec adapter.

### RE-22 — resident file loads and TITLE splash phase
- status: re-partial
- deps: RE-19, RE-20
- evidence: `game/cd/native_file.cpp` and `game/render/title_splash.cpp` retain finite semantic
  owners backed by exact disc extents and TITLE measurements.
- where: `game/cd/native_file.cpp`, `game/render/title_splash.cpp`, `tools/re_title_startup.py`
- gap: Reverify against ordinary dynarec execution and real presentation.

### RE-23 — TITLE save check and card initialization
- status: re-partial
- deps: RE-20, RE-22
- evidence: `tools/re_title_save.py` and `tools/re_title_memcard.py` derive the save/card facts;
  `game/save/` retains the finite semantic owners.
- where: `tools/re_title_save.py`, `tools/re_title_memcard.py`, `game/save/`
- gap: Connect at an image-scoped native override boundary and reverify event/file lifecycle.

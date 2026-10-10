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
  `0x80042C38`. The authenticated image itself is extracted and identity-checked by
  `tools/extract_exe.py`.
- where: `tools/extract_exe.py`, `game/boot/resident_facts.h`, `docs/references.md`
- gap: The future title adapter must apply the measured boot contract through psxport's dynarec
  entry path.

### RE-02 — resident runtime mapping and entry
- status: re-partial
- deps: RE-01
- evidence: `vagrant::VagrantRuntime::loadResidentImage` now refuses a structurally valid PS-X EXE
  whose measured resident header differs, then delegates the accepted image to psxport's central
  `loadPsxExeImage` publication and image catalog. `vagrant_image_contract` proves the positive
  entry/range/catalog path and the changed-entry refusal with a synthetic PS-X shape.
- where: `game/runtime/vagrant_runtime.{h,cpp}`, `game/boot/resident_image.{h,cpp}`,
  `game/boot/application.{h,cpp}`, `tests/test_vagrant_image_contract.cpp`,
  `CLAUDE.md`
- gap: The measured resident header is admitted in a process that reads the file whole and refuses
  any other size. A run now enters the guest at `0x8001F544` and executes the resident leaf order on
  Lightrec, but it dies in field 1 inside libcd `CD_sync` (issue 0042), so the entry is not yet
  established end to end. The file's SHA-1 stays `tools/extract_exe.py`'s rule; this repository
  deliberately does not re-derive it.

### RE-03 — load bases for all PRG images
- status: re-verified
- deps: RE-01
- evidence: All 20 non-empty PRGs were verified by owned-byte self-consistency and SHA-bound
  independent metadata; the resulting bases are shipped in `game/images/overlay_images.cpp`. BATTLE/TITLE/ENDING load at `0x80068800`;
  INITBTL/SCREFF2/MAINMENU at `0x800F9800`; MENU0-5,7-9,B-F at `0x80102800`; `MENUA.PRG` is empty.
  The exact disc's last sectors match the authenticated BATTLE/INITBTL/TITLE file prefixes and have
  respectively 1,756/1,156/440 zero bytes after EOF. Resident `_loadTitlePrg 0x80041F34` requests
  271 whole sectors from LBA 256000, so its final 440 bytes write up to `0x800F0000`
  (exclusive).
  `OverlayImages::loadTransfer` checks those whole-sector extents, refuses changed padding, copies the
  complete transfer to RAM, and invalidates the transfer while the image identity ends at file EOF.
  The isolated real-disc check read all three exact transfers, adopted their completed sector bytes
  from guest RAM, and refused all three changed tails through both staged and resident admission.
  `OverlayImages::adoptTransfer` checks the same authenticated extent after CD has already written
  guest RAM, publishes it without a second copy, and invalidates the previous slot generation. Its
  synthetic test refuses changed payload, changed padding, and foreign tail residency; a valid
  in-RAM TITLE-to-BATTLE replacement executes newly translated code with zero fallback.
- where: `tools/extract_overlays.py`, `tests/test_overlay_inputs.py`,
  `game/images/overlay_images.cpp`, `tests/test_vagrant_overlay_images.cpp`
- gap: The finite resident TITLE read now publishes only after all 271 native sectors complete and
  the acquired buffer passes image authentication.
  A future path using the natural CD queue must publish only at its successful Loaded transition;
  the publisher does not infer or set queue state. The resident-to-TITLE guest continuation and later
  overlays remain open.

## Resident services

### RE-04 — CD load chokepoints and loader contract
- status: re-partial
- deps: RE-01
- evidence: The authenticated executable gives `_diskReset 0x80044A60`, `DsControlB 0x80025BE4`,
  `DsCommand 0x80023B34`, `DsSync 0x8002411C`, `CD_cw 0x80021470`, and `CD_sync 0x80020F28`, shipped in
  `game/cd/cd_facts.h` with the measured queue and callback words. `game/cd/` retains cohesive native
  semantic owners without an execution-engine registry.
- where: `game/cd/`, `game/cd/cd_facts.h`
- gap: Later XA/streaming modes and dynarec/native-override composition remain unverified.

### RE-05 — authored frame and presentation contract
- status: re-partial
- deps: RE-03
- evidence: The authenticated BATTLE.PRG gives its presenter `0x8007629C`, resident parity
  `0x8005E210`, dynamic OT pointer array `0x80055C80`, and dynamic packet-pool pointer array
  `0x8005E0C0`; TITLE's presenter is `0x80071A68`. The retained frame owner has one presentation
  fence.
- where: `game/sync/frame_loop.cpp`, `game/render/battle_frame.cpp`, `game/render/battle_projection_facts.h`
- gap: Reconnect the frame owner at the dynarec/native boundary and reverify real output.

### RE-06 — pad driver buffers and byte order
- status: re-verified
- deps: RE-01
- evidence: The authenticated executable gives both buffers, the driver pointer table and stride,
  and the high-byte-first button normalization, shipped in `game/input/pad_facts.h` and used by
  `game/input/pad_delivery.cpp`.
- where: `game/input/`
- gap: Runtime delivery awaits the dynarec adapter.

### RE-07 — retained semantic native owners
- status: re-partial
- deps: RE-02
- evidence: Cohesive owners remain for frame timing, input delivery, CD/file boundaries, title
  splash/movie/menu completion, battle presentation, heap initialization, save checks, and card
  initialization. Their guest-address facts are independently measured.
- where: `game/boot/`, `game/cd/`, `game/execution/`, `game/images/`, `game/input/`,
  `game/render/`, `game/runtime/`, `game/save/`, `game/sync/`
- gap: The one image-scoped psxport native-override adapter EXISTS and is exercised
  (`vagrant::dynarec`, `vagrant::installResidentNativeOwners`, CTest `vagrant_dynarec_dispatch`:
  7/7 groups, every one a negative as well as a positive). The first leaf it made reachable is
  S007's allocator, which now runs natively and re-enters the original guest body, and the run of
  2026-10-04 records exactly one invocation of it with one original call that returned. What is NOT
  done: the other retained owners are still called as finite guest leaves rather than registered as
  overrides, so no run has compared a native owner against its ordinary dynarec path.
  Guest code spanning fields runs as a suspended `ResumableGuestCall` (`GuestPhase`); the R3000 register
  file is restored on every resume. `vs_main_execTitle` (0x80042BAC) after `vs_title_exec` is guest code run
  by `ExecTitleTail`; `_loadBattlePrg` (0x80041E4C) is native, and `vs_battle_exec` (0x800798A4) runs from
  the guest tail. libds: `CD_cw` sync completion is delivered by `LibDsField::completeOwedCommand` into the
  slot at 0x800321FC, and the `ds_cbready` body (0x8002559C) is wrapped so INT1 data-ready never precedes
  the owed completion.

### RE-08 — platform/HLE leaf inventory
- status: re-partial
- deps: RE-01
- evidence: Typed fact headers retain exact VSync, CD, GPU-sync, pad, and resident addresses.
- where: `game/sync/vsync_facts.h`, `game/cd/cd_facts.h`, `game/render/gpu_sync_facts.h`,
  `game/boot/resident_facts.h`
- gap: Only demonstrated hardware/service boundaries may become native leaves; all ordinary game
  instructions remain dynarec-owned.

### RE-09 — SPU DMA completion route
- status: closed in a run
- deps: RE-01
- evidence: The authenticated executable gives DMA callback table `0x80032128`, DMA channel 4, and
  the StartSound-to-waiter/callback chain, shipped in `game/boot/resident_facts.h`. Re-read from the
  SHA-bound bytes on 2026-10-04: `DMACallback` 0x80020280 computes `&DAT_80032128 + ch` and arms bit
  `ch+16` plus bit 23; `SpuSetTransferCallback` 0x800134A0 sets `0x800377F0` and installs
  `_spuWriteComplete` 0x8001347C at `0x80030898`, the only clear of that flag; `_waitTransferAvailable`
  0x8001355C is `do {} while (DAT_800377f0 == 1)`; and 0x8001DE94 — the channel-4 slot's body — calls
  `(*0x80030898)()`. The table is now DECLARED (`VagrantRuntime::platformHlePlan_`, `.dmaCallbackTable
  = resident::kDmaCallbackTable`) and the boot crosses `_initSound` in a run.
- where: `game/boot/resident_facts.h`, `game/runtime/vagrant_runtime.cpp`
- gap: none for the boot. The later DMA users (MDEC-out, GPU, OTC) are still unverified in a run.

### RE-10 — retail VBlank/VSync route
- status: re-verified
- deps: RE-01
- evidence: The authenticated executable gives VSync `0x8001F6C4`, handler `0x8001FFEC`, counter
  `0x80032114`, callback table `0x800320F4`, and interrupt return PC `0x8001FAD0`, shipped in
  `game/sync/vsync_facts.h`.
- where: `game/sync/vsync_facts.h`
- gap: Historical direct handler dispatch is not retained; dynarec execution and native frame
  ownership must establish equivalent lifecycle invariants.

## TITLE and BATTLE evidence

### RE-11 — TITLE image provisioning and identity
- status: re-partial
- deps: RE-03
- evidence: `TITLE.PRG` is 554,568 bytes, SHA-1
  `f74a76e6215edebf607d0c2af56481050edb139a`, loads at `0x80068800`, and enters at `0x80071334`.
  The exact resident has `jal 0x80071334` at `0x80042BD8` with a zero delay slot; the title entry
  gate validates those words and both live image generations before psxport dynarec continuation.
- where: `tools/extract_overlays.py`, `tests/test_overlay_inputs.py`,
  `game/images/overlay_images.cpp`, `game/images/title_entry.cpp`,
  `tests/test_vagrant_overlay_images.cpp`, `tests/test_vagrant_title_entry.cpp`
- gap: The title-owned entry gate and synthetic direct-call execution are separate from a run that
  has not yet reached TITLE. Wire the authenticated retail load and reached call through the product's
  CD and dynarec route.

### RE-12 — TITLE publisher/developer splash producer
- status: re-partial
- deps: RE-11
- evidence: The authenticated TITLE.PRG gives sprite leaf `0x8006A778`, packet `0x800DED28`, and
  producer `0x8006F54C`; `game/render/title_startup.cpp` retains the native completed-field owner.
- where: `game/render/title_startup.cpp`, `game/render/title_startup_recipe.{h,cpp}`
- gap: Reverify presentation through the dynarec/native composition.

### RE-13 — TITLE 24-bit intro/MDEC producer
- status: re-partial
- deps: RE-12
- evidence: The exact DCT callback and frame-completion facts are retained in
  `game/render/title_movie.cpp`; that file owns only the native presentation boundary.
- where: `game/render/title_movie.cpp`
- gap: XA/STR progress and natural completion require dynarec runtime proof.

### RE-14 — TITLE menu completed-pass producer
- status: re-partial
- deps: RE-12
- evidence: The menu-item completion boundary is retained in `game/render/title_menu.cpp`, which owns
  its native producer.
- where: `game/render/title_menu.cpp`
- gap: Prove authored transition and menu output without bypassing lifecycle callbacks.

### RE-15 — first BATTLE image identities and entries
- status: re-partial
- deps: RE-03
- evidence: Exact BATTLE and INITBTL bytes, bases, and historical reach remain recorded by the
  extraction tools and the shipped BATTLE fact tables.
- where: `tools/extract_overlays.py`, `game/render/battle_projection_facts.h`,
  `tests/test_overlay_inputs.py`, `game/images/overlay_images.cpp`,
  `tests/test_vagrant_overlay_images.cpp`
- gap: BATTLE/INITBTL admission and TITLE→BATTLE generation replacement now have a focused
  synthetic Lightrec proof. Runtime CD-load integration, reached entries, and image-scoped native
  registration remain missing.

### RE-16 — natural movie-end transition
- status: re-partial
- deps: RE-13, RE-14
- evidence: The natural-return `0` and Start/right return `1` classification, and the one epilogue
  they converge at, are recorded in `docs/issues/0035`; historical traces reached the common TITLE menu
  path.
- where: `game/render/title_menu.cpp`, `game/render/title_movie.cpp`, `docs/issues/0035`
- gap: Reverify the complete transition on the dynarec product.

### RE-17 — BATTLE completed-field ownership
- status: re-partial
- deps: RE-15
- evidence: The presenter, viewport, projection, dynamic OT, and packet-pool ownership are measured
  from the authenticated bytes and shipped in `game/render/battle_projection_facts.h`;
  `game/render/battle_frame.cpp` retains the native boundary.
- where: `game/render/battle_projection_facts.h`, `game/render/battle_frame.cpp`
- gap: Native world production and live parity remain unverified.

## Finite native-owner evidence retained for the hybrid

### RE-18 — finite resident/TITLE/BATTLE frame owner
- status: re-partial
- deps: RE-05, RE-10
- evidence: `game/sync/frame_loop.cpp` owns explicit per-field service order and one presentation
  commit; focused C++ tests retain its previously measured contract, and `vagrant::Application` is the
  composition owner that binds it to the product loop.
- where: `game/sync/frame_loop.cpp`, `game/boot/application.cpp`, `tests/test_vagrant_runtime.cpp`
- gap: The boot reaches the product loop and presents one field; the field is the boot's first field
  and the run then dies in field 1 (issue 0042).

### RE-19 — finite system initialization and TITLE loading phase
- status: re-partial
- deps: RE-18
- evidence: The typed facts in `game/boot/resident_facts.h` and `game/boot/resident_phase.cpp` retain
  the finite owner boundaries recovered from the retail executable. The native synthetic contract
  exercises those phases through injected services; production leaves now call psxport's bounded guest
  executor, and the completed-sector TITLE acquisition and authenticated publication through
  `readAndLoadTitle` is refused when broken.
- where: `game/boot/resident_phase.cpp`, `game/boot/resident_facts.h`
- gap: The exact `vs_main_exec` and `vs_main_execTitle` calls still need title-owned continuation:
  their live outer frames and saved registers, each leaf's measured callsite PC/return address, and
  the direct TITLE JAL at `0x80042BD8` with RA `0x80042BE0`. `ResidentPhase` calls bounded leaves
  using the inherited r31 and manually enters the splash after loading TITLE; the isolated
  `enterTitle` guest-JAL test does not compose with this finite phase. Prove that call/return chain
  and a finite field yield through the shipping adapter before claiming TITLE guest reach.

### RE-20 — native CD command and finite menu-sound loads
- status: re-partial
- deps: RE-04, RE-19
- evidence: Exact CD facts and native file/command owners remain under `game/cd/`. The measured
  TITLE request is `0x87800` bytes (271 complete sectors), including the final 440 bytes beyond the
  authenticated ISO file length. `readNativeSectors` acquires the complete extent before any guest
  RAM write. `VagrantRuntime::createContext` gives each Core an `OverlayImages` owner;
  `ResidentPhase` calls `readAndLoadTitle` at that acquisition boundary before its TITLE field wait.
  `OverlayImages::loadTransfer` authenticates the buffer before copying RAM and activating identity.
  The shipping-path synthetic test rejects a short final sector even with matching RAM and preserves
  a prior identity and RAM on both short and complete altered replacements.
- where: `game/cd/`, `game/images/title_transfer.cpp`, `tests/test_vagrant_title_transfer.cpp`
- gap: Validate override ABI, failure paths, and ordinary dynarec comparison on the real title. The
  resident-to-TITLE guest continuation remains uncomposed, and the CD wait that ends the boot is a
  declared-callback gap (issue 0042).

### RE-21 — TITLE GPU timeout arm
- status: re-partial
- deps: RE-08, RE-19
- evidence: `game/render/gpu_sync_facts.h` retains the measured timeout arm/deadline/flag facts.
- where: `game/render/gpu_sync_facts.h`
- gap: Runtime behavior awaits the dynarec adapter.

### RE-22 — resident file loads and TITLE splash phase
- status: re-partial
- deps: RE-19, RE-20
- evidence: `game/cd/native_file.cpp` and `game/render/title_splash.cpp` retain finite semantic
  owners backed by exact disc extents and TITLE measurements.
- where: `game/cd/native_file.cpp`, `game/render/title_splash.cpp`
- gap: Reverify against ordinary dynarec execution and real presentation.

### RE-23 — TITLE save check and card initialization
- status: re-partial
- deps: RE-20, RE-22
- evidence: The authenticated TITLE.PRG gives the save and memory-card facts, shipped in
  `game/save/title_save_facts.h` and `game/save/title_memcard_facts.h`; `game/save/` retains the finite
  semantic owners. Read out of the SHA-bound TITLE.PRG on 2026-10-04: `_saveFileExists` is
  `0x8006E988` (0x68-byte frame) and `_initMemcard` is `0x8006A49C`; `_saveFileExists` opens with
  `_initMemcard(1)`, spins `do { vs_main_gametimeUpdate(2); } while (_initMemcard(0) == 0)`, then scans
  card ports 1 and 2 through `_memcardEventHandler` (`0x8006947C`) and shuts the card down through
  `0x8006A6E0`. Guest RAM read through the product's own control channel at the stall: `_spmcimg`
  `0x800DEAB8` = `0x8010C010`, `_mcData` `0x800DEABC` = `0x8011D410`, the overlay's `_initMemcardState`
  `0x800DC8C4` = 0 (`none`), its `cdQueueSlot` `0x800DC8C8` = `0x800501E0` with `slot->state` = 2
  (`vs_main_CdQueueStateReading`), `cdFile.lba` = `0x00014C98` and `cdFile.size` = `0x0001C000`, and all
  eight `_memcardEventDescriptors` at `0x800DEA98` still zero. So the wait was the libds CD-queue
  completion for SPMCIMG.BIN and NOT a card event: the queue reaches `Reading` on one
  `_processCdQueue` and needs a second one to reach `Loaded` (4), which requires
  `_diskGetState() == diskIdle`, and psxport's synchronous CD controller raises no completion to make
  that true. `TitleSaveCheck` therefore reaches `TitleMemcardInit`, the finite native owner that reads
  the exact extents `(0x14C98,0x1C000)` and `(0x14CD0,0x2000)` and preserves the allocation, pointer
  graph, SPMCIMG upload, reset policy and eight-event lifecycle; the guest `_initMemcard` is now
  asserted undispatched. Measured run: `TITLE save-file check completed`, `fallback_blocks=0`,
  `faults=0`, 1,406 translated blocks, 2,900,904 executed instructions.
- where: `game/save/`, `game/boot/resident_phase.{h,cpp}`
- gap: `_memcardEventHandler` is still reached as guest code, and it works only because psxport's
  libcard HLE (`A0:0xAB` cardsInfo, `A0:0xAC` cardLoad) delivers SwCARD `EvSpIOE` synchronously. That
  is measured to work for a present card, not owned by this title: a card that is absent, unformatted
  or faulted still takes the guest's `memcardEventTimeout`/`Unformatted` branches, and no run has
  exercised them. The save-file check also still runs only against port 1 and 2 with a stubbed
  `firstfile`; the load/save arms beyond `_saveFileExists` are unowned.

### RE-24 — BATTLE room draw and its screen-space reject
- status: re-partial
- deps: RE-22
- evidence: Decompiled from the authenticated BATTLE.PRG with the pipeline and checked against the image's own
  words. The room draw is `0x8008AC78` -> `0x8008B1FC` -> `0x8009723C` -> `0x80097388`. `0x80097388` loops the
  room quads: RTPT and NCLIP through `0x80097A10`, then `0x80098014` (screen reject, register convention, vertices in
  `$t0-$t3`, answer in `$at`, leftovers in `$t4-$t7`), then the OT insert `0x800980F8` (depth window 8..0x7FF) and
  the near-clip subdivision `0x80097AEC`, which calls `0x80098014` too. `0x80098014` compares rows against
  `[0,224)` then columns against `[0,320)` and returns when all four vertices lie past one side. Nothing reads its
  result but packet emission, so it is widened for drawing (`game/render/battle_cull.cpp`). Actors have no
  screen-space cull.
- where: `game/render/battle_cull.{h,cpp}`, `tests/test_battle_cull.cpp`
- gap: the sky-dome inline reject near `0x8009820C`, the literal-320 gradient in `0x8008EC48`, rain `0x8008F440`,
  particles, HUD and the `0x800BB874` scanline effect still use retail 4:3 limits; whether any of their results
  feeds gameplay is unread. `0x80098160` (near-clip consumer) is named but not decompiled.

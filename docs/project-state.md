# Vagrant Story project state

This is the factual capability inventory. Epic intent is in `docs/project-goals.md`, atomic work in
`docs/issues/`, subsystem placement in `docs/codemap.md`, and ordered binary evidence in
`docs/re-frontier.md`.

| ID | Capability / observable outcome | State | Dependencies | Goals |
|---|---|---|---|---|
| S001 | Retail executable and reached overlays are reproducibly identified and provisioned | verified | — | G001 |
| S002 | Offline-generated guest execution and its product selectors are absent | verified | S001 | G001 |
| S003 | Finite native boot/platform owners preserve the measured route into TITLE/BATTLE phases | partial | S015 | G001 |
| S004 | TITLE splashes, intro movie, Start-skip menu, and input are visibly presented | partial | S003 | G001 |
| S005 | Natural intro completion is classified and visibly reaches the same title/menu result | partial | S004 | G001 |
| S006 | BATTLE and INITBTL have authenticated runtime images and measured initialization entries | partial | S001, S003, S015 | G001 |
| S007 | The first decomp-seeded native game body preserves its measured ABI and memory effects | verified | S001 | G001 |
| S008 | BATTLE has an explicit measured completed-field fence and mapped viewport/projection boundary | partial | S006 | G001, G002 |
| S009 | BATTLE world geometry is produced natively from semantic game state | missing | S008 | G002 |
| S010 | BATTLE world rendering supports true widescreen | missing | S009 | G003 |
| S011 | Native world presentation interpolates semantic camera/object state | missing | S009 | G004 |
| S012 | The zero-argument launcher provisions, builds, and launches the intended product | blocked | S001, S015 | G001 |
| S013 | Vagrant Story is playable through the complete game | missing | S003, S004, S006, S009 | G001 |
| S014 | Streaming CD/XA and audio behavior is owned beyond the verified intro path | partial | S003 | G001 |
| S015 | The gameplay product executes authenticated guest images through psxport's dynarec-only runtime | missing | S001, S002 | G001 |
| S016 | Hosted CI truthfully distinguishes repository policy from native product support on Linux, Windows, macOS, and Android | partial | S015 | G001 |

## Current focus

S015 is the current focus. The static product has been removed first, and the repository now stops at
one explicit missing boundary: a Vagrant Story adapter to psxport's dynarec-only executor. The
preserved native route previously crossed TITLE `ClearImage`, `_diskReset`, all four menu-sound reads,
TITLE.PRG, both publisher/developer loops, the complete save-check `gametimeUpdate` caller, and finite
`_initMemcard`; those owners are migration inputs and not a currently runnable product.

## Capability details

### S001 — Reproducible retail inputs

Evidence: `tools/extract_exe.py`, `tools/extract_overlays.py`, and
`tools/verify_decomp_targets.py` identity-check the USA executable and reached TITLE/BATTLE/INITBTL
images from a user-supplied disc. Positive and altered-input controls refuse mismatched hashes, extra
overlay inputs, and missing provenance.

### S002 — Static execution removal

Evidence: the generator wrapper, seed manifest, static registry, generated corpus, generated-source
build rules, legacy product entry/runtime adapter, and generated-super registration glue are absent.
`tools/check_structure.py` scans first-party product sources and the build entry for retired registry,
dispatcher, generated-body, selector, and build-input patterns, and its negative tests prove each
class is observable. CMake and the launcher name S015 instead of selecting a fallback.

### S003 — Boot and platform delivery

The preserved `VagrantFrameDriver` implementation supplies one finite title-owned field. Its tested
order is host frame index, measured pad delivery, SPU/audio service, completed
resident/TITLE/BATTLE producer arbitration, exactly one presentation commit, one field pace, then
resumption of finite resident work that retail would have resumed only after VSync returned. Sony
VSync `0x8001F6C4` remains a measured forbidden guest boundary. Historical exact-product runs and the
retained RE instruments establish the behavior below, but no current gameplay binary exists until
S015 is implemented.

Gap: these preserved owners are not composed into a current gameplay product and cannot advance the
authenticated executable until S015 supplies the dynarec title adapter.

`ResidentPhase` now executes the real finite `_sysInit` leaf order around InitCARD's measured
VSync(0), enters TITLE `_sysReinit`, preserves `_displayLoadingScreen`'s VSync(2) as two complete host
fields, submits both loading images, and stops immediately before `_loadMenuSound 0x800468FC`.
The first correction bound measured nested `CD_sync`, but the next bounded launch reached
`CD_cw 0x80021470`'s direct VSync(-1), return `0x80021634`. The outer-command correction then served
three CD-init commands natively, but `CD_init` called `CD_sync` independently and restored the
`0x80020F64` fatal. Both exact leaves are required. `_diskReset`'s VSync(3) and all four menu-sound
file polls already have finite host-field owners through the measured CD-queue/game-time work.

The combined PID 2657967 run live-proved both CD leaves and moved the next fatal to TITLE
`ClearImage -> 0x8002A3E8 -> GPU timeout arm 0x8002AB84 -> VSync(-1)`. The arm's executable body
only stamps a 240-field deadline at `0x80033580` and clears `0x80033584`; Vagrant now binds the
existing synchronous-GPU owner through the fourth exact one-instruction window. A later real-disc
run crossed that arm, `_diskReset`, and four real WAVE/EFFECT copies. The root incompatibility was
then explicit: psxport's CD controller completes commands synchronously and models no controller IRQ,
while retail libds waits for asynchronous callbacks. `NativeFile` therefore owns the measured finite
file extents directly from the CHD. The same route copied TITLE.PRG LBA 256000, size `0x87800`, into
`0x80068800`; signature routing entered `0x80071334` and the mandatory fatal identified the first
remaining guest wait inside publisher owner `0x8006F54C`.

`TitleSplashPhase` now owns that 0xB0-byte frame and both 364-field loops. Against clean pinned
psxport `3c342ec3`, exact-product PID 3180949 completed all 728 native `_drawSprt` fields and wrote
seven inspected player-view captures: the first loop visibly fades “Published by Square Electronic
Arts L.L.C.” and the second fades the SQUARESOFT logo. The run then made the mandatory fatal contract
observable at the next unowned field: TITLE `0x8006E988 -> gametimeUpdate 0x8004261C -> VSync(2)`,
return `0x80042634` (issue 0033). `TitleSaveCheck` now owns that whole caller and preserves its stack,
CD-queue tail, packed game time, memory-card event/port state, filename probe, shutdown, and result.
Exact-product PID 3213121 then completed 1000/1000 host fields with zero dropped layers and no guest
VSync; this resolves issue 0033. Its 728 native sprites occupied fields 12..739, while ten captures
from fields 749..950 were uniformly black and the save-check completion transition was absent.

The corrected boundary is issue 0034: `_initMemcard(0)` was still waiting for SPMCIMG.BIN's retail
asynchronous CD slot, whose interrupt-driven Loaded transition cannot occur under psxport's
synchronous controller. `TitleMemcardInit` now replaces the two exact queue transfers with finite
disc reads `(85144,0x1C000)` and `(85200,0x2000)`, while retaining allocation, pointer graph, SPMCIMG
upload, reset policy, and eight event opens/enables. After a first live rerun
exposed and corrected missing parent-to-child phase resumption, exact-product PID 3309285 copied both
extents, completed the save-file check, and reached `_initIntroMovie` with 1000/1000 reconciled fields,
zero drops, and no guest VSync. Fields 749..950 are a stable 35,160/691,200 non-black, but visual
inspection shows only a partial lower-right texture strip rather than a valid intro frame (issue
0035). The SHA-bound tools pass 13/13 + 4/4 and 33/33 + 4/4 respectively; the fresh Clang 22.1.8
build and all 8 CTests pass. `_initIntroMovie`, later TITLE continuation, BATTLE reach, and complete
game-lifetime timing remain unverified.

### S004 — Visible TITLE path

Publisher/developer splashes, coherent 24-bit intro frames, and the recorded Start-skip route to a
readable Vagrant Story/New Game/Continue/Sound screen have historical guest-loop producer/control
evidence in RE-12, RE-13, and RE-14. Their retained producer fences now prepare fields for the single
VagrantFrameDriver commit.

The new native phase path reaches the publisher producer, owns its VSync boundaries, and visibly
presents both the actual publisher art and SQUARESOFT developer logo. Intro/movie/menu interaction,
title transitions, teardown ownership, and complete title-loop behavior remain unverified.

Gap: no current product can reach these owners before S015; intro/movie/menu interaction and complete
title-loop behavior also remain unverified after composition.

### S005 — Natural intro completion

The SHA-bound retail classifier proves natural return `0` and Start/right return `1` converge at one
epilogue and the sole caller ignores the result before common title/menu initialization (C028/I020).

Gap: no correctly provenanced natural-end menu screenshot exists. Issue 0026 resolved the earlier
black-menu report as a later BATTLE/loading capture, not as visible natural-menu proof.

### S006 — BATTLE/INITBTL execution

Historical guest-loop evidence reached BATTLE `0x800798A4` and INITBTL `0x800FA35C` in their
authenticated runtime images. Issues 0022–0024 preserve the retired pipeline's evidence about
cross-overlay targets, computed control flow, and shared epilogues; they are not implementation
requirements for the new runtime.

Gap: the native phase path does not currently re-enter BATTLE. A room/world field, gameplay loop,
later overlays, and complete BATTLE execution are not verified.

### S007 — First measured native game body

Evidence: `vagrant::heap::initHeap` preserves the measured memory effects of
`vs_main_initHeap 0x80043F74`; its hermetic contract and `tools/re_heap.py` negative controls pin the
implementation (C023). It is intentionally not registered until S015 supplies the image-scoped
native-override boundary.

### S008 — BATTLE completed-field and projection boundary

`tools/re_frame.py` uniquely measures presenter `0x8007629C`, dynamic-OT submit owner `0x8008A3A0`,
viewport initializer `0x800760CC`, the 320x240-to-320x224 convention, field center `(160,112)`,
projection word `0x8005E248`, and setter `0x8007CCF0`. Its source gate pins the retained native
completion fact. A historical run reached the boundary 9,073 times (C029/I013), while the native
frame-driver contract test proves one commit after exactly one selected resident/TITLE/BATTLE
producer arbitration per field. Neither is current product evidence until S015 reconnects it.

Gap: the driver has not been launched and the native phase path does not reach the BATTLE fence, so
the exact one-commit relationship is hermetic rather than live proof. The four prior 320x224 captures
were byte-identical black frames while a separate diagnostic composition still showed the title
menu. The fence publishes guest-translated primitives and is not the semantic native world producer.
Issue 0027 owns that later proof after issue 0028 restores BATTLE reach.

### S009 — Semantic native BATTLE world production

Missing capability: no producer currently reads named BATTLE camera, object, material, animation,
and model inputs before GTE projection and regenerates the world through native geometry. The active
queue contains post-projection screen vertices and cannot supply this ownership.

### S010 — True widescreen

Missing capability: Vagrant publishes no game-owned BATTLE projection policy. Widening belongs in the
future semantic world producer, preserving the vertical center while leaving fixed 2D layers at their
retail layout. `docs/battle-rendering.md` records the measured boundary.

### S011 — Interpolated presentation

Missing capability: there are no owned previous/current semantic camera and object snapshots, no
world re-render at a presentation-time interpolation parameter, and no cut/reset policy. The current
neutral field commits bypass the framework temporal decorator, so a local `fps60=1` preference is not
interpolation evidence.

### S012 — Default launcher contract

Blocked by S015. `run.sh` remains a slim frozen-uv shim into `bootstrap.py`/`tools/run.py`, and help
is available before product construction. Its zero-argument route now refuses with the one exact
missing dynarec-adapter boundary; it does not provision or launch the removed product and cannot yet
satisfy the player launcher outcome.

Blocker: S015 has no title adapter to psxport's dynarec-only executor.

### S013 — Complete playable game

Missing capability: the port does not yet present verified BATTLE world gameplay or cover later
overlays, saves, complete audio, progression, and end-to-end completion.

### S014 — Later streaming and audio ownership

The initial menu WAVE reads, TITLE overlay transfer, intro STR/XA stream, and the completion behavior
that previously froze the movie have measured/live evidence in RE-04 and issue 0025.

Gap: later music, effects, voices, room streaming, XA teardown, and game-lifetime audio behavior are
not verified.

### S015 — Dynarec-only gameplay execution

Missing capability: there is no Vagrant Story title adapter for psxport's per-Core Lightrec executor,
authenticated image generations, typed exits, invalidation, or image-scoped native overrides. The
product must remain unavailable until that adapter executes real resident and `.PRG` blocks without
linking or selecting an interpreter.

### S016 — Platform CI coverage

Partial capability: `.github/workflows/ci.yml` runs the maintained asset-free structure and launcher
verifier on one Linux host with full history, read-only permissions, pinned actions, and an explicit
timeout. The job is intentionally host-neutral policy coverage rather than a Linux product claim.

| Platform | Applicability | Current CI evidence and exact gap |
| --- | --- | --- |
| Linux x86-64 | applicable portable-PC target | Repository policy is covered; S015 leaves no native/dynarec executable to compile, execute, lint, or package. |
| Windows x86-64 | applicable portable-PC target | Missing: no native/dynarec executable, supported Windows build, runtime test, or package boundary exists. |
| macOS arm64 | applicable portable-PC target | Missing: no native/dynarec executable, Apple-Silicon build, runtime test, or application package exists. |
| Android arm64 | applicable future portable target | Missing: no Android title integration, shared `android-port` consumer, native runtime, APK build, or install test exists. |

Gap: create platform jobs only after the corresponding native runtime boundary exists and can be
exercised with redistributable synthetic inputs; repeating the Python policy verifier on another host
does not establish platform support.

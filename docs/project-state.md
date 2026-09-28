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
| S012 | The zero-argument launcher provisions, builds, and launches the intended product | partial | S001, S015 | G001 |
| S013 | Vagrant Story is playable through the complete game | missing | S003, S004, S006, S009 | G001 |
| S014 | Streaming CD/XA and audio behavior is owned beyond the verified intro path | partial | S003 | G001 |
| S015 | The gameplay product executes authenticated guest images through psxport's dynarec-only runtime | partial | S001, S002 | G001 |
| S016 | Hosted CI truthfully distinguishes repository policy from native product support on Linux, Windows, macOS, and Android | partial | S015 | G001 |

## Current focus

S015 is still the current focus and it is now **`partial` rather than `missing`**, because the number
it was `missing` for has been measured. **On 2026-09-28 a run survived the boot's first host field
and `fallback.calls` read 0**, with all thirteen per-reason counters printed and zero, beside
nonzero and rising executor counters (44,855 then 58,663 executed instructions over 430 then 617
translated blocks). That is the instrument having run and scanned, which is the distinction issue
0041 could not reach: its `fallback_blocks=0` carried `executor_calls=0` and was therefore "the
instrument never ran".

**What that establishes, stated as separate clauses because they can fail separately.** The product
executes the AUTHENTICATED guest image through Lightrec, and no guest block is interpreted. The
title's boot is owned rather than merely executed: the projection owner's four resident leaves run
again instead of replacing the guest's, and the boot's own display-area publication is measured
through the guest's leaf — `8005E18C` reads `00E00140`, the halfword 320, beside BATTLE's rectangle
at `8005DFD6` still reading zero. **What it does not establish is a single TITLE phase.** The run
ends in field 1, so S004's splash, the intro movie and the Start-skip menu are all still
unpresented, and no gameplay exists.

Fatal #4 is fixed at root cause, and the root cause was TWO halves of one thing rather than the wrong
comparison: the owner was REPLACING four resident SDK leaves while its header claimed it observed
them, and the cross-check named `0x8005DFD6`, which a reference census over all four provisioned
modules shows the resident executable never writes. A publication's own horizontal extent is the word
the leaf itself stores the stated width into, at `env + 4` of the struct the CALLER named. The frame
that presented is the boot's first field and it is black — 0 of 71,680 pixels non-black, opened as an
image — which is one step earlier than a splash and is not a title phase.

**Fatal #3 PERSISTED, and the in-segment clock hypothesis is refuted by measurement.** The exit is
still `budget-exhausted at 0x80020F28 after 564486 cycles` inside libcd's `CD_sync`, and the guest's
VSync field counter at `0x80032114` advances exactly once per host field (1 before any field, 2 after
field 0) and not at all across field 1's 564,486 cycles. The framework's own in-segment clock commit
(`4a08ec55`, merged `5d4b3327`) landed while this work was in flight; the product was rebuilt against
it and the exit is unchanged, so the `cpu-executor` claim is **not** a dependency of this defect.
What it is instead: the completion byte `CD_sync` reads at `0x800324D8` has exactly ONE writer in
the resident — `sb $v0, -0x1DB28($at)` at `0x80020D38`, inside the unnamed libcd command-state
function between `CdDataSync` and `CD_sync` — and the boot never reaches it; and separately,
`VagrantRuntime` declares no `guestCdStreamCallbackLayout`, so psxport's
`cdReadyCallbackOwnedByGuestInterrupt()` is false and the framework's CD-ready-callback delivery to
the guest's own interrupt path is not part of this title's contract. Measuring the slot
`CdReadyCallback` writes is the next RE step, and it is title-side. `docs/issues/0042` carries the
evidence and the falsifiers.

The product-link finding from issue 0041 has been ACTED ON and is superseded: `verify_product_link`
now reports both the retired symbols (`0 of 3`) and Lightrec's own per-block interpreter (`2 of 2 …
PERMITTED`), and states that neither is a measurement of whether this title used one — that number
is `fallback.calls` at run time. The check no longer goes green on a subject outside the execution
path, and it no longer implies it can answer S015.

**THE GATE IS GREEN, ALL 22 CONTRACTS, and `tools/verify.py` EXITS 0.** The row that was red while
this was in flight is green now, and the reason is worth keeping because it is the documented cost of
one shared framework tree rather than a defect in this port. The shared framework advanced twice
under other agents (`5d4b3327`, then `6bb49c24`) while this work was running, so the build receipt
named a commit the recorded pin did not, and `vagrant_psxport_pin_live` was correctly red about it.
The first attempt to bump was also correctly REFUSED — the framework tree was dirty from another
agent's uncommitted `docs/workspace/WORKSPACE.md`, and a receipt taken from a dirty tree does not
say what the commit contains. Once that tree was clean the prescribed order was run end to end
(`reconfigure -> build -> test -> --bump`) and the pin moved `b951d747 -> 6bb49c24` from the build's
own receipt rather than from the framework's HEAD.

**STYLE GATES, and these were red before this work and are green now.** `tools/verify.py` was exiting
FAIL on the clang-tidy stage alone, with 56 clang-format violations and 13 clang-tidy findings, none
of them in code this change wrote. Both are now **0 violations and 0 findings** across 75
format-checked files and 38 compile-backed first-party translation units. The 13 were fixed at root
cause and not suppressed: `ExecutionTelemetry::recordExecutableWrite`'s two adjacent `std::uint64_t`
parameters became a named `WriteExtents` struct, `BattleProjectionOwner::readPublishedArea`'s
`uint32_t`/`int32_t` pair became a named `DisplayAreaPublication` struct, the twelve
`bugprone-unchecked-optional-access` findings became one checked `identityOf` helper and one checked
`invokeLeaf` helper rather than twelve unchecked dereferences, and the escaping exception out of a
test `main` is now caught at the boundary and names the failure.

The coordinate product slot was HELD by a Spyro agent until 2026-09-29T12:00, which is why issue
0040 shipped an adapter with no run. The run is now taken. A later run found the slot's claim naming
a CTR agent with a 2026-10-02 expiry; the conflict is recorded in `docs/info/claims/032` rather than
edited, and every run was bounded, headless and checked against a live process list first.

The preserved native route previously crossed TITLE `ClearImage`, `_diskReset`, all four menu-sound
reads, TITLE.PRG, both publisher/developer loops, the complete save-check `gametimeUpdate` caller,
and finite `_initMemcard` — under the RETIRED static-recomp product. Those owners are wired into the
composition chain now, so they are reachable, but reachability through a composition chain is not a
run.

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

The title's `OverlayImages` owner now admits the reached BATTLE and INITBTL files at their measured
bases and retires the older TITLE/BATTLE generation in the shared slot. The synthetic contract
executes a translated block before and after replacement, checks that the old translation is
invalidated, and refuses altered bytes and unknown existing residency without changing Core state.

Gap: the title adapter does not currently re-enter BATTLE. A room/world field, gameplay loop,
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

**The field rate is MEASURED, so this item's scope is settled: it is IN scope.**
`docs/issues/0039` measures 2 fields per game frame (30 fps) or 4 (15 fps) from the image, with
`vs_gametime_tickspeed` (`0x8005E24C`) as the rate-bearing argument and a setter that admits
**only 2 and 4** — so 60 fps is structurally impossible and this title is never out of scope. The
2-vs-4 choice is a **presentation** decision: every consumer scales its per-step increment by the
same value that scales the field wait, so the game clock keeps real time while the picture is
presented half as often. Interpolation is therefore over the same source geometry, not over a
slowed simulation. Instrument: `tools/re_cadence.py`, CTest `vagrant_cadence{,_selftest}`, 8/8.

Missing capability, unchanged: there are no owned previous/current semantic camera and object
snapshots, no world re-render at a presentation-time interpolation parameter, and no
cut/reset policy. The current neutral field commits bypass the framework temporal decorator, so a
local `fps60=1` preference is not interpolation evidence.

### S012 — Default launcher contract

Partial. `run.sh` remains a slim frozen-uv shim into `bootstrap.py`/`tools/run.py`, and help is
available before provisioning. The zero-argument route now resolves the framework, provisions the
authenticated measured inputs through `tools/extract_exe.py` and `tools/extract_overlays.py`,
configures, builds `vagrant_port`, and launches it. The refusal that named "the one explicit
unavailable-product boundary" is gone, and each refusal that replaced it names the STAGE and the
tool rather than a missing boundary.

Evidence: `tests/test_launcher.py` 16/16 with the process boundary injected. It asserts the route
provisions, configures, builds `vagrant_port`, and launches; that it refuses BEFORE configuring when
provisioning fails; that a configure or build failure refuses before the next stage; that
`--prepare-only` builds without launching; and — through the repository's own retired-pattern table
rather than a second list — that no retired selector is reachable from the launcher.

Gap: the route has never been executed end to end on this machine, because the product slot was held.
`run.sh` opens a window and plays audio, so it is a player command and not an agent check; the
gate-covered claim is about the route's composition and its refusals, not about a completed launch.

### S013 — Complete playable game

Missing capability: the port does not yet present verified BATTLE world gameplay or cover later
overlays, saves, complete audio, progression, and end-to-end completion.

### S014 — Later streaming and audio ownership

The initial menu WAVE reads, TITLE overlay transfer, intro STR/XA stream, and the completion behavior
that previously froze the movie have measured/live evidence in RE-04 and issue 0025.

Gap: later music, effects, voices, room streaming, XA teardown, and game-lifetime audio behavior are
not verified.

### S015 — Dynarec-only gameplay execution

**`partial`. Two of the item's clauses are established and the rest are not, and the split is the
honest state rather than a rounding.** A run on 2026-09-28 survived the boot's first host field and
read `fallback.calls = 0` over the live control surface, with all thirteen per-reason counters
printed and zero, beside `executor_calls` 40 then 44, `translated_blocks` 430 then 617,
`executed_blocks` 8,400 then 10,722 and `executed_instructions` 44,855 then 58,663
(`docs/issues/0042`, `docs/info/claims/032`).

| clause | state | evidence |
|---|---|---|
| the product executes the AUTHENTICATED guest image through Lightrec | established | `authenticated resident image: … 337920 bytes, sha256 51dfdf15…, image 1/1`, then the counters above |
| no guest block is interpreted | established | `fallback.calls=0` and every per-reason counter zero, beside nonzero executor counters — a SCANNED zero, not an absent tail |
| the boot is OWNED, not merely executed | established | the four resident viewport leaves run again; `rw 8005E18C` reads `00E00140` (the halfword 320) beside BATTLE's rectangle at `8005DFD6` still zero |
| a TITLE phase is reached | **missing** | the run ends in field 1, so the splash, the intro movie and the Start-skip menu are all unpresented |
| the product is playable | **missing** | — |

**"The composition is correct and a frame presents" is not this item**, and the difference is the
table above: a present is not a title phase, and a title phase is not gameplay. The one frame that
presented is the boot's first field and it is black — 0 of 71,680 pixels non-black, opened as an
image, and the same field's log carries `[gpu] display standard -> NTSC`, so the display area was
published and nothing had been drawn into it.

**Fatal #4, fixed at root cause, and the cause was TWO halves of ONE thing.** The projection owner
was REPLACING four resident SDK leaves while its own header claimed it observed them — psxport
consults a title's override before the original body, so `SetGeomOffset`, `SetGeomScreen`,
`SetDefDrawEnv` and `SetDefDispEnv` never ran, and the guest's GTE geometry, display environment and
draw environment were written by nothing in the product. And the cross-check named `0x8005DFD6`, a
reference census over all four provisioned modules shows the resident executable never writes (the
only stores anywhere are BATTLE's `func_800760CC` at 0x800761E0/E8/F0/0x80076200), so a 0 there means
"no overlay publication has run yet", which is the ordinary state of the whole boot. Both are fixed:
the GTE leaves perform their measured effect through psxport's public GTE primitive, the env leaves
run the original guest body through psxport's own `psx::cpu::callOriginalToReturn`
(`runtime/cpu/native_dispatch.h:96` — the framework's, not a second copy here) and then read the word
the leaf filled, and the cross-check target is `env + 4` — a per-call address the CALLER names, which
is why no title constant can be it. The test that would have caught the replacement seeds nothing
and asserts CR24/CR25/CR26 and `projParams` all moved.

**Fatal #3 PERSISTED, and it is not the framework's in-segment clock.** The exit is still
`budget-exhausted at 0x80020F28 after 564486 cycles` in libcd's `CD_sync`. The guest's VSync field
counter at `0x80032114` advances once per host field and not at all inside one, and the framework's
own in-segment clock commit (`4a08ec55` / `5d4b3327`) changed nothing when the product was rebuilt
against it — so `cpu-executor` is NOT a dependency of this. The completion byte `CD_sync` reads at
`0x800324D8` has exactly one writer in the resident, `sb $v0, -0x1DB28($at)` at `0x80020D38`, and the
boot never reaches it; and `VagrantRuntime` declares no `guestCdStreamCallbackLayout`, so psxport's
`cdReadyCallbackOwnedByGuestInterrupt()` is false and the framework's CD-ready delivery to the
guest's own interrupt path is not this title's contract. Measuring the slot `CdReadyCallback` writes
is the next RE step, and it is title-side.

**`verify_product_link`'s false negative has been FIXED, and this paragraph supersedes the one below.**
It now reports `0 of 3 retired-interpreter entry points` AND `2 of 2 Lightrec per-block interpreter
entry points ARE linked … It is NOT a measurement of whether this title used one: that number is
`fallback.calls` at run time`. The check no longer goes green on a subject outside the execution
path, and it states that it cannot answer S015 in either direction. `fallback.calls` is the only
possible answer, and it is now a number.

What exists. `game/core/dynarec_dispatch.{h,cpp}` is the whole title/dynarec boundary in six
operations — image-scoped install, finite call, bounded turn, original call, the one
bounded-resume-and-refuse rule every owner that re-enters its own leaf shares, and a named fatal on a
call that did not return — and it is the only module in this repository that resolves an image
identity, spells an `ExecutionBudget`, or chooses a dispatch form, so there is one answer to each
rather than two. `game/core/native_owners.{h,cpp}` is the all-or-nothing registry of image-scoped
leaves, reached from the resident publication boundary because `registerOverrides` runs before any
image exists. `game/core/application.{h,cpp}` composes the machine into a product. `game/main.cpp` is
a one-call entry point, and the `vagrant_port` target went from `COMMAND false` to a real
`add_executable`. `VagrantRuntime::platformHlePlan` binds the measured guest VSync `0x8001F6C4` with
its measured field counter, plus the two measured stock libcd leaves, so a guest VSync is a named
refusal rather than a hang and a title with no measured address is refused before boot.

**The instruments are three tools, because the cap was right.** `tools/re_viewport.py` measures the
BATTLE overlay publication and owns the shared MIPS-I field decoder and the SHA-bound image loaders;
`tools/re_display_area.py` measures the RESIDENT display-area publication and which word is one
horizontal extent; `tools/re_vsync_sites.py` censuses every `jal VSync` and the field count its
argument holds. The decoder is imported, never copied, and `re_viewport.py` imports
`re_display_area` at the point of use because the callee imports the caller.

What is established, with denominators. `vagrant_dynarec_dispatch` passes 7 groups through the
SHIPPING seam: a real translated block executes and returns the guest's own result register with
`fallback.calls == 0`; an infinite `b .` ends in `BudgetExhausted` with a PC inside the loop and
non-zero cycles; an install with no active image and an install against a generation the caller did
not publish are BOTH refused AND counted with their own reasons; a null handler is refused; a
TITLE-generation leaf becomes unreachable after BATTLE publishes into `0x80068800` while the resident
leaf survives (their ranges are disjoint — resident text ends at `0x80062000`); `callOriginal` returns
the value only the GUEST body produces, which is what proves suppression rather than recursion; and
the census closes (`accepted + refused == attempts`, per-reason attribution, capacity overflow
counted rather than dropped). `tools/re_vblank.py --check-source --selftest` is 4/4 including a
negative case that perturbs the shipped `kVSyncQueryCounter` by +4. Full gate: 38 of 38 first-party
units compile-backed, 18 of 18 CTests pass, `clang-format` 0 violations (56 at baseline `9eb8b55`)
and 13 pre-existing clang-tidy findings, none of them in the code issue 0041 added. The brief's "17/18"
was about CTest only: the style stages were never green, and "18/18" must not be read as a green gate.

What is NOT established. No `fallback.calls`. No translated/executed block count for the real image.
No presented frame LOOKED AT — the product reaches a headless present, but `shot` needs the control
surface that field 0 does not reach, so there is no picture and no gameplay claim of any kind. No
guest state read back over the loopback surface. The heap leaf's seeded free list has not been
compared against the real guest body's own writes. `docs/issues/0040` names each remaining step in
order; issue 0041 is the run that took the first one and found four blockers.

The first image boundary is owned by `vagrant::VagrantRuntime`: it checks the measured resident PS-X
header and delegates publication to psxport's `loadPsxExeImage`. `vagrant::OverlayImages` adds exact
SHA-256 admission for the three reached TITLE/BATTLE/INITBTL `.PRG` files at their measured load
bases. Staged loads copy verified bytes; `adoptTransfer` authenticates an already completed CD sector
write in guest RAM without copying it again. Both paths call psxport's central executable-write
invalidation, retire the prior generation in its address slot, and register the new image identity.
`VagrantRuntime::createContext` now gives each Core its own `OverlayImages`. The finite resident
phase calls `readAndLoadTitle` at its measured TITLE read boundary. It uses the same whole-sector
acquisition as `readNativeFile`, which acknowledges a sector only when all 2,048 bytes arrive, then
authenticates the complete 271-sector buffer through `OverlayImages::loadTransfer` before any RAM
write or identity activation. The compile-backed synthetic contract refuses a 1,608-byte final
sector even when RAM already holds matching image bytes. A full-length altered replacement and a
short replacement both preserve RAM and the prior image generation. This is a native phase handoff,
not yet the process adapter or a real-title execution result.
The focused synthetic test proves changed payload refusal is atomic, unknown slot residency is
refused, and TITLE→BATTLE replacement executes a newly translated block with zero fallback. The
resident-memory adoption test refuses changed payload, changed final-sector padding, and foreign
tail residency before publishing a valid replacement with the same zero-fallback result.
The isolated real-input admission check accepted 3/3 exact TITLE/BATTLE/INITBTL files, resolved each
measured entry to its new image generation, and refused 1/1 changed TITLE file. The completed-sector
check read the same disc and adopted 3/3 exact transfers from guest RAM while refusing 3/3 changed
tails. Those checks mapped retail bytes but did not execute them. `vagrant::enterTitle` now admits the
exact resident `0x80042BD8` direct call only when PC, call/delay words, and both resident/TITLE
image generations agree. Its synthetic run executed the call, TITLE return, and resident continuation
through 3 translated blocks and 6 guest instructions with zero fallback; stale and altered call cases were
refused before dispatch. A read-only admission of the exact retail resident and TITLE bytes accepted
the call and refused a changed word without executing retail guest code. This remains structural
adapter coverage: no retail bytes have entered a current gameplay product, and no authenticated
resident-to-overlay gameplay route is claimed.

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

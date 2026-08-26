# Vagrant Story project state

This is the factual capability inventory. Epic intent is in `docs/project-goals.md`, atomic work in
`docs/issues/`, subsystem placement in `docs/codemap.md`, and ordered binary evidence in
`docs/re-frontier.md`.

| ID | Capability / observable outcome | State | Dependencies | Goals |
|---|---|---|---|---|
| S001 | Retail executable and reached overlays are reproducibly identified and provisioned | verified | — | G001 |
| S002 | Resident, TITLE, BATTLE, and INITBTL form a reproducible static-recompilation substrate | verified | S001 | G001 |
| S003 | Retail boot/platform delivery reaches TITLE through intact guest timing, CD, SPU, VBlank, and pad paths | partial | S002 | G001 |
| S004 | TITLE splashes, intro movie, Start-skip menu, and input are visibly presented | partial | S003 | G001 |
| S005 | Natural intro completion is classified and visibly reaches the same title/menu result | partial | S004 | G001 |
| S006 | BATTLE and INITBTL execute through initialization without the former emitter faults | partial | S002, S003 | G001 |
| S007 | The first decomp-seeded native game body is reached and byte-equivalent to the substrate | verified | S002 | G001 |
| S008 | BATTLE has an explicit measured completed-field fence and mapped viewport/projection boundary | partial | S006 | G001, G002 |
| S009 | BATTLE world geometry is produced natively from semantic game state | missing | S008 | G002 |
| S010 | BATTLE world rendering supports true widescreen | missing | S009 | G003 |
| S011 | Native world presentation interpolates semantic camera/object state | missing | S009 | G004 |
| S012 | The zero-argument launcher provisions, builds, and launches the intended product | verified | S001, S002 | G001 |
| S013 | Vagrant Story is playable through the complete game | missing | S003, S004, S006, S009 | G001 |
| S014 | Streaming CD/XA and audio behavior is owned beyond the verified intro path | partial | S003 | G001 |

## Current focus

S009 is the current focus: identify the reached BATTLE world submit owner and its semantic
camera/object inputs, then establish faithful native 4:3 production before widescreen or interpolation.
Issue 0027 tracks this atomic boundary.

## Capability details

### S001 — Reproducible retail inputs

Evidence: `tools/extract_exe.py`, `tools/extract_overlays.py`, and
`tools/verify_decomp_targets.py` identity-check the USA executable and reached TITLE/BATTLE/INITBTL
images from a user-supplied disc. Positive and altered-input controls refuse mismatched hashes, extra
overlay inputs, and missing provenance.

### S002 — Reproducible recompilation substrate

Evidence: `tools/ensure_recomp.py` derives the resident plus TITLE/BATTLE/INITBTL generated sources
from verified inputs and requires the reached overlay entries. The Clang product build links the
generated registry without tracked generated files; RE-02, RE-11, and RE-15 contain the measured seed
and routing evidence.

### S003 — Boot and platform delivery

Measured crt0, blocking and asynchronous CD, DMA4 completion, resident VBlank, and pad delivery carry
the intact guest from entry through TITLE. Claims C004, C011, and C012 plus RE-01/04/06/09/10 record
the binary and live evidence.

Gap: later platform-HLE windows, streaming modes, memory-card behavior, and complete game-lifetime
timing have not been verified.

### S004 — Visible TITLE path

Publisher/developer splashes, coherent 24-bit intro frames, and the recorded Start-skip route to a
readable Vagrant Story/New Game/Continue/Sound screen have live producer/control evidence in RE-12,
RE-13, and RE-14.

Gap: later menu interaction, all title transitions, teardown ownership, and complete title-loop
behavior remain unverified.

### S005 — Natural intro completion

The SHA-bound retail classifier proves natural return `0` and Start/right return `1` converge at one
epilogue and the sole caller ignores the result before common title/menu initialization (C028/I020).

Gap: no correctly provenanced natural-end menu screenshot exists. Issue 0026 resolved the earlier
black-menu report as a later BATTLE/loading capture, not as visible natural-menu proof.

### S006 — BATTLE/INITBTL execution

Generated BATTLE `0x800798A4` and INITBTL `0x800FA35C` are reached. Upstream emitter fixes close the
cross-overlay target, computed-dispatch, and shared-epilogue corruption causes recorded in issues
0022–0024; the last serialized evidence continues in BATTLE initialization for 240 seconds.

Gap: a room/world field, gameplay loop, later overlays, and complete BATTLE execution are not verified.

### S007 — First decomp-seeded native body

Evidence: `vagrant::heap::initHeap` is installed at measured `vs_main_initHeap 0x80043F74`; the live
mirror gate proves install, reach, and byte-equivalent effects, while the hermetic contract and
`tools/re_heap.py` negative controls pin the shipping implementation (C023).

### S008 — BATTLE completed-field and projection boundary

`tools/re_frame.py` uniquely measures presenter `0x8007629C`, dynamic-OT submit owner `0x8008A3A0`,
viewport initializer `0x800760CC`, the 320x240-to-320x224 convention, field center `(160,112)`,
projection word `0x8005E248`, and setter `0x8007CCF0`. The shipping source gate requires the retained
presenter super-call; Clang product and focused context tests link the per-Core completed-field fence.
A serialized exact-pin run reached it 9,073 times, proving the fence is live (C029/I013).

Gap: exactly one commit per completed BATTLE field is not proved, and the four requested 320x224
captures were byte-identical black frames while a separate diagnostic composition still showed the
title menu. The fence publishes guest-translated primitives and is not the semantic native world
producer. Issue 0027 owns the next proof.

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

Evidence: `run.sh` is a slim frozen-uv shim into `bootstrap.py`/`tools/run.py`; the launcher tests
cover dependency refusal, input resolution, isolated build orchestration, and current product
selection. `--prepare-only` provisions and builds without launching, while the no-argument route is
the player product path.

### S013 — Complete playable game

Missing capability: the port does not yet present verified BATTLE world gameplay or cover later
overlays, saves, complete audio, progression, and end-to-end completion.

### S014 — Later streaming and audio ownership

The initial menu WAVE reads, TITLE overlay transfer, intro STR/XA stream, and the completion behavior
that previously froze the movie have measured/live evidence in RE-04 and issue 0025.

Gap: later music, effects, voices, room streaming, XA teardown, and game-lifetime audio behavior are
not verified.

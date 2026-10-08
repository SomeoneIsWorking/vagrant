# Vagrant Story project state

Epic intent is in `docs/project-goals.md`, atomic work in `docs/issues/`, placement in
`docs/codemap.md`, ordered binary evidence in `docs/re-frontier.md`.

| id | capability | state | one-line evidence or gap |
|---|---|---|---|
| S001 | Retail executable and reached overlays are reproducibly identified and provisioned | verified | `tools/extract_exe.py`, `tools/extract_overlays.py` identity-check the USA executable and the reached TITLE/BATTLE/INITBTL images from the user's disc, with positive and altered-input controls |
| S002 | Offline-generated guest execution and its product selectors are absent | verified | generator, seed manifest, static registry, generated corpus and product selectors are gone; `tools/quality/structure.py` scans every first-party source and the build entry for them, and the launcher asserts it through that table |
| S003 | Finite native boot/platform owners preserve the measured route into TITLE/BATTLE phases | partial | 2026-10-04: the route is preserved through the whole resident bootstrap, the TITLE publisher/developer splash, `_saveFileExists`'s full stack and TITLE's background upload; it stops at `ResidentPhase::TitleIntroBoundary`, which has no owner yet. BATTLE is not reached |
| S004 | TITLE splashes, intro movie, Start-skip menu and input are visibly presented | partial | 2026-10-04: both TITLE splash halves are presented from the guest's own VRAM and captured (320x224, "Published by Square Electronic Arts L.L.C." at field 61, the SQUARESOFT logo at field 424, with the retail 32-field fades); the intro movie and Start-skip menu are still unreached because `_initIntroMovie` has no owner |
| S005 | Natural intro completion converges with the Start-skip route | partial | retail classifier proves return 0 (natural) and return 1 (Start) reach one epilogue; the route is unexercised in a run |
| S006 | BATTLE and INITBTL have authenticated runtime images and measured initialization entries | partial | `OverlayImages` admits both at their measured bases and invalidates the retired generation; the adapter does not re-enter BATTLE |
| S007 | The first decomp-seeded native game body preserves its measured ABI and memory effects | verified | `vagrant::heap::initHeap` preserves `vs_main_initHeap 0x80043F74`'s measured memory effects, pinned by `tests/test_game_heap.cpp` |
| S008 | BATTLE has an explicit measured completed-field fence and mapped viewport/projection boundary | partial | presenter `0x8007629C`, OT owner `0x8008A3A0`, viewport owner `0x800760CC`, centre `(160,112)`, projection word `0x8005E248` are mapped and unit-covered; BATTLE is never reached |
| S009 | BATTLE world geometry is produced natively from semantic game state | missing | no producer reads named BATTLE camera/object/material/animation/model inputs; the queue holds post-projection screen vertices |
| S010 | BATTLE world rendering supports true widescreen | missing | `BattleProjectionOwner::derive` ships but publishes no aspect; the guest's horizontal projection word is gameplay state, so the canvas widens, never `H` (issue 0037, `docs/battle-rendering.md`) |
| S011 | Native world presentation interpolates semantic camera/object state | missing | 60 fps is structurally impossible for this title — 2 (30 fps) or 4 (15 fps) fields per game frame, chosen at run time (issue 0039); no owned previous/current semantic snapshots exist yet |
| S012 | The zero-argument launcher provisions, builds and launches the intended product | partial | `run.sh` → `bootstrap.py` → `tools/run.py` composes every stage and refuses by stage name, covered by `tests/test_launcher.py`; never executed end to end here because the product slot was held |
| S013 | Vagrant Story is playable through the complete game | missing | no verified BATTLE world gameplay, later overlays, saves, progression or completion |
| S014 | Streaming CD/XA and audio behavior is owned beyond the verified intro path | partial | menu WAVE reads, TITLE transfer and the intro STR/XA stream have measured evidence; later music, effects, voices and XA teardown are unowned |
| S015 | The gameplay product executes authenticated guest images through psxport's dynarec-only runtime | partial | 2026-10-04 run: authenticated 337,920-byte resident plus TITLE.PRG, 1,406 translated blocks, 2,900,904 executed instructions, `fallback_blocks=0` with every per-reason counter zero, `faults=0`, 6 of 6 native leaves installed with 1 invocation and 1 original call that returned (issues 0042, 0043, 0044) |
| S016 | Hosted CI distinguishes repository policy from native product support on Linux, Windows, macOS and Android | partial | `.github/workflows/ci.yml` runs the asset-free verifier on one Linux host; no Windows, macOS or Android job exists because no native runtime boundary does |
| S017 | Vagrant Story load operations complete without loading-only waits or presentation; logos cancel through the recovered route | missing | no load operation has been classified for this title; enumerate its issuers and their waits first |

Comparison baseline (retail, the shipped disc): widescreen = S010, controls = S004/S012,
field rate = S011, loading = S017, platforms = S016.

Current focus: S004 — the TITLE save-file wait is owned: `_saveFileExists` (0x8006E988) reaches the
finite `TitleMemcardInit` instead of the guest `_initMemcard` whose libds queue cannot complete
(issues 0044, 0043), and the run now reaches `ResidentPhase::TitleIntroBoundary`. Own
`_initIntroMovie` next, then the Start-skip menu.
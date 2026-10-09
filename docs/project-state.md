# Vagrant Story project state

Epic intent is in `docs/project-goals.md`, atomic work in `docs/issues/`, placement in
`docs/codemap.md`, ordered binary evidence in `docs/re-frontier.md`.

| id | capability | state | one-line evidence or gap |
|---|---|---|---|
| S001 | Retail executable and reached overlays are reproducibly identified and provisioned | verified | `tools/extract_exe.py`, `tools/extract_overlays.py` identity-check the USA executable and the reached TITLE/BATTLE/INITBTL images from the user's disc, with positive and altered-input controls |
| S002 | Offline-generated guest execution and its product selectors are absent | verified | generator, seed manifest, static registry, generated corpus and product selectors are gone; `tools/quality/structure.py` scans every first-party source and the build entry for them, and the launcher asserts it through that table |
| S003 | Finite native boot/platform owners preserve the measured route into TITLE/BATTLE phases | verified | 2026-10-09: the resident bootstrap, TITLE publisher/developer splash, `_saveFileExists`, TITLE's background upload, the intro movie, the Start-skip menu and `vs_main_execTitle`'s tail (`_displayLoadingScreen`, `_loadBattlePrg`, `vs_battle_exec`) all run; New Game enters BATTLE and the opening cutscene runs past field 6000 with no fatal |
| S004 | TITLE splashes, intro movie, Start-skip menu and input are visibly presented | verified | 2026-10-09: splashes, the intro movie (STR at fields 900 and 1200), the title logo and the menu (field 1800) are presented, and a pad `start` tap skips the movie; pad input reaches the guest through the declared `guestPadBufferLayout()` |
| S005 | Natural intro completion converges with the Start-skip route | partial | the Start route is exercised end to end; the natural-completion route reaches the same epilogue by the retail classifier but is not yet run to its end |
| S006 | BATTLE and INITBTL have authenticated runtime images and measured initialization entries | verified | 2026-10-09: `_loadBattlePrg` (0x80041E4C) is owned natively (`readAndLoadBattle`), both images are published, and `vs_battle_exec` (0x800798A4) runs from the guest tail of `vs_main_execTitle` |
| S007 | The first decomp-seeded native game body preserves its measured ABI and memory effects | verified | `vagrant::heap::initHeap` preserves `vs_main_initHeap 0x80043F74`'s measured memory effects, pinned by `tests/test_game_heap.cpp` |
| S008 | BATTLE has an explicit measured completed-field fence and mapped viewport/projection boundary | partial | presenter `0x8007629C`, OT owner `0x8008A3A0`, viewport owner `0x800760CC`, centre `(160,112)`, projection word `0x8005E248` are mapped and unit-covered; BATTLE is never reached |
| S009 | BATTLE world geometry is produced natively from semantic game state | missing | no producer reads named BATTLE camera/object/material/animation/model inputs; the queue holds post-projection screen vertices |
| S010 | BATTLE world rendering supports true widescreen | missing | `BattleProjectionOwner::derive` ships but publishes no aspect; the guest's horizontal projection word is gameplay state, so the canvas widens, never `H` (issue 0037, `docs/battle-rendering.md`) |
| S011 | Native world presentation interpolates semantic camera/object state | missing | 60 fps is structurally impossible for this title — 2 (30 fps) or 4 (15 fps) fields per game frame, chosen at run time (issue 0039); no owned previous/current semantic snapshots exist yet |
| S012 | The zero-argument launcher provisions, builds and launches the intended product | partial | `run.sh` → `bootstrap.py` → `tools/run.py` composes every stage and refuses by stage name, covered by `tests/test_launcher.py`; never executed end to end here because the product slot was held |
| S013 | Vagrant Story is playable through the complete game | partial | the first BATTLE-overlay scene (opening cutscene at Duke Bardorba's manor, then 3D scenes and dialogue) runs through field 6000+; the speech bubble shows stray triangles; later overlays, saves, progression and completion are unverified |
| S014 | Streaming CD/XA and audio behavior is owned beyond the verified intro path | partial | 2026-10-09: menu WAVE reads, TITLE transfer, the intro STR/XA stream and the BATTLE program transfer have measured evidence; libds command completion is owned natively (`handleCdCommand`, `LibDsField::completeOwedCommand`, the `ds_cbready` override); later music, effects, voices and XA teardown are unowned |
| S015 | The gameplay product executes authenticated guest images through psxport's dynarec-only runtime | partial | resident, TITLE and BATTLE run under the dynarec with suspended guest calls spanning fields (`GuestPhase`, `ResumableGuestCall` with the R3000 register file restored on resume); executor counters are read at run end, not restated here (issues 0042-0044, 0045-0050) |
| S016 | Hosted CI distinguishes repository policy from native product support on Linux, Windows, macOS and Android | partial | `.github/workflows/ci.yml` runs the asset-free verifier on one Linux host; no Windows, macOS or Android job exists because no native runtime boundary does |
| S017 | Vagrant Story load operations complete without loading-only waits or presentation; logos cancel through the recovered route | missing | no load operation has been classified for this title; enumerate its issuers and their waits first |

Comparison baseline (retail, the shipped disc): widescreen = S010, controls = S004/S012,
field rate = S011, loading = S017, platforms = S016.

Current focus: S013 — the first BATTLE scene runs from New Game. Next: the speech-bubble triangle artifacts, then
the natural intro-completion route (S005) and the BATTLE world producers.

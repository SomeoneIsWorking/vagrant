---
id: 20
title: Unattended headless run stalls inside TITLE intro-movie wait: watchdog fires, zero presents, when no pad input arrives
status: open
symptom: headless vagrant_port with PSXPORT_NOPACE=1 and no PSXPORT_PAD_REPLAY hangs in ov_title_gen_8006F328 (overrides::dispatch), [watchdog] STUCK no frame presented, exit 134; PSXPORT_NATIVE_FRAMES cannot end it because the guest never yields
tags: gate,title,movie,nopace,re-13,re-14
created: 2026-08-24
updated: 2026-08-24
---

Measured 2026-08-24 while baselining the inherited tree (scratch/logs/inherited-baseline.log): an unattended headless run never presents a frame — _playIntroMovie spins inside one long TITLE call and the host frame loop never turns over, so PSXPORT_NATIVE_FRAMES cannot produce a clean exit and the ovhit atexit dump can never fire. With the recorded Start-skip replay (scratch/raw/re14_pad_delivery.pad) the same binary advances to the menu and fails fast at 0x800798A4 as documented. Not a regression of any 2026-08-24 change; RE-13's movie-frame evidence was captured on runs that advanced. Consequence for gates: this window has NO clean-exit path; assert advance + end state via pad replay instead.

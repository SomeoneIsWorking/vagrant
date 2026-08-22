---
id: C021
kind: claim
status: holds
created: 2026-08-22
tags: render,title,mdec,re-13
depends: game/render/title_movie.cpp#title_movie_dct_out_callback, game/render/title_movie.cpp#TitleMovieProducer::present, game/sync/vblank.cpp#vagrant_vblank_turn, tools/re_title_movie.py#measure
reconfirmed: 2026-08-22 19:09:18
verified_at: 2026-08-22 19:09:18
---

## Claim

Vagrant Story's first intro movie frames are directly presented from TITLE's intact guest STR/VLC/MDEC pipeline and live RGB24 VRAM

## Evidence

2026-08-22 against psxport 57a17a14: tools/re_title_movie.py --check-source --selftest derives/gates callback 0x8006F174 and frameComplete 0x800DEDDC, passing 3/3 negatives. The no-argument owned-disc shipping present_200 is coherent and 678339/691200 nonblack (98.14%), SHA256 0c3a55101d1b4e07a69c4eb39084d039d73936d920e3a32e1ea577900574ed7e. A compile-time VAGRANT_TEST_DISABLE_TITLE_MOVIE_PRODUCER build retains guest execution, completes 4000 DMA1 outputs, reaches the same 24-bit mode, and produces no present_200 before watchdog.

## What would falsify it

if the callback or completion word no longer derive from the exact TITLE bytes, the generated super-call is not retained, the disabled-producer build reaches present_200, or shipping present_200 no longer contains a coherent live movie frame

## Re-confirmed 2026-08-22 18:46:01

2026-08-22: shipping real-disc present_200 is coherent at 678339/691200 nonblack (sha256 0c3a5510...); producer-disabled build completed 4000 DMA1 outputs and reached 24-bit 320x224 but same-index present_200 was absent. re_title_movie.py --check-source --selftest 3/3.

## Re-confirmed 2026-08-22 19:09:18

2026-08-22 against recorded/built psxport 57a17a14: fresh no-argument owned-disc present_200 is coherent at 678339/691200 nonblack (sha256 0c3a5510...); producer-disabled build completes 4000 DMA1 outputs and reaches 24-bit but present_200 is absent; instrument 3/3.

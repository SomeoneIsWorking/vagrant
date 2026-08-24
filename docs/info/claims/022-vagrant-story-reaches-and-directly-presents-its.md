---
id: C022
kind: claim
status: holds
created: 2026-08-22
tags: render,title,re-14
depends: game/render/title_menu.cpp#title_menu_items_complete, game/render/title_menu.cpp#TitleMenuProducer::present, game/sync/vblank.cpp#vagrant_vblank_turn, tools/re_title_menu.py#measure
reconfirmed: 2026-08-24 19:41:40
verified_at: 2026-08-24 19:41:40
---

## Claim

Vagrant Story reaches and directly presents its first TITLE menu after an intact guest Start-skip transition

## Evidence

2026-08-22 against psxport d2266f4b and owned SLUS_010.40: shipping switches live 24-bit movie output to 15-bit 512x224 and presents readable Vagrant Story/New Game/Continue/Sound at present 64, 241809/691200 nonblack, SHA256 7b93beafa44f1b9a76c511e396b9bbc179f09c004eea5725e1b3e19194198529. VAGRANT_TEST_DISABLE_TITLE_MENU_PRODUCER retains the exact generated super and transition but hits the 65536-item queue fail-fast with same-index present absent. re_title_menu 3/3.

## What would falsify it

if TITLE.PRG no longer uniquely derives 0x800705AC, the generated super-call is removed, the producer-disabled build emits present 64, or the shipping capture is no longer a readable guest-built menu

## Re-confirmed 2026-08-24 19:41:40

2026-08-24 against psxport d2266f4b: shipping recorded-input run produced present_64 SHA256 7b93beafa44f1b9a76c511e396b9bbc179f09c004eea5725e1b3e19194198529, bit-identical to the readable prior capture, then failed honestly at 0x800798A4. Producer-disabled replay reached the same boundary with present_64 absent; the original forced-input schedule reproduced the 65536-item queue fail-fast with present_64 absent.

---
id: C020
kind: claim
status: holds
created: 2026-08-22
tags: render,title,runtime
depends: game/render/title_startup.cpp#title_draw_sprite, game/render/title_startup_recipe.cpp#TitleSpriteRecipe::decode, game/sync/vblank.cpp#vagrant_vblank_turn, game/core/vagrant_runtime.cpp#VagrantRuntime::registerOverrides, tools/re_title_startup.py#measure
reconfirmed: 2026-08-22 19:12:02
verified_at: 2026-08-22 19:12:02
---

## Claim

Vagrant Story's first publisher splash is directly produced from TITLE's measured _drawSprt semantics and guest-uploaded VRAM by VagrantRuntime: the owned-disc default run presents a legible non-black Square Electronic Arts splash before the 24-bit intro boundary

## Evidence

2026-08-22: tools/re_title_startup.py --check-source --selftest derives/gates 0x8006A778 and passes 3/3 negatives; real-disc ./run.sh writes scratch/screenshots/re12/positive_present_8.ppm at 29,499/691,200 non-black (4.27%), visually legible; test-only VAGRANT_TEST_DISABLE_TITLE_PRODUCER build writes scratch/screenshots/re12/negative_present_1.ppm at mean/extrema zero and no present_2 before the same 24-bit MDEC watchdog

## What would falsify it

if the measured TITLE leaf/owner no longer gates the shipping super-call, the owned-disc positive becomes black/absent, the disabled-producer negative still presents the splash, or the picture no longer comes from live guest VRAM

## Re-confirmed 2026-08-22 17:51:59

2026-08-22 tools/re_title_startup.py --check-source --selftest passed 3/3; full CTest passed; owned-disc scratch/screenshots/re12/positive_present_8.ppm is 29,499/691,200 non-black and legible, while scratch/screenshots/re12/negative_present_1.ppm is uniformly black and the test-only disabled producer yields no present_2

## Re-confirmed 2026-08-22 18:14:40

2026-08-22 against recorded/built psxport ad5cf802: shipping present_8 is exactly 29,499/691,200 non-black and readable; compile-time disabled producer retains guest execution but present_1 is 0/691,200 and present_2 is absent; both reach GP1 24-bit next boundary

## Re-confirmed 2026-08-22 18:46:01

2026-08-22: re_title_startup.py --check-source --selftest 3/3 and real-disc splash evidence remain valid after the VBlank one-present arbitration change; splash producer still wins fields with pending sprites.

## Re-confirmed 2026-08-22 19:09:18

2026-08-22 against recorded/built psxport 57a17a14: the no-argument shipping run advances through the retained-super splash producer into coherent 24-bit intro frames; re_title_startup.py --check-source --selftest remains 3/3.

## Re-confirmed 2026-08-22 19:12:02

Post-commit 4bd0718 positive real-disc capture preserves the publisher-splash path and 6/6 CTests pass; the VBlank selection gives an immediate splash priority for its field.

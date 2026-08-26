---
id: C028
kind: claim
status: holds
created: 2026-08-26
tags: title,menu,re-16
depends: tools/re_title_natural.py#measure
---

## Claim

Vagrant TITLE's natural intro timeout and Start/right skip return different values but converge at one epilogue; the sole retail caller ignores v0 and enters one common title-screen/menu initialization chain

## Evidence

tools/re_title_natural.py on SHA-1 f74a76e... TITLE.PRG measures natural >=2293 VSync ticks -> v0=0, input mask 0x820 -> v0=1, common epilogue 0x8006FC0C, sole caller 0x800713DC -> init 0x8006FE30 / SetDispMask(1) / menu init 0x8006FEC4; --selftest 3/3 changes the measured timer answer, refuses a destroyed continuation, and rejects mutated identity

## What would falsify it

a SHA-matching retail TITLE.PRG measurement finds another playback caller, distinct exit continuation, or any v0 consumer/branch before title/menu initialization

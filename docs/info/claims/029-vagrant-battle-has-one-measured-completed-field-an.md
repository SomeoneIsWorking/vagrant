---
id: C029
kind: claim
status: holds
created: 2026-08-26
tags: battle,render,widescreen,re-17
depends: tools/re_frame.py#measure
---

## Claim

Vagrant BATTLE has one retail-measured completed-field presenter and one game-owned viewport/projection boundary: presenter 0x8007629C restores OFX/OFY 160,112 each field, viewport initializer 0x800760CC receives 320x240 and produces the 320x224 convention, and setter 0x8007CCF0 owns projection word 0x8005E248

## Evidence

SHA-bound tools/re_frame.py uniquely measures the presenter, viewport initializer/call sequence, projection word/setter, dynamic OT submit owner 0x8008A3A0, and retained shipping super; --check-config --check-source --selftest passes 6/6, including destroyed viewport-width and shifted shipping-address refusals. A serialized exact-pin product run reached the retained completion fence 9,073 times. Its four requested guest captures were byte-identical black frames, so this proves fence reach but not a BATTLE world picture.

## What would falsify it

a SHA-matching retail BATTLE.PRG yields another complete presenter or viewport owner, the measured viewport call does not supply 320x240, the setter writes another projection word, or a future binary-backed world-owner measurement proves these calls belong only to a non-world phase

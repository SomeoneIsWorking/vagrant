---
id: C025
kind: claim
status: holds
created: 2026-08-25
tags: runtime,overlay,battle,re-15
depends: tools/re_overlay.py#measure, tools/extract_overlays.py#OVERLAYS, tools/ensure_recomp.py#generated_complete, tests/test_overlay_inputs.py#OverlayInputsTest
---

## Claim

Owned Vagrant bytes classify 0x800798A4 as BATTLE's entry, and the reached BATTLE+INITBTL+TITLE inventory emits and links against psxport aa0b2067

## Evidence

Resident direct jal at 0x80042C0C follows the two overlay loads; SHA-matched BATTLE offset 0x110A4 has the vs_battle_exec stack prologue while TITLE's same offset is undecodable data. extract_overlays verifies 3/3, ensure_recomp emits ov_battle_func_800798A4 and ov_initbtl_func_800FA35C, exact Clang build links vagrant_port, and CTest passes 7/7. This is static/build evidence only, not runtime entry.

## What would falsify it

Any owned image SHA changes; resident 0x80042C0C no longer directly targets 0x800798A4 after the two loads; generated output lacks either reached entry; exact aa0b2067 Clang build or overlay-input gate fails; or a runtime shows 0x800798A4 belongs to another resident image.

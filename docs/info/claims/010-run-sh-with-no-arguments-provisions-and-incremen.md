---
id: C010
kind: claim
status: holds
created: 2026-08-21
tags: launcher,substrate
depends: run.sh, tools/resolve_disc.py#resolve
---

## Claim

./run.sh with no arguments provisions and incrementally builds the verified resident substrate, then executes scratch/bin/vagrant_port; its honest current runtime boundary is the no-frame watchdog under 0x8001355C, not gameplay.

## Evidence

2026-08-21: vagrant_launcher_test positive/refusal cases passed; real ./run.sh runs resolved the configured USA CHD, matched SHA-1 fababcfd..., built with Clang, loaded all 4 RmlUi assets after the launcher fix, and reached the watchdog with no recomp miss or BIOS fatal. Repeated runs reported recomp up to date and rebuilt no generated TU. Reconfirmed after pinning and rebuilding against final psxport be381503: the launcher explicitly selected the still-frameless headless bootstrap, entered guest crt0/main, and sampled the watchdog under generated 0x8001355C.

## What would falsify it

if no-argument ./run.sh selects another executable, rewrites unchanged generated sources, omits framework assets, or reaches a runtime boundary other than the documented watchdog without the claim being refreshed

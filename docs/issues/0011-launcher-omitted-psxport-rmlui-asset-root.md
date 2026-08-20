---
id: 11
title: Launcher omitted psxport RmlUi asset root
status: resolved
symptom: run.sh reached the port but RmlUi reported 0 of 4 assets found and MENU UNAVAILABLE
tags: launcher,rmlui,assets
created: 2026-08-21
updated: 2026-08-21
---

## Root cause

The shell launcher was replaced by Python orchestration without carrying the resolved psxport checkout into `PSXPORT_ASSET_DIR`. RmlUi therefore resolved `assets/rml` against the game repo, which does not own framework UI assets.

## Resolution

`tools/run.py::launch` now exports the already-resolved psxport root when the operator did not provide an override. A real `./run.sh` rerun reported 4/4 assets, 3/3 fonts, and a 6-tab/35-row menu before reaching the known `0x8001355C` watchdog.

## Falsifier

Run `./run.sh` from the repo root with no `PSXPORT_ASSET_DIR`; any missing framework RmlUi asset falsifies the resolution.

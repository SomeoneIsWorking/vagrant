---
id: 0050
title: TITLE menu never drawn and RenderQueue aborted at 65,536 items
status: resolved
symptom: black menu, then abort
tags: S004,S006,S013,title,cd
created: 2026-10-09
updated: 2026-10-09
---

`game/title/title_exec_phase.cpp:TitleExecPhase`: the menu producer presented on exhausted turns and on every pass, never fenced at the guest's VSync.

## Fix

`TitleMenu::frameCompleted` is called only on a VSync suspension.

## Test

menu-fence test in `tests/test_vagrant_runtime.cpp`.

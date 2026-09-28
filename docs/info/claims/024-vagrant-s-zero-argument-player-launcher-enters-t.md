---
id: C024
kind: claim
status: holds
created: 2026-08-24
tags: launcher,bootstrap
depends: run.sh, bootstrap.py, tools/run.py#execute, tools/discdump.py#configure_command, tests/test_launcher.py, CMakeLists.txt, cmake/vagrant_port.cmake
reconfirmed: 2026-08-24 22:36:51
verified_at: 2026-08-24 22:36:51
---

## Claim

Vagrant's zero-argument player launcher enters through frozen uv, propagates that interpreter, builds only the current vagrant_port target with testing disabled, and accepts compilers by C11/C++20 capability rather than identity.

## Evidence

2026-08-24: 13/13 hermetic launcher checks exercised the shipping execute sequence and refusal ordering; custom compiler names were accepted without --version parsing; real GCC/G++ preflight passed; a real Clang player configure recorded BUILD_TESTING=OFF and Python3_EXECUTABLE=.venv/bin/python3, exposed no Vagrant test/quality targets, and the separate Clang vagrant_seam build plus launcher CTest passed. Per operator constraint, no game/window run was used as evidence.

## What would falsify it

if run.sh stops using uv run --frozen, a Python/CMake child escapes sys.executable, the player command invokes CTest/builds a test target, zero arguments select another product, or a capable compiler is refused by brand identity

## Re-confirmed 2026-08-24 22:36:51

Final re-verification: uv lock check, Ruff, 13/13 locked-Python unit tests, launcher CTest, codemap check, shell syntax, and diff check pass; real GCC/G++ capability preflight passes; Clang vagrant_seam build passed; the player CMake cache records BUILD_TESTING=OFF and the uv interpreter with no Vagrant test target registered.

## STALE as of 2026-09-28 — its SUBJECT was rewritten, and the falsifier fired correctly

`tools/info.py claim check` reports this claim stale against `run.sh` (1 commit since
verification). That is the checker working, and re-confirming it would be wrong, because two of its
named falsifiers are now true of the file it describes:

- it claims the launcher "builds only the current vagrant_port target with **C11/C++20 capability
  probes**" and names `tools/run.py#execute`. The rewritten launcher has no compiler probe and no
  `execute`; it defers entirely to the framework's `tools/project.py` for Lightrec and Lightning
  definitions.
- it names `cmake/vagrant_port.cmake`, which no longer exists; the product target is a plain
  `add_executable` in `CMakeLists.txt`.

**The parts that still hold** — frozen-uv entry through `run.sh`/`bootstrap.py`, `sys.executable`
propagation, `BUILD_TESTING=OFF` for the player build, and no test target reachable from the player
route — are covered by the new `tests/test_launcher.py` (16/16, every mutation of its subject shown
failing). What the new suite does NOT cover is the compiler-selection behaviour this claim recorded,
because that behaviour was deliberately removed rather than moved.

This claim is left `holds` with an unresolved staleness flag rather than silently re-confirmed, and
it is superseded for practical purposes by `docs/info/claims/030` and
`docs/info/instruments/010-tests-test-launcher-py.md`. Resolving it properly is a registry cleanup
for the operator: either rewrite its text to the rewritten launcher or mark it superseded by C030.
Either way, re-confirming the 2026-08-24 text would assert facts about code that is gone.

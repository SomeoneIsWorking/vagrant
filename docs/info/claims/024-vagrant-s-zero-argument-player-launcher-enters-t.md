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

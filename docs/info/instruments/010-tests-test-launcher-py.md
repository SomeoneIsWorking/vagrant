---
id: I010
kind: instrument
status: trusted
created: 2026-08-21
---

## Instrument

tests/test_launcher.py

## Validated by

2026-08-24: 13 hermetic checks exercise the shipping `execute()` sequence and its prepare-only
branch, prove refusal ordering, capture the headless exec environment, accept arbitrary compiler
names only after C11/C++20 capability probes, force incapable-compiler and missing-library outcomes,
check exact DNF/APT/Homebrew/winget commands, inspect both product/discdump CMake configurations for
testing-off and locked-Python arguments, and pin the frozen-uv shell/bootstrap/lock contract. A real
GCC/G++ preflight produced the opposite compiler-family result, while a real Clang player configure
recorded `BUILD_TESTING=OFF` and the uv `.venv` interpreter. The earlier live-run evidence remains
historical; the 2026-08-24 launcher change intentionally did not start a game/window.

## Known failure modes

(none recorded yet)

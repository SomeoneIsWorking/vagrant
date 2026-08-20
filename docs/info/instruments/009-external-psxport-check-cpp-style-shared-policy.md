---
id: I009
kind: instrument
status: trusted
created: 2026-08-21
---

## Instrument

external/psxport/tools/check_cpp_style.py — shared first-party clang-format, structure, and compile-database clang-tidy gate

## Validated by

The shared checker rejected the initially unformatted shipping sources. Its provisional full portability profile also rejected game/cd/ds_control_contract.h's pragma-once directive; after formatting and replacing the pragma with a guard, the final shared-policy invocation format- and size-checked 7 first-party files and linted all 6 compile-backed first-party Clang C++ translation units with exit 0. Revalidated after the shared checker made full-tree linting the normal default; CTest does not select its local-only `--tidy-touched` fast mode.

## Known failure modes

It can only lint translation units represented by the selected compile database; configure the
targets that own first-party TUs instead of treating an incomplete database as full coverage.

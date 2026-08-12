# Vagrant Story — a PC-native port (bootstrap stage)

A PC-native port of **Vagrant Story** (PS1, USA, `SLUS_010.40`) built on the
[psxport](https://github.com/SomeoneIsWorking/psxport) static-recompilation framework, vendored here as
`external/psxport`.

## Status: scaffolding. It does not run

Created 2026-08-12. There is no recompiled substrate, no port binary, and nothing about the game is
reverse-engineered yet. What exists:

- disc → executable provisioning from **your own** disc image (nothing game-derived is in this repo),
- the framework seam (`GameConfig` / `GameHooks`), compiling against the pinned framework, with every
  guest address honestly `0`,
- the project registries (`docs/re-frontier.md`, `docs/codemap.md`, `docs/info/`, `docs/issues/`),
- a vendored CC0 **matching decompilation** of this exact executable, `external/rood-reverse`, whose
  target images are *measured* to be byte-identical to the ones on this disc (21/21).

`docs/codemap.md` is the honest inventory; `docs/re-frontier.md` is the ordered RE chain and every entry
in it is `todo` or blocked.

## Getting started

```sh
git clone --recurse-submodules <this repo>          # or: git submodule update --init
cp .env.example .env && $EDITOR .env                # point it at your own disc image (.env is gitignored)
python3 tools/extract_exe.py                        # extract + identity-check SLUS_010.40
python3 tools/verify_decomp_targets.py              # does the vendored decomp target our bytes? (21/21)
cmake -S . -B build && cmake --build build --target vagrant_seam -j"$(nproc)"
python3 tools/re_frontier.py next                   # what to work on
```

`run.sh` is the eventual play launcher; today it does every real step and then stops, naming what blocks
the recompile.

## Requirements

cmake ≥ 3.21, pkg-config, SDL3, zlib, zstd, python3, a C++20 toolchain.

## Legal

**No game content is distributed here.** The disc image, the executable extracted from it and the
recompiled substrate derived from it are all yours and are gitignored. `tools/go_public.py` audits the
full history for disc-derived material and machine-specific paths.

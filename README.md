# Vagrant Story — a PC-native port (bootstrap stage)

A PC-native port of **Vagrant Story** (PS1, USA, `SLUS_010.40`) built on the
[psxport](https://github.com/SomeoneIsWorking/psxport) static-recompilation framework, vendored here as
`external/psxport`.

## Status: verified resident bootstrap, not gameplay

Created 2026-08-12. An owner-provisioned, gitignored resident substrate now builds and runs. It
executes measured crt0 and guest main, completes `_initRand`, and now completes `_diskReset`'s Pause
and Setmode through blocking libds control ownership. The next watchdog is sampled later under
generated `0x8001355C`. The bounded run has no recompilation miss or unimplemented-BIOS fatal; async
CD, reads, XA, overlays, and gameplay have not been reached. What exists:

- disc → executable provisioning from **your own** disc image (nothing game-derived is in this repo),
- the framework seam (`GameConfig` / `GameHooks`), compiling against the pinned framework,
- two measured RE groups: crt0/boot (RE-01) and all 20 non-empty `.PRG` load-base mappings into three
  overlay slots (RE-03), each gated back to the owned images by its instrument,
- the project registries (`docs/re-frontier.md`, `docs/codemap.md`, `docs/info/`, `docs/issues/`),
- a vendored CC0 **matching decompilation** of this exact executable, `external/rood-reverse`, whose
  target images are *measured* to be byte-identical to the ones on this disc (21/21).

`docs/codemap.md` is the honest inventory; `docs/re-frontier.md` is the ordered RE chain. RE-04 and
RE-08 own the loader and still-unmeasured platform-HLE boundaries exposed by the resident bootstrap.

## Getting started

**Do NOT use `git clone --recurse-submodules` or `git submodule update --init --recursive` on this
tree.** Both ABORT partway: `external/psxport/vendor/beetle-psx` nests a URL-less
`deps/lightning/gnulib`, and a recursive operation dies on it *after* cloning beetle and *before*
reaching `vendor/lucent` — leaving lucent's worktree empty with every file staged-deleted, and cmake
then failing on a missing `CMakeLists.txt`. Measured 2026-08-11; see
`external/psxport/docs/workspace/KNOWN-DEFECT-sync-submodules.md`. Init the vendors ONE AT A TIME,
non-recursively, exactly as `psxport/scripts/bootstrap-workspace.sh` does:

```sh
git clone <this repo> && cd vagrant
git submodule update --init external/psxport external/rood-reverse
for sm in vendor/beetle-psx vendor/lucent; do                    # one at a time, NEVER --recursive
  git -C external/psxport submodule update --init "$sm"
  git -C "external/psxport/$sm" reset --hard -q HEAD             # repairs a half-checkout
done
git -C external/psxport/vendor/beetle-psx submodule update --init deps/libchdr   # CHD disc access
cp .env.example .env && $EDITOR .env                # point it at your own disc image (.env is gitignored)
python3 tools/extract_exe.py                        # extract + identity-check SLUS_010.40
python3 tools/verify_decomp_targets.py              # does the vendored decomp target our bytes? (21/21)
cmake -S . -B build && cmake --build build --target vagrant_seam -j"$(nproc)"
python3 tools/re_frontier.py next                   # what to work on
```

`run.sh` is the eventual play launcher; today it provisions, emits, builds, and runs only this honest
resident-bootstrap boundary. Agents must never invoke it.

## Requirements

cmake ≥ 3.21, pkg-config, SDL3, zlib, zstd, python3, a C++20 toolchain.

## Legal

**No game content is distributed here.** The disc image, the executable extracted from it and the
recompiled substrate derived from it are all yours and are gitignored. `tools/go_public.py` audits the
full history for disc-derived material and machine-specific paths.

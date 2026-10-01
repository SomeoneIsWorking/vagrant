# Vagrant Story native/dynarec port

This repository targets the USA PlayStation release of **Vagrant Story**
(`SLUS_010.40`) as a native/dynarec hybrid built on
[psxport](https://github.com/SomeoneIsWorking/psxport). The player supplies the original disc; no
game content is distributed here.

## Current status

The dynarec title adapter exists and `./run.sh` builds and launches the `vagrant_port` product, which
executes the authenticated resident image and reached `.PRG` overlays through psxport's per-`Core`
Lightrec executor. There is no interpreter fallback, no engine selector, and no generated guest
corpus; `tools/verify.py` inspects the shipped binary's symbols to keep that true.

**The title has not been run against the real disc, so it does not yet play.** The adapter and its
gates are covered; the run is not, because the workspace's single product slot was held by another
agent (`docs/issues/0040`, which also states what a run would settle).
"the adapter exists" and "the title runs" are different claims and only the first is established.

Substantial title-owned work remains in the tree: authenticated resident and `.PRG` provisioning,
finite resident/TITLE phases, CD and memory-card ownership, pad delivery, native heap behavior, TITLE
presentation producers, a BATTLE field fence, and the measured retail facts each of them rests on. The
old runtime's successful splash/menu/BATTLE observations are historical evidence from the RETIRED
static-recomp product, not claims about this one. See `docs/project-state.md` for the capability
inventory, `docs/issues/` for the open defects, and `docs/re-frontier.md` for the ordered binary
evidence chain.

## Intended product

- Execute every non-native guest instruction on demand through psxport's per-Core Lightrec runtime.
- Never link, select, or fall back to an interpreter in gameplay; a separate test oracle is allowed.
- Preserve authenticated resident/overlay image identity and invalidate translated blocks when a
  reused `.PRG` slot changes generation.
- Keep deliberately native CD, save, input, timing, and rendering owners behind image-scoped
  overrides with original calls routed through the dynarec.
- Reach representative interactive BATTLE gameplay before claiming compatibility.
- Add semantic native world rendering, true widescreen, and presentation interpolation only after
  the faithful baseline is verified.

## Developer entry points

The launcher remains the stable player interface:

```sh
./run.sh
```

It provisions the authenticated measured inputs, configures, builds `vagrant_port`, and launches it.
`./run.sh --prepare-only` does everything except the launch, which opens a window and plays audio.
Help remains available with `./run.sh --help`. Focused migration checks do not use the launcher:

```sh
CXX=clang++ uv run --frozen python tools/verify.py
uv run --frozen python tools/extract_exe.py /path/to/disc.chd
uv run --frozen python tools/extract_overlays.py /path/to/disc.chd
```

The extraction commands place authenticated runtime inputs under gitignored `scratch/`. The normal
verifier configures a Ninja build under `build/verify`, builds and runs the native image/title
contracts AND the shipping product, inspects that product's symbols to prove no interpreter is
linked, checks first-party C++ with clang-format and clang-tidy, then runs the Python tests and
structure policy. It checks the Python launcher composition and its stage-named refusals, exact-image
provisioning behavior, the 1,200-line source cap, Python-only automation, absence of retired
execution dependencies, and product-code bans on direct stderr and process-environment reads.

The eventual fresh-clone product requires `uv`, CMake, Git, a C++20 compiler, and psxport's documented
native dependencies. Maintainer C++ verification uses Clang, clang-format, and clang-tidy; the shipped
project remains compatible with its supported GCC, Clang, and AppleClang toolchains.

## Legal

The disc image, extracted executable, and overlays remain user-owned and gitignored. The vendored CC0
`rood-reverse` decompilation is a readable source aid for the exact game revision, not independent
runtime evidence. `tools/go_public.py` audits repository history for game-derived content and
machine-specific paths.

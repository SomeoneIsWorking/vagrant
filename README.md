# Vagrant Story native/dynarec port

This repository targets the USA PlayStation release of **Vagrant Story**
(`SLUS_010.40`) as a native/dynarec hybrid built on
[psxport](https://github.com/SomeoneIsWorking/psxport). The player supplies the original disc; no
game content is distributed here.

## Current status

The former offline-generated guest-code product has been removed before the replacement runtime is
implemented. There is currently no runnable gameplay binary. `./run.sh` and the `vagrant_port` CMake
target fail at one explicit boundary: the title adapter to psxport's dynarec-only executor is missing.
They do not fall back to the removed pipeline or to an interpreter.

Substantial title-owned work remains in the tree as migration input: authenticated resident and
`.PRG` provisioning, finite resident/TITLE phases, CD and memory-card ownership, pad delivery, native
heap behavior, TITLE presentation producers, a BATTLE field fence, and the associated retail-backed
RE instruments. The old runtime's successful splash/menu/BATTLE observations are historical evidence,
not claims about the current product. See `docs/project-state.md` for the capability inventory and
`docs/re-frontier.md` for the evidence chain.

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

It currently exits with the missing-adapter message above. Help remains available with
`./run.sh --help`. Focused migration checks do not use the launcher:

```sh
uv run --frozen python tools/verify.py
uv run --frozen python tools/extract_exe.py /path/to/disc.chd
uv run --frozen python tools/extract_overlays.py /path/to/disc.chd
```

The extraction commands place authenticated runtime inputs under gitignored `scratch/`. The normal
verifier checks the Python launcher boundary, exact-image provisioning behavior, the 1,200-line source
cap, Python-only automation, absence of retired execution dependencies, and product-code bans on
direct stderr and process-environment reads.

The eventual fresh-clone product requires `uv`, CMake, Git, a C++20 compiler, and psxport's documented
native dependencies. Maintainer C++ verification uses Clang, clang-format, and clang-tidy; the shipped
project remains compatible with its supported GCC, Clang, and AppleClang toolchains.

## Legal

The disc image, extracted executable, and overlays remain user-owned and gitignored. The vendored CC0
`rood-reverse` decompilation is a readable source aid for the exact game revision, not independent
runtime evidence. `tools/go_public.py` audits repository history for game-derived content and
machine-specific paths.

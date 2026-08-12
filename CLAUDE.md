# Vagrant Story — working rules for THIS repo

A PC-native port of **Vagrant Story (PS1, USA, `SLUS_010.40` / SLUS-01040)** built on the
[psxport](https://github.com/SomeoneIsWorking/psxport) static-recompilation framework
(`external/psxport`). psxport recompiles the game's MIPS code to C and supplies the PSX platform layer;
this repo supplies the game — the seam, the RE, and the native reimplementations.

**The framework rules are NOT restated here. Read `external/psxport/CLAUDE.md`** — it is the authority
for how a game consumes psxport: the CVar ladder, the seam, `generated/` being sacrosanct, RE-first,
diagnostics through `lucent`, the registries, never editing `external/psxport`, and the standing USER
directive that **`./run.sh` is the user's and agents must never invoke it**. The workspace map is
`external/psxport/docs/workspace/WORKSPACE.md`; the multi-agent protocol is `…/PROTOCOL.md`; the
methodology is `…/docs/porting-a-new-psx-game.md`.

## THE STATE OF THIS PORT: nothing is reverse-engineered. Do not read anything else as progress

Created 2026-08-12. There is **no recompiled substrate, no port binary, and no RE'd guest address.**
`game/core/game_config.cpp` is all zeros with each field pointing at its open step in
`docs/re-frontier.md`. If something here looks like it works, check `docs/codemap.md` — the honest
inventory is short, and it is provisioning plus a compiling seam.

What DOES build today, and is the gate for a change to the seam:

```sh
cmake -S . -B build && cmake --build build --target vagrant_seam -j$(nproc)
```

`vagrant_seam` is an OBJECT library over `game/core/{game_config,game_hooks,main}.cpp`: it compiles but
does not link, which is the strongest check possible before a substrate exists — it proves this port's
`GameConfig`/`GameHooks` still satisfy the pinned framework's seam. `vagrant_port` is not configured at
all until `generated/rec_sources.cmake` exists, and CMake says so loudly at configure time.

## Start here, every task

```sh
python3 tools/re_frontier.py next            # which RE step is actually ready to work
python3 tools/info.py brief <words>          # what's already proven — and does it still hold?
python3 tools/catalog.py search <symptom>    # has this been hit (or ruled out) before?
```

Believe these over your instinct about what is known. End the task by writing back what you proved,
what you disproved, and any tool you caught lying. `tools/re_frontier.py` is a SHIM onto the shared
engine in `external/psxport/tools/port/`; do not grow a local copy of it.

## The thing that makes this title different: a CC0 MATCHING decomp of this exact executable

`external/rood-reverse` (submodule, CC0-1.0) is a byte-matching decompilation of SLUS-01040. **Measured
2026-08-12: all 21 code images it targets are byte-identical to the ones on our disc**
(`tools/verify_decomp_targets.py`, 21/21; the only uncovered image is the 0-byte `MENU/MENUA.PRG`). So
its 2,299 lines of `symbol_addrs.txt` name OUR addresses with no translation, and CC0 means we may take
**code and ideas** freely.

Three rules for using it, and they are the whole reason this section exists:

1. **A borrowed address is a HYPOTHESIS until measured against these bytes.** Where a reference and a
   measurement disagree, the measurement wins — the standing workspace rule. Nothing in
   `game_config.cpp` is filled in from it, and nothing should be filled in without the disassembly line
   that justifies it pasted alongside (the shape `spider1/game/core/game_config.cpp` uses).
2. **Never paste an overlay load base from it.** Its splat configs state a `vram` per module
   (`0x80068800` / `0x800F9800` / `0x80102800`); an overlay is keyed BY its load address, so a wrong
   base emits a whole module of correctly-decoded instructions at wrong addresses and every `jal`
   target, pointer test and router lookup goes silently wrong. Confirm on a running loader. RE-03.
3. **Its decomp.dev percentage is not our percentage.** Theirs is `objdiff` object identity; this port's
   axis is SBS byte-exact RAM parity. Neither implies the other, and quoting one as evidence about the
   other is how a port looks finished while nothing is gated.

Why it matters structurally: psxport's override registry wants `(addr, native, gen)` triples whose
native body byte-matches the substrate body, and a matching decomp is a **pre-verified supply of exactly
that**. Testing whether that supply can be consumed wholesale is the point of this port (`RE-07`), and
it is blocked until there is a substrate to match against. Importing a body before then is a hack with a
citation attached. Full detail: `docs/references.md`.

## Vagrant-Story-specific facts (measured 2026-08-12 — the whole list, nothing inferred)

- **One boot executable, no boot stub.** `SYSTEM.CNF` reads `BOOT = cdrom:\SLUS_010.40;1`,
  `STACK = 801fff00`, `TCB = 4`, `EVENT = 16`. So psxport's stub stage is unused, as in spyro/spider1.
- **`SLUS_010.40`** is 337,920 bytes, SHA-1 `fababcfd4325d42f350d95b3472874affeb0e48c`. PS-EXE header:
  entry `pc0 = 0x8001F544`, text `0x80010000 + 0x52000`, initial sp `0x801FFFF0`, `gp0 = 0` (so crt0
  sets `gp`).
- **21 `.PRG` code modules on the disc** — `BATTLE/BATTLE.PRG` (577,828 B), `TITLE/TITLE.PRG`,
  `ENDING/ENDING.PRG`, `BATTLE/INITBTL.PRG`, `GIM/SCREFF2.PRG` and 16 `MENU/*.PRG` (one of which,
  `MENUA.PRG`, is 0 bytes). This game's "overlays" are these files; their load bases are UNKNOWN here.
- **Top-level disc directories:** `BATTLE BG EFFECT ENDING EVENT GIM MAP MENU MOV MUSIC OBJ SE SMALL
  SOUND TITLE`, plus `SLUS_010.40`, `SYSTEM.CNF`, `DBGFNT.TIM` in the root (5,180 files listed).
- **It is a heavy streamer.** `ENDING/ENDING.XA` alone is 68 MB, plus `MOV/`, `MUSIC/`, `SE/`. The CD
  path is more load-bearing here than in the other ports in this workspace — expect RE-04 to matter early.
- **The executable links stock Sony libraries**, per the decomp's own section map: libcd (`SYS`, `BIOS`,
  `C_011`), libetc (`VSYNC`, `INTR`, `INTR_DMA`), libgpu, libspu, libpad (`PADENTRY`), libds, libc.
  That says which SHAPES to look for; it says nothing about where they are in this image.

Everything else about this game — crt0 layout, the loader, the frame loop, the OT/packet-pool dance,
the pad buffers, the scene model — is **unknown**. Do not let a plausible-sounding sentence in a doc
elsewhere stand in for it.

## The rules that bite hardest here

**Never guess a guest address or an overlay load base.** An un-RE'd `GameConfig` field stays `0` with a
TODO naming the frontier step. Zero is honest and psxport fails fast on it; a plausible wrong value
breaks boot in a way that reads as a framework bug. This repo has a *tempting* supply of addresses
sitting in `external/rood-reverse` — that is precisely why the rule is stated twice.

**Work the step `re_frontier.py next` names, not a downstream one.** The cardinal sin on a port is
faking a step's output before its RE is done; it makes a broken port look finished.

**Provision from your own disc; commit nothing derived from it.** Resolution order (one
implementation, `tools/resolve_disc.py`): CLI arg > `$PSXPORT_VAGRANT_DISC` > `.env` > a `*.chd` in the
repo root. `.env` is gitignored because the path is machine-specific; `.env.example` is the template.
`python3 tools/extract_exe.py` does the extraction and identity-checks the result.
`tools/go_public.py` audits the full history for disc images, extracted executables and `/home/<user>`
paths — run it before this repo is ever published.

**Everything transient goes in the gitignored `scratch/`, split by kind** (`scratch/bin/`,
`scratch/raw/`, `scratch/logs/`). **Never `/tmp`** — a small RAM-backed tmpfs on this machine; diagnose
"disk quota exceeded" with `quota -s`, not `df`.

## Where the framework source comes from — NEVER edit `external/psxport`

It is a **read-only pinned consumer**. Framework edits happen in the workspace's framework DEV CLONE
(`../psxport`) and nowhere else; `run.sh` re-syncs this submodule to the recorded gitlink, so an edit
made here is liable to be silently reverted mid-gate. Build against in-progress framework work without
touching the submodule:

```sh
cmake -S . -B build -DPSXPORT_DIR=/path/to/psxport      # or: PSXPORT_DIR=... ./run.sh   (user only)
```

`PSXPORT_DIR` defaults to the submodule, so a bare clone of this repo builds standalone — keep it that
way.

#!/usr/bin/env bash
# run.sh — the USER's build-and-play entry point for the Vagrant Story native PC port.
#
#   ./run.sh [/path/to/Vagrant Story (USA).chd]
#
# AGENTS MUST NOT RUN THIS (standing USER directive, external/psxport/CLAUDE.md): it is the windowed
# play launcher, it competes with the user's session for the tree, and its submodule re-sync silently
# reverts in-progress framework work to the recorded pin. Build explicitly instead:
#
#   cmake -S . -B build && cmake --build build --target vagrant_seam -j$(nproc)
#
# THERE IS NOTHING TO LAUNCH YET, and this script says so and stops rather than pretending. It does
# every step that IS real today — check the toolchain, announce which framework checkout is in play,
# sync submodules, resolve the disc, extract and identity-check SLUS_010.40, build what builds — and
# then refuses at the recompile step because RE-02's executable seed set/substrate has not been
# established. RE-03's 20 non-empty .PRG mappings are measured and gated; no substrate was emitted.
set -eu
cd "$(dirname "$0")"

say() { printf '\033[1;36m[run]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[run] error:\033[0m %s\n' "$*" >&2; exit 1; }

# ---- 0. toolchain -------------------------------------------------------------------------------
command -v cmake      >/dev/null || die "cmake not found"
command -v python3    >/dev/null || die "python3 not found"
command -v pkg-config >/dev/null || die "pkg-config not found"
pkg-config --exists sdl3 || die "SDL3 not found (Linux: SDL3-devel/libsdl3-dev; macOS: brew install sdl3)"
JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"

# ---- 0a. WHICH FRAMEWORK CHECKOUT IS THIS RUN BUILT FROM? ---------------------------------------
# Default: the pinned submodule, so `git clone && ./run.sh` works standalone. Override to build against
# the workspace's framework dev clone without touching the submodule. ANNOUNCED either way — a binary
# built from in-progress framework work must never be mistaken for one built from the pin.
PSXPORT_DIR="${PSXPORT_DIR:-external/psxport}"
[ -f "$PSXPORT_DIR/cmake/psxport.cmake" ] || die "PSXPORT_DIR=$PSXPORT_DIR is not a psxport checkout"
if [ "$PSXPORT_DIR" = "external/psxport" ]; then
  say "framework: external/psxport (pinned submodule $(git -C external/psxport rev-parse --short HEAD 2>/dev/null || echo '?'))"
else
  say "framework: *** $PSXPORT_DIR *** (DEV CLONE $(git -C "$PSXPORT_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')$(
        [ -n "$(git -C "$PSXPORT_DIR" status --porcelain 2>/dev/null)" ] && echo ' +dirty')) — NOT the recorded pin"
fi

# ---- 0b. sync git submodules --------------------------------------------------------------------
# ONE implementation, shared by every port: external/psxport/scripts/sync-submodules.sh. It lives
# INSIDE the submodule, so on a fresh clone it does not exist yet — init first, then call it.
# KNOWN DEFECT, do not trust its all-clear: it certifies pins it never checked, because
# `git submodule status --recursive` aborts on beetle-psx's URL-less nested deps/lightning/gnulib and
# the script's `|| true` swallows the non-zero exit. See
# external/psxport/docs/workspace/KNOWN-DEFECT-sync-submodules.md.
if command -v git >/dev/null && [ -f .gitmodules ]; then
  if [ ! -f external/psxport/scripts/sync-submodules.sh ]; then
    say "initializing git submodules…"
    git submodule update --init external/psxport || die "submodule init failed"
  fi
  bash external/psxport/scripts/sync-submodules.sh || die "submodule sync failed"
fi

# ---- 1. resolve the disc + extract the boot executable ------------------------------------------
# ONE implementation of the resolution order (CLI arg > $PSXPORT_VAGRANT_DISC > .env > *.chd drop-in):
# tools/resolve_disc.py, which extract_exe.py also uses. Duplicating it in shell is how two answers to
# "which disc" appear.
PSXPORT_DIR="$PSXPORT_DIR" python3 tools/extract_exe.py ${1:+"$1"} || die "executable provisioning failed"

# ---- 2. build what builds today -----------------------------------------------------------------
say "building the framework library + the seam check…"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPSXPORT_DIR="$(cd "$PSXPORT_DIR" && pwd)" >/dev/null \
  || die "cmake configure failed"
cmake --build build -j "$JOBS" --target vagrant_seam || die "seam check failed"

# ---- 3. STOP. There is no port binary yet ------------------------------------------------------
cat <<'EOF'

[run] ------------------------------------------------------------------------------------------
[run] STOPPING HERE, ON PURPOSE. There is no vagrant_port binary to launch.
[run]
[run] The next step is the static recompilation of SLUS_010.40, and it CANNOT run yet:
[run]   * RE-02  the executable seed arrays are empty; no substrate has been emitted or verified
[run]   * RE-03  is complete: 20 non-empty .PRG mappings are measured at three slots; MENUA is empty
[run]
[run] python3 tools/re_frontier.py next        -- the step that is actually ready to work
[run] python3 tools/verify_decomp_targets.py   -- what the vendored CC0 decomp does target, measured
[run] ------------------------------------------------------------------------------------------
EOF
exit 3

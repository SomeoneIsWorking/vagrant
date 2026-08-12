#!/usr/bin/env python3
"""discdump.py — locate (and, if needed, build) the framework's `discdump` tool, and read a disc.

`discdump` is psxport's own ISO9660/CHD reader (external/psxport/tools/discdump.cpp). Every disc read
in this repo goes through it rather than through a second implementation, so "what is on the disc" has
ONE answer.

WHICH framework checkout it is built from is the same decision CMake makes: $PSXPORT_DIR, defaulting
to the pinned submodule, so a bare clone works standalone. $PSXPORT_DISCDUMP overrides with a
prebuilt binary (useful for an agent that must not write into a submodule's build tree).

Nothing here caches a file list: a stale listing is a silent trap, and the reads are cheap.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def psxport_dir():
    d = os.environ.get("PSXPORT_DIR") or os.path.join(ROOT, "external", "psxport")
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    return d


def find(build_if_missing=True):
    """Return an absolute path to a usable `discdump`, or raise SystemExit(2) saying why not."""
    override = os.environ.get("PSXPORT_DISCDUMP")
    if override:
        if not os.access(override, os.X_OK):
            print(f"[discdump] $PSXPORT_DISCDUMP={override} is not executable", file=sys.stderr)
            raise SystemExit(2)
        return os.path.abspath(override)

    px = psxport_dir()
    if not os.path.isfile(os.path.join(px, "cmake", "psxport.cmake")):
        print(
            f"[discdump] PSXPORT_DIR={px} is not a psxport checkout — run "
            "`git submodule update --init external/psxport`, or set PSXPORT_DIR.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    for name in ("discdump", "discdump.exe"):
        cand = os.path.join(px, "build", "tools", name)
        if os.access(cand, os.X_OK):
            return cand
    if not build_if_missing:
        print(f"[discdump] not built under {px}/build/tools", file=sys.stderr)
        raise SystemExit(2)

    print(f"[discdump] building it from {px} (first run only)…", file=sys.stderr)
    jobs = str(os.cpu_count() or 4)
    for cmd in (
        ["cmake", "-S", px, "-B", os.path.join(px, "build"), "-DCMAKE_BUILD_TYPE=Release"],
        ["cmake", "--build", os.path.join(px, "build"), "-j", jobs, "--target", "discdump"],
    ):
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL)
        if r.returncode != 0:
            print(f"[discdump] FAILED: {' '.join(cmd)}", file=sys.stderr)
            raise SystemExit(2)
    return find(build_if_missing=False)


def listing(disc, dd=None):
    """Every file on the disc, as a list of (path, lba, size). Raises SystemExit(2) on a bad read."""
    dd = dd or find()
    out = subprocess.run([dd, "list", disc], capture_output=True, text=True)
    if out.returncode != 0:
        print(f"[discdump] list failed on {disc}:\n{out.stdout}{out.stderr}", file=sys.stderr)
        raise SystemExit(2)
    # `discdump list` prints a bare "DIR/" header line and then each file with its FULL path already
    # prefixed ("BATTLE/BATTLE.PRG   LBA 1100   577828 bytes"). Prepending the header directory again
    # was this parser's first bug: every path became "BATTLE/BATTLE/BATTLE.PRG", the coverage set
    # intersected to zero, and the verifier reported "covered by a config 0" while every module
    # matched — a coverage denominator that was wrong in the safe-looking direction.
    files = []
    for line in out.stdout.splitlines():
        s = line.strip()
        if not s or s.startswith("disc:") or s.startswith("root dir") or (s.endswith("/") and " " not in s):
            continue
        parts = s.split()
        if len(parts) >= 5 and parts[1] == "LBA":
            files.append((parts[0], int(parts[2]), int(parts[3])))
    if not files:
        print(f"[discdump] list produced ZERO files for {disc} — refusing to report an empty disc "
              "as a successful read", file=sys.stderr)
        raise SystemExit(2)
    return files


def get(disc, path_on_disc, outdir, dd=None):
    """Extract one file. `path_on_disc` uses forward slashes ('BATTLE/BATTLE.PRG'), exactly as
    `discdump list` prints it — the backslash form does NOT resolve. Returns the written path."""
    dd = dd or find()
    os.makedirs(outdir, exist_ok=True)
    out = subprocess.run([dd, "get", path_on_disc, disc, outdir], capture_output=True, text=True)
    dest = os.path.join(outdir, os.path.basename(path_on_disc))
    if out.returncode != 0 or not os.path.isfile(dest):
        print(f"[discdump] get {path_on_disc} failed:\n{out.stdout}{out.stderr}", file=sys.stderr)
        return None
    return dest

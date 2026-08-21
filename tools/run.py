#!/usr/bin/env python3
"""Provision, build, and launch the current Vagrant Story port target."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import discdump

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
EXE = ROOT / "scratch/bin/vagrant/SLUS_010.40"
PORT = ROOT / "scratch/bin/vagrant_port"


class Refusal(RuntimeError):
    """The requested run cannot be performed honestly."""


def say(message):
    print(f"[run] {message}", file=sys.stderr)


def command(args, *, env=None, quiet=False):
    result = subprocess.run(
        [str(value) for value in args],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL if quiet else None,
        check=False,
    )
    if result.returncode:
        raise Refusal(f"command failed ({result.returncode}): {' '.join(map(str, args))}")


def checked_clang(name, default):
    compiler = os.environ.get(name, default)
    if not shutil.which(compiler):
        raise Refusal(f"{name}={compiler} was not found")
    probe = subprocess.run(
        [compiler, "--version"], capture_output=True, text=True, check=False
    )
    if probe.returncode or "clang" not in (probe.stdout + probe.stderr).lower():
        raise Refusal(f"{name}={compiler} is not Clang")
    return compiler


def preflight():
    for tool in ("cmake", "git", "pkg-config"):
        if not shutil.which(tool):
            raise Refusal(f"{tool} was not found")
    if subprocess.run(["pkg-config", "--exists", "sdl3"], check=False).returncode:
        raise Refusal("SDL3 was not found by pkg-config (install SDL3-devel/libsdl3-dev)")
    return checked_clang("CC", "clang"), checked_clang("CXX", "clang++")


def sync_framework():
    command([sys.executable, ROOT / "tools/psxport_sync.py", "--auto"])
    psxport = Path(os.environ.get("PSXPORT_DIR", ROOT / "external/psxport")).resolve()
    if not (psxport / "cmake/psxport.cmake").is_file():
        raise Refusal(f"PSXPORT_DIR={psxport} is not a psxport checkout")
    head = subprocess.run(
        ["git", "-C", str(psxport), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    say(f"framework: {psxport} @ {head.stdout.strip() or 'unknown'}")
    return psxport


def ensure_reference():
    reference = ROOT / "external/rood-reverse/config/SLUS_010.40/splat.yaml"
    if reference.is_file():
        return
    if not (ROOT / ".gitmodules").is_file():
        raise Refusal("external/rood-reverse is absent and this checkout has no .gitmodules")
    say("initializing the executable-identity reference…")
    command(["git", "submodule", "update", "--init", "external/rood-reverse"])
    if not reference.is_file():
        raise Refusal("external/rood-reverse initialized without its SLUS_010.40 identity config")


def build_discdump(psxport, cc, cxx):
    return Path(discdump.build(psxport=psxport, cc=cc, cxx=cxx))


def verify_clang_build(build, target):
    compiler_files = sorted((build / "CMakeFiles").glob("*/CMakeCXXCompiler.cmake"))
    if not compiler_files or 'CMAKE_CXX_COMPILER_ID "Clang"' not in compiler_files[-1].read_text():
        raise Refusal(f"the configured {target} build is not using Clang")


def provision(disc, psxport, discdump):
    env = os.environ.copy()
    env["PSXPORT_DIR"] = str(psxport)
    env["PSXPORT_DISCDUMP"] = str(discdump)
    args = [sys.executable, ROOT / "tools/extract_exe.py"]
    if disc:
        args.append(disc)
    command(args, env=env)
    if not EXE.is_file():
        raise Refusal(f"executable provisioning produced no {EXE.relative_to(ROOT)}")
    command([sys.executable, ROOT / "tools/ensure_recomp.py"], env=env)


def configure_and_build(psxport, cc, cxx):
    say("building vagrant_port (incremental)…")
    command(
        [
            "cmake",
            "-S",
            ROOT,
            "-B",
            BUILD,
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DPSXPORT_DIR={psxport}",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
        ],
        quiet=True,
    )
    verify_clang_build(BUILD, "vagrant_port")
    command(
        [
            "cmake",
            "--build",
            BUILD,
            "--target",
            "vagrant_port",
            "-j",
            str(os.cpu_count() or 4),
        ]
    )
    if not os.access(PORT, os.X_OK):
        raise Refusal(f"build produced no executable at {PORT.relative_to(ROOT)}")


def launch(psxport):
    say("launching the resident bootstrap (known stop: VSync watchdog after SPU DMA completion)…")
    os.environ.setdefault("PSXPORT_ASSET_DIR", str(psxport))
    os.environ["PSXPORT_VK_HEADLESS"] = "1"
    os.execv(PORT, [str(PORT)])


def execute(
    disc,
    *,
    preflight_step=preflight,
    sync_step=sync_framework,
    reference_step=ensure_reference,
    discdump_step=build_discdump,
    provision_step=provision,
    build_step=configure_and_build,
    launch_step=launch,
):
    """Run the shipping sequence; injectable steps let tests exercise refusal ordering."""
    cc, cxx = preflight_step()
    psxport = sync_step()
    reference_step()
    discdump = discdump_step(psxport, cc, cxx)
    provision_step(disc, psxport, discdump)
    build_step(psxport, cc, cxx)
    launch_step(psxport)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Provision, build, and launch the current Vagrant Story resident-bootstrap port."
    )
    parser.add_argument("disc", nargs="?", help="Vagrant Story (USA) CHD; otherwise use env/.env/drop-in")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        execute(args.disc)
    except (OSError, Refusal) as error:
        print(f"[run] error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

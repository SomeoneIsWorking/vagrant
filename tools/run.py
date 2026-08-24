#!/usr/bin/env python3
"""Provision, build, and launch the current Vagrant Story port target."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

try:
    from tools import discdump
except ModuleNotFoundError:
    import discdump

ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = ROOT / "scratch/build/player"
DISCDUMP_BUILD_ROOT = ROOT / "scratch/build/discdump-player"
EXE = ROOT / "scratch/bin/vagrant/SLUS_010.40"
PORT = ROOT / "scratch/bin/vagrant_port"

PACKAGE_NAMES = {
    "cmake": {
        "fedora": "cmake",
        "debian": "cmake",
        "macos": "cmake",
        "windows": "Kitware.CMake",
    },
    "compiler": {
        "fedora": "gcc gcc-c++",
        "debian": "build-essential",
        "macos": "xcode-select --install",
        "windows": "LLVM.LLVM",
    },
    "git": {"fedora": "git", "debian": "git", "macos": "git", "windows": "Git.Git"},
    "pkg-config": {
        "fedora": "pkgconf-pkg-config",
        "debian": "pkg-config",
        "macos": "pkg-config",
        "windows": "pkgconf",
    },
    "glslc": {
        "fedora": "glslc",
        "debian": "glslc",
        "macos": "shaderc",
        "windows": "KhronosGroup.VulkanSDK",
    },
    "sdl3": {
        "fedora": "SDL3-devel",
        "debian": "libsdl3-dev",
        "macos": "sdl3",
        "windows": "sdl3:x64-windows",
    },
    "sdl3-image": {
        "fedora": "SDL3_image-devel",
        "debian": "libsdl3-image-dev",
        "macos": "sdl3_image",
        "windows": "sdl3-image:x64-windows",
    },
    "freetype2": {
        "fedora": "freetype-devel",
        "debian": "libfreetype-dev",
        "macos": "freetype",
        "windows": "freetype:x64-windows",
    },
    "zlib": {
        "fedora": "zlib-devel",
        "debian": "zlib1g-dev",
        "macos": "zlib",
        "windows": "zlib:x64-windows",
    },
    "libzstd": {
        "fedora": "libzstd-devel",
        "debian": "libzstd-dev",
        "macos": "zstd",
        "windows": "zstd:x64-windows",
    },
}

PKG_CONFIG_DEPENDENCIES = (
    ("sdl3", "SDL3 development files"),
    ("sdl3-image", "SDL3_image development files"),
    ("freetype2", "FreeType development files"),
    ("zlib", "zlib development files"),
    ("libzstd", "zstd development files"),
)


class Refusal(RuntimeError):
    """The requested run cannot be performed honestly."""


class Host:
    """Injectable host boundary for dependency discovery and compiler probes."""

    @staticmethod
    def which(name: str) -> str | None:
        return shutil.which(name)

    @staticmethod
    def run(args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        kwargs.pop("check", None)
        return subprocess.run([str(value) for value in args], check=False, **kwargs)

    @staticmethod
    def system() -> str:
        return platform.system()

    @staticmethod
    def linux_distribution() -> str:
        try:
            values = {}
            for line in (
                Path("/etc/os-release")
                .read_text(encoding="utf-8", errors="replace")
                .splitlines()
            ):
                key, separator, value = line.partition("=")
                if separator:
                    values[key] = value.strip().strip('"').lower()
        except OSError:
            return "unknown"
        return " ".join((values.get("ID", ""), values.get("ID_LIKE", ""))).strip()


def say(message: str) -> None:
    print(f"[run] {message}", file=sys.stderr)


def command(args: Sequence[object], *, env=None, quiet=False) -> None:
    result = subprocess.run(
        [str(value) for value in args],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL if quiet else None,
        check=False,
    )
    if result.returncode:
        raise Refusal(
            f"command failed ({result.returncode}): {' '.join(map(str, args))}"
        )


def host_family(host: Host) -> str:
    system = host.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    if system == "Linux":
        distribution = set(host.linux_distribution().split())
        if distribution & {"fedora", "rhel", "centos", "rocky", "almalinux"}:
            return "fedora"
        if distribution & {"debian", "ubuntu", "linuxmint", "pop"}:
            return "debian"
    return "unknown"


def install_instruction(host: Host, dependency: str) -> str:
    family = host_family(host)
    package = PACKAGE_NAMES[dependency].get(family)
    if package is None:
        return (
            f"install the native package providing {dependency}; no package mapping is recorded "
            f"for {host.system()}/{host.linux_distribution()}, so report that platform/version "
            "rather than guessing"
        )
    if family == "fedora":
        return f"please run: sudo dnf install {package}"
    if family == "debian":
        return f"please run: sudo apt install {package}"
    if family == "macos":
        if dependency == "compiler":
            return f"please run: {package}"
        return f"please run: brew install {package}"
    if dependency in {
        "sdl3",
        "sdl3-image",
        "freetype2",
        "zlib",
        "libzstd",
        "pkg-config",
    }:
        return f"please run: vcpkg install {package}"
    return f"please run: winget install {package}"


def require_tool(host: Host, name: str, dependency: str | None = None) -> str:
    resolved = host.which(name)
    if resolved is None:
        package = dependency or name
        raise Refusal(
            f"required tool {name!r} was not found; {install_instruction(host, package)}"
        )
    return resolved


def require_library(host: Host, module: str, label: str) -> None:
    try:
        result = host.run(
            ["pkg-config", "--exists", module],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError as error:
        raise Refusal(f"could not query {label}: {error}") from error
    if result.returncode:
        raise Refusal(
            f"required native library {label} ({module}) was not found; "
            f"{install_instruction(host, module)}"
        )


def require_compiler(host: Host, setting: str, language: str) -> str:
    compiler = require_tool(host, setting, "compiler")
    standard = "c11" if language == "c" else "c++20"
    try:
        probe = host.run(
            [compiler, f"-std={standard}", "-x", language, "-fsyntax-only", "-"],
            input="int main(void) { return 0; }\n",
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError as error:
        raise Refusal(f"could not execute compiler {setting!r}: {error}") from error
    if probe.returncode:
        raise Refusal(
            f"compiler {setting!r} cannot compile a minimal {standard} translation unit; "
            f"{install_instruction(host, 'compiler')}"
        )
    return compiler


def preflight(
    host: Host | None = None, environment: Mapping[str, str] | None = None
) -> tuple[str, str]:
    machine = host or Host()
    env = os.environ if environment is None else environment
    for tool in ("cmake", "git", "pkg-config", "glslc"):
        require_tool(machine, tool)
    cc_default = "clang" if machine.system() == "Windows" else "cc"
    cxx_default = "clang++" if machine.system() == "Windows" else "c++"
    cc = require_compiler(machine, env.get("CC", cc_default), "c")
    cxx = require_compiler(machine, env.get("CXX", cxx_default), "c++")
    for module, label in PKG_CONFIG_DEPENDENCIES:
        require_library(machine, module, label)
    return cc, cxx


def toolchain_build(root: Path, cc: str, cxx: str) -> Path:
    identity = hashlib.sha256(f"{cc}\0{cxx}".encode()).hexdigest()[:12]
    return root / identity


def cmake_configure_command(
    psxport: Path, cc: str, cxx: str, python: str = sys.executable
) -> list[object]:
    return [
        "cmake",
        "-S",
        ROOT,
        "-B",
        toolchain_build(BUILD_ROOT, cc, cxx),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_TESTING=OFF",
        f"-DPSXPORT_DIR={psxport}",
        f"-DCMAKE_C_COMPILER={cc}",
        f"-DCMAKE_CXX_COMPILER={cxx}",
        f"-DPython3_EXECUTABLE={python}",
    ]


def sync_framework() -> Path:
    command([sys.executable, ROOT / "tools/psxport_sync.py", "--auto"])
    configured = os.environ.get("PSXPORT_DIR")
    psxport = Path(configured or ROOT / "external/psxport").resolve()
    if not (psxport / "cmake/psxport.cmake").is_file():
        raise Refusal(f"PSXPORT_DIR={psxport} is not a psxport checkout")
    head = subprocess.run(
        ["git", "-C", str(psxport), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    dirty = subprocess.run(
        ["git", "-C", str(psxport), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    suffix = " +dirty" if dirty.stdout.strip() else ""
    if configured:
        say(
            f"framework: *** {psxport} *** (DEV CLONE "
            f"{head.stdout.strip() or 'unknown'}{suffix}) — NOT the recorded pin"
        )
    else:
        say(
            f"framework: external/psxport -> {psxport} @ "
            f"{head.stdout.strip() or 'unknown'}{suffix}"
        )
    return psxport


def ensure_reference() -> None:
    reference = ROOT / "external/rood-reverse/config/SLUS_010.40/splat.yaml"
    if reference.is_file():
        return
    if not (ROOT / ".gitmodules").is_file():
        raise Refusal(
            "external/rood-reverse is absent and this checkout has no .gitmodules"
        )
    say("initializing the executable-identity reference…")
    command(["git", "submodule", "update", "--init", "external/rood-reverse"])
    if not reference.is_file():
        raise Refusal(
            "external/rood-reverse initialized without its SLUS_010.40 identity config"
        )


def build_discdump(psxport: Path, cc: str, cxx: str) -> Path:
    build = toolchain_build(DISCDUMP_BUILD_ROOT, cc, cxx)
    return Path(
        discdump.build(
            psxport=psxport,
            build_dir=build,
            cc=cc,
            cxx=cxx,
            python=sys.executable,
        )
    )


def provision(disc: str | None, psxport: Path, discdump_path: Path) -> None:
    env = os.environ.copy()
    env["PSXPORT_DIR"] = str(psxport)
    env["PSXPORT_DISCDUMP"] = str(discdump_path)
    args = [sys.executable, ROOT / "tools/extract_exe.py"]
    if disc:
        args.append(disc)
    command(args, env=env)
    if not EXE.is_file():
        raise Refusal(f"executable provisioning produced no {EXE.relative_to(ROOT)}")
    overlay_args = [sys.executable, ROOT / "tools/extract_overlays.py"]
    if disc:
        overlay_args.append(disc)
    command(overlay_args, env=env)
    command([sys.executable, ROOT / "tools/ensure_recomp.py"], env=env)


def configure_and_build(psxport: Path, cc: str, cxx: str) -> None:
    build = toolchain_build(BUILD_ROOT, cc, cxx)
    say("building vagrant_port (incremental)…")
    command(cmake_configure_command(psxport, cc, cxx), quiet=True)
    command(
        [
            "cmake",
            "--build",
            build,
            "--target",
            "vagrant_port",
            "-j",
            str(os.cpu_count() or 4),
        ]
    )
    if not os.access(PORT, os.X_OK):
        raise Refusal(f"build produced no executable at {PORT.relative_to(ROOT)}")


def launch(psxport: Path) -> None:
    say(
        "launching the current resident + TITLE/BATTLE startup frontier headlessly; BATTLE "
        "later BATTLE initialization and gameplay remain fail-fast boundaries…"
    )
    environment = os.environ.copy()
    environment.setdefault("PSXPORT_ASSET_DIR", str(psxport))
    environment["PSXPORT_VK_HEADLESS"] = "1"
    os.execve(PORT, [str(PORT)], environment)


def execute(
    disc: str | None,
    *,
    prepare_only: bool = False,
    preflight_step=preflight,
    sync_step=sync_framework,
    reference_step=ensure_reference,
    discdump_step=build_discdump,
    provision_step=provision,
    build_step=configure_and_build,
    launch_step=launch,
) -> None:
    """Run the shipping sequence; injectable steps keep tests hermetic."""
    cc, cxx = preflight_step()
    psxport = sync_step()
    reference_step()
    discdump_path = discdump_step(psxport, cc, cxx)
    provision_step(disc, psxport, discdump_path)
    build_step(psxport, cc, cxx)
    if prepare_only:
        say("Vagrant Story is built and ready.")
        return
    launch_step(psxport)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision, build, and launch the current Vagrant Story runtime frontier."
    )
    parser.add_argument(
        "disc",
        nargs="?",
        help="Vagrant Story (USA) CHD; otherwise use env/.env/drop-in",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="provision and build the current product without launching it",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        execute(args.disc, prepare_only=args.prepare_only)
    except (OSError, Refusal, SystemExit) as error:
        print(f"[run] error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The player launcher's product boundary, and its refusals.

The break-first migration left exactly one unavailable boundary: a Vagrant Story adapter to
psxport's dynarec-only executor. The adapter now exists (`game/core/application.{h,cpp}`), so this
module no longer refuses a product — it provisions the measured inputs, builds the one shipping
executable, and launches it.

WHAT MOVED OUT OF HERE, and why. Media discovery stays in `tools/resolve_disc.py` and
`tools/extract_*.py` because those already own the identity rules, and a second copy of "which bytes
are this title's" is a second answer. Toolchain discovery stays in this module because it is the
launcher's concern and nothing else needs it. The product itself is the C++ `Application`; the
launcher only decides when to build it and when to refuse.
"""

from __future__ import annotations

import os
import platform
import runpy
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


class ProductUnavailable(RuntimeError):
    """A required product input, tool, or build step is missing or unverified."""


# The one shipping executable, and the one target that produces it. Naming both here means the
# launcher and the build cannot disagree about what "the product" is.
PRODUCT_TARGET = "vagrant_port"

# The measured inputs, relative to the repository root. `tools/extract_exe.py` and
# `tools/extract_overlays.py` own how each is authenticated; this names where they land.
RESIDENT_IMAGE = Path("scratch/bin/vagrant/SLUS_010.40")
OVERLAY_DIRECTORY = Path("scratch/bin/overlays")

REQUIRED_TOOLS = ("cmake", "git", "ninja")

# Where the framework lands when `PSXPORT_DIR` is not set: a symlink to the workspace's single
# writable checkout, or a private clone at `psxport.pin` on a fresh machine.
DEFAULT_FRAMEWORK = Path("external/psxport")


def _distribution() -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if key == "ID" and separator:
                return value.strip().strip('"').lower()
    except OSError:
        pass
    return "unknown"


def install_command(package: str) -> str | None:
    """The exact command a player runs to install `package` on this host, or None if unmapped."""
    system = platform.system()
    if system == "Darwin":
        return {
            "cmake": "brew install cmake",
            "git": "xcode-select --install",
            "ninja": "brew install ninja",
        }.get(package)
    if system == "Windows":
        return {
            "cmake": "winget install Kitware.CMake",
            "git": "winget install Git.Git",
            "ninja": "winget install Ninja-build.Ninja",
        }.get(package)
    if system != "Linux":
        return None
    if _distribution() in {"fedora", "rhel", "centos", "rocky", "almalinux"}:
        return {"cmake": "sudo dnf install cmake", "git": "sudo dnf install git", "ninja": "sudo dnf install ninja-build"}.get(
            package
        )
    if _distribution() in {"debian", "ubuntu", "linuxmint", "pop"}:
        return {"cmake": "sudo apt install cmake", "git": "sudo apt install git", "ninja": "sudo apt install ninja-build"}.get(
            package
        )
    return None


def require_tool(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is not None:
        return resolved
    command = install_command(name)
    if command:
        raise ProductUnavailable(f"{name} not found. Install it with: {command}")
    raise ProductUnavailable(
        f"{name} not found, and no install command is recorded for {platform.system()}/{_distribution()}; "
        "install it with your platform package manager and rerun"
    )


def framework_checkout(environment: Mapping[str, str], root: Path) -> Path:
    """Resolve the framework, establishing the workspace symlink when the environment does not.

    `PSXPORT_DIR` wins so an agent or CI job can point at a specific checkout. Otherwise the
    repository's own sync tool establishes `external/psxport`, which is a symlink to the workspace's
    single writable framework in this workspace and a private clone at `psxport.pin` anywhere else.
    """
    configured = environment.get("PSXPORT_DIR")
    if configured:
        framework = Path(configured)
        return framework if framework.is_absolute() else root / framework
    subprocess.run(
        [sys.executable, "tools/psxport_sync.py", "--auto"],
        cwd=root,
        check=True,
        env=dict(environment),
    )
    framework = root / DEFAULT_FRAMEWORK
    if not (framework / "cmake" / "psxport.cmake").is_file():
        raise ProductUnavailable(f"{framework} has no cmake/psxport.cmake — it is not a psxport checkout")
    return framework


def load_framework_policy(framework: Path, relative: str) -> dict[str, object]:
    """Load one of the framework's Python policy modules as a namespace.

    The framework's own `tools/` directory is on `sys.path` for the duration, because those modules
    import their siblings (`automation.process`) as top-level names. That is the framework's
    packaging, not this port's, so the import path is established here rather than by copying its
    policy into this repository — a copy would drift silently and would be a second answer to "which
    Lightrec revision does the player build".
    """
    module = framework / "tools" / relative
    if not module.is_file():
        raise ProductUnavailable(f"psxport checkout is missing {relative}: {module}")
    tools = str(framework / "tools")
    sys.path.insert(0, tools)
    try:
        return runpy.run_path(str(module))
    finally:
        sys.path.remove(tools)


def configured_build(build: Path, framework: Path, environment: Mapping[str, str]) -> list[str]:
    """The configure line for the player's build directory.

    The framework's own `tools/project.py` supplies the Lightrec and Lightning definitions, so the
    dependency versions the player builds against are the framework's policy and not a second list
    maintained here.
    """
    arguments = [
        "cmake",
        "-S",
        ".",
        "-B",
        str(build),
        "-G",
        "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_TESTING=OFF",
        f"-DPSXPORT_DIR={framework}",
        f"-DPython3_EXECUTABLE={sys.executable}",
    ]
    policy = load_framework_policy(framework, "project.py")
    try:
        arguments.extend(policy["lightrec_cmake_definitions"](environment))
        arguments.extend(policy["lightning_cmake_definitions"](environment))
    except policy["ToolError"] as error:
        raise ProductUnavailable(str(error)) from error
    return arguments


def build_product(build: Path, environment: Mapping[str, str], jobs: int) -> None:
    """Build the one shipping executable. A build failure is a refusal, not a traceback."""
    result = subprocess.run(
        ["cmake", "--build", str(build), "--parallel", str(jobs), "--target", PRODUCT_TARGET],
        env=dict(environment),
        check=False,
    )
    if result.returncode != 0:
        raise ProductUnavailable(f"the {PRODUCT_TARGET} product build failed")


def cpu_jobs() -> int:
    """Parallelism for the build. A cgroup-limited host reports its own affinity mask, not the
    machine's core count, so this does not oversubscribe the container it is running in."""
    return max(1, len(os.sched_getaffinity(0)))


def provision_inputs(root: Path, environment: Mapping[str, str], disc: str | None) -> None:
    """Authenticate and write the measured inputs, refusing rather than launching on absent media.

    Both tools raise on a hash mismatch against the decompilation's own target, so a wrong disc
    cannot reach the product. They are separate tools because their identity rules are separate:
    the resident executable is authenticated against `SLUS_010.40/splat.yaml` and each overlay
    against its own module config.
    """
    for tool in ("tools/extract_exe.py", "tools/extract_overlays.py"):
        command = [sys.executable, tool]
        if disc is not None:
            command.append(disc)
        result = subprocess.run(command, cwd=root, env=dict(environment), check=False)
        if result.returncode != 0:
            raise ProductUnavailable(f"input provisioning failed while running {tool}")


def missing_inputs() -> list[Path]:
    """The measured inputs this product needs and does not have. Empty means ready to build."""
    missing: list[Path] = []
    if not RESIDENT_IMAGE.is_file():
        missing.append(RESIDENT_IMAGE)
    if not OVERLAY_DIRECTORY.is_dir():
        missing.append(OVERLAY_DIRECTORY)
    return missing


def launch_environment(framework: Path, environment: Mapping[str, str]) -> dict[str, str]:
    """Apply psxport's own shipping launch policy at the final product-exec boundary.

    `product` names this title's run-log directory under the OS user-data location. psxport requires
    it: the log is the only copy of what the product said, and it must not land in another title's
    file. Omitting it raises, which is how a fresh clone would otherwise fail to launch at all.
    """
    policy = load_framework_policy(framework, "port/launch_environment.py")
    apply_policy = policy.get("player_environment")
    if not callable(apply_policy):
        raise ProductUnavailable(
            f"invalid psxport shipping launch policy: {framework / 'tools' / 'port' / 'launch_environment.py'}"
        )
    return apply_policy(environment, product="vagrant")


def provision_build_and_launch(
    disc: str | None,
    *,
    build: Path,
    root: Path,
    environment: Mapping[str, str],
    jobs: int,
) -> int:
    """The zero-argument product route. Returns the product's own exit code."""
    for tool in REQUIRED_TOOLS:
        require_tool(tool)
    framework = framework_checkout(environment, root)
    provision_inputs(root, environment, disc)
    missing = missing_inputs()
    if missing:
        named = ", ".join(str(path) for path in missing)
        raise ProductUnavailable(f"provisioning finished but these measured inputs are still absent: {named}")
    configured = subprocess.run(
        configured_build(build, framework, environment), cwd=root, env=dict(environment), check=False
    )
    if configured.returncode != 0:
        raise ProductUnavailable("the product configure failed")
    build_product(build, environment, jobs)
    return subprocess.run(
        [str(build / PRODUCT_TARGET)],
        cwd=root,
        env=launch_environment(framework, environment),
        check=False,
    ).returncode


def product_stage_names() -> Sequence[str]:
    """The ordered stages the launcher runs. Named so a test can assert the product is built, not
    merely configured — the failure this replaces was a launcher that reported success and launched
    nothing."""
    return ("resolve framework", "provision measured inputs", "configure", f"build {PRODUCT_TARGET}", "launch")

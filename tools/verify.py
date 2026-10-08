#!/usr/bin/env python3
"""Verify Vagrant's available native contracts and repository-owned policy."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "verify"
NATIVE_TESTS = frozenset({
    "vagrant_battle_projection",
    "vagrant_ds_control_contract",
    "vagrant_dynarec_dispatch",
    "vagrant_game_heap",
    "vagrant_image_contract",
    "vagrant_native_runtime",
    "vagrant_overlay_images",
    "vagrant_title_entry",
    "vagrant_title_transfer",
    "vagrant_title_startup_recipe",
})
# The shipping product, built so a compile failure on a player's machine shows up here.
PRODUCT_TARGET = "vagrant_port"
# CTest names that must be registered.
REQUIRED_TESTS = NATIVE_TESTS
sys.path.insert(0, str(ROOT))

from tools.quality.structure import check_repository


def run(*command: object, capture: bool = False) -> subprocess.CompletedProcess[str]:
    arguments = [str(part) for part in command]
    print(f"[verify] {' '.join(arguments)}", flush=True)
    return subprocess.run(arguments, cwd=ROOT, check=False, text=True, capture_output=capture)


def resolve_framework() -> Path | None:
    configured = os.environ.get("PSXPORT_DIR")
    if not configured and run(sys.executable, ROOT / "tools" / "psxport_fetch.py", "--auto").returncode:
        return None
    framework = Path(configured) if configured else ROOT / "external" / "psxport"
    if not framework.is_absolute():
        framework = ROOT / framework
    if not (framework / "tools" / "check_cpp_style.py").is_file():
        print(f"[verify] REFUSED: psxport C++ policy owner is missing: {framework}", file=sys.stderr)
        return None
    return framework.absolute()


def verify_compile_coverage() -> bool:
    listed = run(
        "git", "ls-files", "--cached", "--others", "--exclude-standard", "--",
        "*.cc", "*.cpp", "*.cxx", capture=True,
    )
    if listed.returncode:
        print(listed.stderr, file=sys.stderr)
        return False
    sources = {
        (ROOT / relative).resolve()
        for relative in listed.stdout.splitlines()
        if relative.split("/", 1)[0] not in {"build", "external", "generated", "scratch", "vendor"}
        and (ROOT / relative).is_file()
    }
    if not sources:
        print("[verify] REFUSED: found zero first-party C++ translation units", file=sys.stderr)
        return False
    database = BUILD / "compile_commands.json"
    try:
        entries = json.loads(database.read_text(encoding="utf-8"))
        compiled = {
            (Path(entry["directory"]) / entry["file"]).resolve()
            for entry in entries
        }
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"[verify] REFUSED: unreadable C++ compile database: {error}", file=sys.stderr)
        return False
    missing = sorted(sources - compiled)
    print(f"[verify] compile-backed {len(sources) - len(missing)} of {len(sources)} first-party C++ units")
    for source in missing:
        print(f"[verify] REFUSED: C++ unit absent from compile database: {source.relative_to(ROOT)}", file=sys.stderr)
    return not missing


def verify_native(framework: Path) -> bool:
    configured = run(
        "cmake",
        "-S", ROOT,
        "-B", BUILD,
        "-G", "Ninja",
        "-DBUILD_TESTING=ON",
        f"-DPython3_EXECUTABLE={sys.executable}",
        f"-DPSXPORT_DIR={framework}",
    )
    if configured.returncode:
        return False
    if not verify_compile_coverage():
        return False
    built = run("cmake", "--build", BUILD, "--target", *sorted(NATIVE_TESTS), PRODUCT_TARGET)
    if built.returncode:
        return False

    # Inspect the product link before ctest, independent of its result.
    product_ok = verify_product_link(framework)

    discovered = run("ctest", "--test-dir", BUILD, "--show-only=json-v1", capture=True)
    if discovered.returncode:
        print(discovered.stdout + discovered.stderr, file=sys.stderr)
        return False
    try:
        names = {test["name"] for test in json.loads(discovered.stdout)["tests"]}
    except (KeyError, TypeError, ValueError) as error:
        print(f"[verify] REFUSED: unreadable CTest inventory: {error}", file=sys.stderr)
        return False
    if not REQUIRED_TESTS.issubset(names):
        print(f"[verify] REFUSED: missing required contracts: {sorted(REQUIRED_TESTS - names)}", file=sys.stderr)
        return False
    print(
        f"[verify] discovered {len(REQUIRED_TESTS)} of {len(REQUIRED_TESTS)} required contracts"
    )
    contracts_ok = run("ctest", "--test-dir", BUILD, "--output-on-failure", "--no-tests=error").returncode == 0
    return contracts_ok and product_ok


def verify_product_link(framework: Path) -> bool:
    """Check the shipped product for banned execution paths and report what is linked.

    The Lightrec per-block interpreter is expected; its use is `fallback.calls` at run time.
    """
    product = BUILD / PRODUCT_TARGET
    if not product.is_file():
        print(f"[verify] REFUSED: the product executable was not built: {product}", file=sys.stderr)
        return False
    result = run("nm", "-C", str(product), capture=True)
    if result.returncode:
        print(f"[verify] REFUSED: cannot inspect the product's symbols: {result.stderr}", file=sys.stderr)
        return False
    symbols = result.stdout

    # The retired generation and generated-corpus artifact.
    retired = ("xemu_interpret_block", "int_exec", "psx_cpu_interpret_step")
    linked_retired = [name for name in retired if name in symbols]
    corpus_candidates = ("xemu_rom", "xemu_rom_entry", "xemu_call")

    # The Lightrec interpreter is permitted; `fallback.calls` at run time measures its use.
    live = ("lightrec_run_interpreter", "lightrec_emit_jump_to_interpreter")
    linked_live = [name for name in live if name in symbols]
    corpus = [name for name in corpus_candidates if name in symbols]

    for name in linked_retired:
        print(f"[verify] REFUSED: the product links the RETIRED interpreter symbol '{name}'",
              file=sys.stderr)
    for name in corpus:
        print(f"[verify] REFUSED: the product links the retired generated-corpus symbol '{name}'",
              file=sys.stderr)
    if linked_retired or corpus:
        return False

    print(f"[verify] product link: 0 of {len(retired)} retired-interpreter entry points present; "
          f"0 of {len(corpus_candidates)} generated-corpus symbols present")
    if linked_live:
        print(f"[verify] product link: {len(linked_live)} of {len(live)} Lightrec per-block interpreter "
              f"entry points ARE linked ({', '.join(linked_live)}). That is PERMITTED — the "
              f"architecture keeps them for bounded, accounted fallback. It is NOT a measurement of "
              f"whether this title used one: that number is `fallback.calls` at run time.")
    else:
        print(f"[verify] product link: 0 of {len(live)} Lightrec per-block interpreter entry points "
              f"present, which no product should be — report it.")
        return False
    return True


def verify_python() -> bool:
    findings = check_repository(ROOT)
    for finding in findings:
        print(finding.render())
    suite = unittest.defaultTestLoader.discover(ROOT / "tests", pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return not findings and result.wasSuccessful()


def main() -> int:
    framework = resolve_framework()
    if framework is None:
        return 1
    native_ok = verify_native(framework)
    style_ok = False
    if native_ok:
        style_ok = run(
            sys.executable,
            framework / "tools" / "check_cpp_style.py",
            "--root", ROOT,
            "--compile-commands", BUILD,
        ).returncode == 0
    python_ok = verify_python()
    if native_ok and style_ok and python_ok:
        print("[verify] PASS: native contracts, C++ policy, product link, Python tests, and structure")
        return 0
    print("[verify] FAIL: one or more required checks failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

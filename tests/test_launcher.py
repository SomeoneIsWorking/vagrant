#!/usr/bin/env python3
"""Hermetic positive and refusal checks for the shipping launcher."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import run as launcher
from tools.resolve_disc import resolve


class FakeHost(launcher.Host):
    def __init__(
        self,
        *,
        missing: set[str] | None = None,
        missing_module: str | None = None,
        broken_compiler: str | None = None,
        system: str = "Linux",
        distribution: str = "fedora",
    ) -> None:
        self.missing = missing or set()
        self.missing_module = missing_module
        self.broken_compiler = broken_compiler
        self.system_name = system
        self.distribution = distribution
        self.commands: list[list[str]] = []

    def which(self, name: str) -> str | None:
        if name in self.missing or Path(name).name in self.missing:
            return None
        return f"/fake/{Path(name).name}"

    def system(self) -> str:
        return self.system_name

    def linux_distribution(self) -> str:
        return self.distribution

    def run(self, args, **_kwargs):
        command = [str(value) for value in args]
        self.commands.append(command)
        failed = (
            command[:2] == ["pkg-config", "--exists"]
            and command[-1] == self.missing_module
        ) or (
            "-fsyntax-only" in command and Path(command[0]).name == self.broken_compiler
        )
        return subprocess.CompletedProcess(command, 1 if failed else 0, "", "")


class LauncherTest(unittest.TestCase):
    def test_no_argument_route_builds_and_launches_current_target(self):
        events = []
        psxport = ROOT / "external/psxport"
        discdump = ROOT / "scratch/build/discdump-player/toolchain/tools/discdump"

        launcher.execute(
            None,
            preflight_step=lambda: events.append("preflight") or ("cc", "c++"),
            sync_step=lambda: events.append("sync") or psxport,
            reference_step=lambda: events.append("reference"),
            discdump_step=lambda px, cc, cxx: (
                events.append(("discdump", px, cc, cxx)) or discdump
            ),
            provision_step=lambda disc, px, dd: events.append(
                ("provision", disc, px, dd)
            ),
            build_step=lambda px, cc, cxx: events.append(("build", px, cc, cxx)),
            launch_step=lambda px: events.append(("launch", px, launcher.PORT)),
        )

        self.assertEqual(events[0:3], ["preflight", "sync", "reference"])
        self.assertEqual(events[4], ("provision", None, psxport, discdump))
        self.assertEqual(events[-2][0], "build")
        self.assertEqual(
            events[-1], ("launch", psxport, ROOT / "scratch/bin/vagrant_port")
        )

    def test_prepare_only_runs_the_product_build_without_launching(self):
        events = []
        launcher.execute(
            None,
            prepare_only=True,
            preflight_step=lambda: ("cc", "c++"),
            sync_step=lambda: Path("external/psxport"),
            reference_step=lambda: None,
            discdump_step=lambda *_args: Path("discdump"),
            provision_step=lambda *_args: events.append("provision"),
            build_step=lambda *_args: events.append("build"),
            launch_step=lambda *_args: events.append("launch"),
        )
        self.assertEqual(events, ["provision", "build"])

    def test_explicit_missing_disc_refuses_before_any_fallback(self):
        missing = ROOT / "scratch/launcher-test/no-such-disc.chd"
        with self.assertRaises(SystemExit) as refused:
            resolve(str(missing))
        self.assertEqual(refused.exception.code, 2)

    def test_refusal_stops_before_build_and_launch(self):
        events = []

        def refuse():
            events.append("refused")
            raise launcher.Refusal("test refusal")

        with self.assertRaises(launcher.Refusal):
            launcher.execute(
                None,
                preflight_step=refuse,
                sync_step=lambda: events.append("sync"),
                launch_step=lambda _px: events.append("launch"),
            )
        self.assertEqual(events, ["refused"])

    def test_launch_opens_the_window_and_never_self_destructs(self):
        # A play launch opens the game window and disables the frame-progress abort: the
        # watchdog is an agent-run diagnostic (2026-08-25) — the intro movie stalls on the
        # unimplemented XA/STR streaming frontier and a 3-second abort killed real sessions.
        psxport = ROOT / "external/psxport"
        with (
            mock.patch.dict(launcher.os.environ, {}, clear=True),
            mock.patch.object(launcher.os, "execve") as execve,
        ):
            launcher.launch(psxport)
        environment = execve.call_args.args[2]
        self.assertEqual(environment["PSXPORT_VK_WINDOW"], "1")
        self.assertNotIn("PSXPORT_VK_HEADLESS", environment)
        self.assertEqual(environment["PSXPORT_WATCHDOG"], "15")
        self.assertEqual(environment["PSXPORT_ASSET_DIR"], str(psxport))
        execve.assert_called_once_with(launcher.PORT, [str(launcher.PORT)], environment)

    def test_headless_escape_hatch_restores_agent_launch(self):
        psxport = ROOT / "external/psxport"
        with (
            mock.patch.dict(launcher.os.environ,
                            {"PSXPORT_HEADLESS": "1"}, clear=True),
            mock.patch.object(launcher.os, "execve") as execve,
        ):
            launcher.launch(psxport)
        environment = execve.call_args.args[2]
        self.assertEqual(environment["PSXPORT_VK_HEADLESS"], "1")
        self.assertNotIn("PSXPORT_VK_WINDOW", environment)
        self.assertEqual(environment["PSXPORT_WATCHDOG"], "15")

    def test_compilers_are_accepted_by_capability_without_identity_policy(self):
        host = FakeHost()
        cc, cxx = launcher.preflight(host, {"CC": "custom-c", "CXX": "custom-cxx"})
        self.assertEqual((cc, cxx), ("/fake/custom-c", "/fake/custom-cxx"))
        self.assertTrue(
            any(command[0] == "/fake/custom-c" for command in host.commands)
        )
        self.assertTrue(
            any(command[0] == "/fake/custom-cxx" for command in host.commands)
        )
        self.assertFalse(any("--version" in command for command in host.commands))

    def test_incapable_compiler_gets_an_actionable_dnf_refusal(self):
        host = FakeHost(broken_compiler="custom-cxx")
        with self.assertRaisesRegex(
            launcher.Refusal, "sudo dnf install gcc gcc-c\\+\\+"
        ):
            launcher.preflight(host, {"CC": "custom-c", "CXX": "custom-cxx"})

    def test_missing_native_library_names_platform_package_command(self):
        host = FakeHost(missing_module="sdl3-image", distribution="ubuntu debian")
        with self.assertRaisesRegex(
            launcher.Refusal, "sudo apt install libsdl3-image-dev"
        ):
            launcher.preflight(host)

    def test_missing_tools_name_macos_and_windows_install_commands(self):
        cases = (
            (FakeHost(missing={"cmake"}, system="Darwin"), "brew install cmake"),
            (
                FakeHost(missing={"glslc"}, system="Windows"),
                "winget install KhronosGroup.VulkanSDK",
            ),
        )
        for host, expected in cases:
            with (
                self.subTest(expected=expected),
                self.assertRaisesRegex(launcher.Refusal, expected),
            ):
                launcher.preflight(host)

    def test_player_cmake_configuration_is_test_free_and_uses_locked_python(self):
        command = [
            str(value)
            for value in launcher.cmake_configure_command(
                Path("external/psxport"),
                "/usr/bin/cc",
                "/usr/bin/c++",
                "/locked/python",
            )
        ]
        self.assertIn("-DBUILD_TESTING=OFF", command)
        self.assertIn("-DPython3_EXECUTABLE=/locked/python", command)
        self.assertTrue(str(launcher.BUILD_ROOT) in command[4])
        self.assertFalse(any(Path(value).name == "ctest" for value in command))
        self.assertFalse(any("/tests/" in value for value in command))

    def test_discdump_build_receives_the_locked_interpreter(self):
        psxport = Path("external/psxport")
        with mock.patch.object(
            launcher.discdump, "build", return_value="/fake/discdump"
        ) as build:
            result = launcher.build_discdump(psxport, "/usr/bin/cc", "/usr/bin/c++")
        self.assertEqual(result, Path("/fake/discdump"))
        self.assertEqual(build.call_args.kwargs["python"], sys.executable)
        self.assertTrue(
            str(build.call_args.kwargs["build_dir"]).startswith(
                str(launcher.DISCDUMP_BUILD_ROOT)
            )
        )

    def test_discdump_configuration_is_also_test_free(self):
        command = launcher.discdump.configure_command(
            Path("external/psxport"),
            Path("scratch/build/discdump"),
            "/usr/bin/cc",
            "/usr/bin/c++",
            "/locked/python",
        )
        self.assertIn("-DBUILD_TESTING=OFF", command)
        self.assertIn("-DPSXPORT_BUILD_TESTS=OFF", command)
        self.assertIn("-DPython3_EXECUTABLE=/locked/python", command)
        self.assertFalse(any(Path(value).name == "ctest" for value in command))

    def test_shell_and_locked_project_are_the_stable_entry_contract(self):
        self.assertEqual(
            (ROOT / "run.sh").read_text(),
            '#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\nexec uv run --frozen python bootstrap.py "$@"\n',
        )
        self.assertIn("from tools.run import main", (ROOT / "bootstrap.py").read_text())
        self.assertIn("package = false", (ROOT / "pyproject.toml").read_text())
        self.assertIn("version = 1", (ROOT / "uv.lock").read_text())
        self.assertTrue(os.access(ROOT / "run.sh", os.X_OK))


if __name__ == "__main__":
    unittest.main()

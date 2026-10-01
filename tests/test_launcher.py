#!/usr/bin/env python3
"""Hermetic checks for the player launcher.

The launcher used to refuse a product that did not exist. It no longer does, so the interesting
questions changed shape: does the route BUILD the shipping target (not merely configure), does it
provision before it launches, and does every refusal name a stage rather than a symptom?

Every test injects the process boundary, so none of them builds, provisions, or launches anything.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import run as launcher
from tools.launcher import runtime_boundary as boundary
from tools.quality import structure


class Completed:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


class LauncherRouteTest(unittest.TestCase):
    """The zero-argument route, with the process boundary injected."""

    def run_route(self, *, configure_rc: int = 0, build_rc: int = 0, product_rc: int = 7):
        calls: list[list[str]] = []

        def fake_run(args, **kwargs):
            calls.append([str(part) for part in args])
            joined = " ".join(str(part) for part in args)
            if "cmake" in joined and "--build" not in joined and "-S" in joined:
                return Completed(configure_rc)
            if "--build" in joined:
                return Completed(build_rc)
            if joined.endswith(boundary.PRODUCT_TARGET):
                return Completed(product_rc)
            return Completed(0)

        with (
            mock.patch.object(subprocess, "run", side_effect=fake_run),
            redirect_stdout(StringIO()),
        ):
            code = launcher.main([], environ={"PATH": os.environ.get("PATH", "")})
        return code, calls

    def test_route_provisions_builds_and_launches_the_shipping_target(self) -> None:
        code, calls = self.run_route()
        self.assertEqual(code, 7, "the launcher's exit code must be the product's own")
        joined = [" ".join(call) for call in calls]
        self.assertTrue(
            any("tools/extract_exe.py" in call for call in joined),
            f"the route never provisioned the resident image: {joined}",
        )
        self.assertTrue(
            any("tools/extract_overlays.py" in call for call in joined),
            f"the route never provisioned the overlay images: {joined}",
        )
        self.assertTrue(
            any(f"--target {boundary.PRODUCT_TARGET}" in call for call in joined),
            f"the route never built {boundary.PRODUCT_TARGET}: {joined}",
        )
        self.assertTrue(
            any(call.endswith(boundary.PRODUCT_TARGET) for call in joined),
            f"the route never launched the product: {joined}",
        )

    def test_provision_failure_refuses_before_configuring(self) -> None:
        """The route must not configure, build, or launch on media it could not authenticate. A
        launcher that keeps going after provisioning failed would build a product against absent or
        wrong bytes and report success."""
        with (
            mock.patch.object(boundary.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"),
            mock.patch.object(boundary, "framework_checkout", return_value=ROOT / "external" / "psxport"),
            mock.patch.object(subprocess, "run", return_value=Completed(2)) as run,
            redirect_stdout(StringIO()),
        ):
            code = launcher.main([], environ={})
        self.assertEqual(code, 2)
        joined = [" ".join(str(part) for part in call.args[0]) for call in run.call_args_list]
        self.assertFalse(
            any("-S" in call and "--build" not in call for call in joined),
            f"the route configured after provisioning failed: {joined}",
        )
        self.assertFalse(
            any("--build" in call for call in joined),
            f"the route built after provisioning failed: {joined}",
        )

    def test_build_failure_refuses_before_launching(self) -> None:
        def fake_run(args, **kwargs):
            joined = " ".join(str(part) for part in args)
            if "--build" in joined:
                return Completed(1)
            return Completed(0)

        with (
            mock.patch.object(boundary.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"),
            mock.patch.object(boundary, "framework_checkout", return_value=ROOT / "external" / "psxport"),
            mock.patch.object(subprocess, "run", side_effect=fake_run),
            redirect_stdout(StringIO()),
        ):
            code = launcher.main([], environ={})
        self.assertEqual(code, 2)

    def test_configure_failure_refuses_before_building(self) -> None:
        def fake_run(args, **kwargs):
            joined = " ".join(str(part) for part in args)
            if "-S" in joined and "--build" not in joined:
                return Completed(1)
            return Completed(0)

        with (
            mock.patch.object(boundary.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"),
            mock.patch.object(boundary, "framework_checkout", return_value=ROOT / "external" / "psxport"),
            mock.patch.object(subprocess, "run", side_effect=fake_run),
            redirect_stdout(StringIO()),
        ):
            code = launcher.main([], environ={})
        self.assertEqual(code, 2)

    def test_provisioning_refusal_names_the_stage_and_the_tool(self) -> None:
        """A refusal must name the STAGE and the tool, not only the cause.

        The previous launcher refused with "the adapter to psxport's dynarec-only executor is not
        implemented", which named a boundary and not a step a player could act on. This asserts the
        real provisioning refusal, through the real `provision_inputs`, with only the process
        boundary injected — so it cannot pass by asserting on a message the test itself wrote.
        """
        def fake_run(args, **kwargs):
            joined = " ".join(str(part) for part in args)
            if "extract_exe.py" in joined:
                return Completed(2)
            return Completed(0)

        error = StringIO()
        with (
            mock.patch.object(boundary.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"),
            mock.patch.object(boundary, "framework_checkout", return_value=ROOT / "external" / "psxport"),
            mock.patch.object(subprocess, "run", side_effect=fake_run),
            redirect_stdout(StringIO()),
        ):
            code = launcher.main([], environ={}, stderr=error)
        self.assertEqual(code, 2)
        self.assertIn("provision", error.getvalue())
        self.assertIn("extract_exe.py", error.getvalue())


class LauncherRefusalTest(unittest.TestCase):
    def test_missing_tool_names_the_install_command(self) -> None:
        with mock.patch.object(boundary.shutil, "which", return_value=None), mock.patch.object(
            boundary, "install_command", return_value="sudo dnf install ninja-build"
        ):
            with self.assertRaisesRegex(boundary.ProductUnavailable, "sudo dnf install ninja-build"):
                boundary.require_tool("ninja")

    def test_unmapped_platform_refusal_is_still_actionable(self) -> None:
        with mock.patch.object(boundary.shutil, "which", return_value=None), mock.patch.object(
            boundary, "install_command", return_value=None
        ):
            with self.assertRaisesRegex(boundary.ProductUnavailable, "platform package manager"):
                boundary.require_tool("ninja")

    def test_absent_framework_is_refused_by_name(self) -> None:
        # A checkout that is not a psxport checkout at all. Asserted against a scratch directory
        # rather than a made-up path so the refusal is about the missing marker, not about a
        # nonexistent parent.
        scratch = ROOT / "scratch" / "tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as empty:
            with mock.patch.object(subprocess, "run", return_value=Completed(0)), mock.patch.object(
                boundary, "DEFAULT_FRAMEWORK", Path(empty)
            ):
                with self.assertRaisesRegex(boundary.ProductUnavailable, "cmake/psxport.cmake"):
                    boundary.framework_checkout({}, ROOT)

    def test_explicit_framework_wins_over_the_symlink(self) -> None:
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("the sync tool ran")):
            self.assertEqual(
                boundary.framework_checkout({"PSXPORT_DIR": "/opt/framework"}, Path("/repo")),
                Path("/opt/framework"),
            )

    def test_missing_measured_inputs_are_named(self) -> None:
        with mock.patch.object(boundary, "RESIDENT_IMAGE", Path("scratch/bin/vagrant/ABSENT")), mock.patch.object(
            boundary, "OVERLAY_DIRECTORY", Path("scratch/bin/ABSENT-OVERLAYS")
        ):
            self.assertEqual(
                boundary.missing_inputs(),
                [Path("scratch/bin/vagrant/ABSENT"), Path("scratch/bin/ABSENT-OVERLAYS")],
            )

    def test_present_measured_inputs_report_nothing_missing(self) -> None:
        self.assertEqual(boundary.missing_inputs(), [], "the provisioned measured inputs are absent")

    def test_refuses_when_provisioning_left_an_input_absent(self) -> None:
        with mock.patch.object(boundary.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"), mock.patch.object(
            boundary, "framework_checkout", return_value=ROOT / "external" / "psxport"
        ), mock.patch.object(boundary, "provision_inputs"), mock.patch.object(
            boundary, "missing_inputs", return_value=[boundary.RESIDENT_IMAGE]
        ):
            with self.assertRaisesRegex(boundary.ProductUnavailable, "still absent"):
                boundary.provision_build_and_launch(None, build=Path("build/player"), root=ROOT, environment={}, jobs=1)


class EntryContractTest(unittest.TestCase):
    def test_help_exits_before_provisioning(self) -> None:
        for spelling in ("-h", "--help"):
            with self.subTest(spelling=spelling):
                with mock.patch.object(boundary, "provision_inputs") as provision:
                    with redirect_stdout(StringIO()), self.assertRaises(SystemExit) as result:
                        launcher.main([spelling])
                self.assertEqual(result.exception.code, 0)
                provision.assert_not_called()

    def test_prepare_only_builds_without_launching(self) -> None:
        calls: list[str] = []

        def fake_run(args, **kwargs):
            joined = " ".join(str(part) for part in args)
            calls.append(joined)
            return Completed(0)

        with (
            mock.patch.object(boundary.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"),
            mock.patch.object(boundary, "framework_checkout", return_value=ROOT / "external" / "psxport"),
            mock.patch.object(subprocess, "run", side_effect=fake_run),
            redirect_stdout(StringIO()),
        ):
            self.assertEqual(launcher.main(["--prepare-only"], environ={}), 0)
        self.assertTrue(any(f"--target {boundary.PRODUCT_TARGET}" in call for call in calls), calls)
        self.assertFalse(
            any(call.endswith(f"build/player/{boundary.PRODUCT_TARGET}") for call in calls),
            f"--prepare-only launched the product: {calls}",
        )

    def test_no_retired_selector_is_reachable_from_the_launcher(self) -> None:
        """S002, asserted through the repository's OWN retired-pattern table.

        The pattern list is not restated here. A second list would be a second answer to "what counts
        as the retired product", and it would drift. The gate's `analyze_text` is the owner, and
        `tools/verify.py` runs it over the whole repository.
        """
        for relative in ("tools/run.py", "tools/launcher/runtime_boundary.py"):
            with self.subTest(source=relative):
                findings = structure.analyze_text(
                    relative,
                    (ROOT / relative).read_text(encoding="utf-8"),
                    product_source=True,
                )
                self.assertEqual(
                    [finding.reason for finding in findings],
                    [],
                    f"the launcher names a retired product pattern: {findings}",
                )

    def test_shell_and_locked_project_are_the_stable_entry_contract(self) -> None:
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

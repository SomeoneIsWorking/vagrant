#!/usr/bin/env python3
"""Positive and refusal checks for the shipping launcher orchestration."""

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import run as launcher
from resolve_disc import resolve


class LauncherTest(unittest.TestCase):
    def test_no_argument_route_builds_and_launches_current_target(self):
        events = []
        psxport = ROOT / "external/psxport"
        discdump = ROOT / "scratch/build/psxport/tools/discdump"

        launcher.execute(
            None,
            preflight_step=lambda: events.append("preflight") or ("clang", "clang++"),
            sync_step=lambda: events.append("sync") or psxport,
            reference_step=lambda: events.append("reference"),
            discdump_step=lambda px, cc, cxx: events.append(
                ("discdump", px, cc, cxx)
            )
            or discdump,
            provision_step=lambda disc, px, dd: events.append(("provision", disc, px, dd)),
            build_step=lambda px, cc, cxx: events.append(("build", px, cc, cxx)),
            launch_step=lambda px: events.append(("launch", px, launcher.PORT)),
        )

        self.assertEqual(events[0:3], ["preflight", "sync", "reference"])
        self.assertEqual(events[4], ("provision", None, psxport, discdump))
        self.assertEqual(events[-2][0], "build")
        self.assertEqual(
            events[-1],
            ("launch", psxport, ROOT / "scratch/bin/vagrant_port"),
        )

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

    def test_launch_pins_the_current_bootstrap_to_headless(self):
        psxport = ROOT / "external/psxport"
        with mock.patch.dict(launcher.os.environ, {}, clear=True):
            with mock.patch.object(launcher.os, "execv") as execv:
                launcher.launch(psxport)
            self.assertEqual(launcher.os.environ["PSXPORT_VK_HEADLESS"], "1")
            self.assertEqual(launcher.os.environ["PSXPORT_ASSET_DIR"], str(psxport))
        execv.assert_called_once_with(launcher.PORT, [str(launcher.PORT)])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Hermetic checks for the break-first player boundary."""

from __future__ import annotations

import logging
import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import run as launcher
from tools.launcher.runtime_boundary import ProductUnavailable, require_product


class LauncherTest(unittest.TestCase):
    def test_help_exits_before_product_boundary(self) -> None:
        for spelling in ("-h", "--help"):
            with self.subTest(spelling=spelling):
                output = StringIO()
                with (
                    mock.patch.object(launcher, "require_product") as boundary,
                    redirect_stdout(output),
                    self.assertRaises(SystemExit) as result,
                ):
                    launcher.main([spelling])
                self.assertEqual(result.exception.code, 0)
                self.assertIn("native/dynarec port", output.getvalue())
                boundary.assert_not_called()

    def test_product_refusal_names_the_only_missing_boundary(self) -> None:
        with self.assertRaisesRegex(
            ProductUnavailable, "adapter to psxport's dynarec-only executor"
        ):
            require_product(None)

    def test_default_route_reports_the_boundary_without_discovering_media(self) -> None:
        error = StringIO()
        handler = logging.StreamHandler(error)
        logger = logging.getLogger("vagrant")
        previous_handlers = logger.handlers[:]
        logger.handlers = [handler]
        try:
            self.assertEqual(launcher.main([]), 2)
        finally:
            logger.handlers = previous_handlers
        self.assertIn("generated-source product was removed", error.getvalue())
        self.assertIn("dynarec-only executor", error.getvalue())

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

#!/usr/bin/env python3
"""Focused static verification while the shared dynarec runtime is in flight."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.quality.structure import check_repository


def main() -> int:
    findings = check_repository(ROOT)
    for finding in findings:
        print(finding.render())
    suite = unittest.defaultTestLoader.discover(ROOT / "tests", pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if not findings and result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

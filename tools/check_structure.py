#!/usr/bin/env python3
"""Report structural policy violations with exact paths and lines."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.quality.structure import check_repository


def main() -> int:
    findings = check_repository(ROOT)
    for finding in findings:
        print(finding.render())
    if findings:
        print(f"[structure] {len(findings)} violation(s)")
        return 1
    print("[structure] checked first-party source, generated/static boundaries, diagnostics, and script ownership")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

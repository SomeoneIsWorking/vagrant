#!/usr/bin/env python3
"""Both-answer tests for the shipping structure checker."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.quality.structure import MAX_SOURCE_LINES, analyze_text


class StructureTest(unittest.TestCase):
    def test_clean_product_source_is_accepted(self) -> None:
        self.assertEqual(
            analyze_text(
                "game/render/frame.cpp",
                'lucent::debug("frame", "presented {}", count);\n',
                product_source=True,
            ),
            [],
        )

    def test_retired_dispatch_stderr_and_environment_are_named(self) -> None:
        source = (
            "shard_set_override(address, handler);\n"
            'fprintf(stderr, "bad");\n'
            'const char* value = getenv("MODE");\n'
        )
        findings = analyze_text("game/core/bad.cpp", source, product_source=True)
        self.assertEqual(len(findings), 3)
        self.assertEqual([finding.line for finding in findings], [1, 2, 3])

    def test_line_cap_reports_the_measured_size(self) -> None:
        findings = analyze_text(
            "game/core/monolith.cpp",
            "x\n" * (MAX_SOURCE_LINES + 1),
            product_source=True,
        )
        self.assertEqual(len(findings), 1)
        self.assertIn(str(MAX_SOURCE_LINES + 1), findings[0].reason)

    def test_static_markers_are_rejected_in_automation(self) -> None:
        findings = analyze_text(
            "tools/bad_generator.py",
            'manifest = "recomp_seeds.json"\n',
            product_source=False,
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].reason, "static build input")

    def test_player_python_must_use_the_logging_boundary(self) -> None:
        findings = analyze_text(
            "tools/run.py",
            'print("failed", file=sys.stderr)\n',
            product_source=True,
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].reason, "direct Python stderr")

    def test_test_diagnostic_stderr_is_allowed(self) -> None:
        findings = analyze_text(
            "tests/test_contract.cpp",
            'std::fprintf(stderr, "failed");\n',
            product_source=False,
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()

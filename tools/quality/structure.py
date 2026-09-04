"""Mechanical ownership and retired-static-path checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".py"}
SKIPPED_PARTS = {".git", ".venv", "build", "external", "scratch", "__pycache__"}
MAX_SOURCE_LINES = 1_200

RETIRED_PRODUCT_PATTERNS = {
    "generated-source registry": re.compile(r"recomp_iface\.h|psxport_install_recomp"),
    "generated guest body": re.compile(r"\b(?:gen_func_|ov_[a-z0-9_]+_gen_)"),
    "static override dispatcher": re.compile(r"\bshard_set_override\b|\brec_dispatch\b"),
    "static build input": re.compile(r"rec_sources\.cmake|ensure_recomp|recomp_seeds\.json"),
    "static product selector": re.compile(r"PSXPORT_ENGINE|VAGRANT_HAVE_SUBSTRATE"),
}
DIRECT_DIAGNOSTIC_PATTERNS = {
    "direct stderr": re.compile(r"fprintf\s*\(\s*stderr|std::(?:cerr|clog)"),
    "process environment outside config": re.compile(r"\b(?:std::)?getenv\s*\("),
    "direct Python stderr": re.compile(r"print\s*\([^\n]*file\s*=\s*sys\.stderr"),
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    reason: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.reason}"


def analyze_text(
    path: str,
    text: str,
    *,
    product_source: bool,
    scan_retired: bool = True,
) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    if len(lines) > MAX_SOURCE_LINES:
        findings.append(
            Finding(path, MAX_SOURCE_LINES + 1, f"source has {len(lines)} lines; cap is {MAX_SOURCE_LINES}")
        )
    for line_number, line in enumerate(lines, start=1):
        if scan_retired:
            for reason, pattern in RETIRED_PRODUCT_PATTERNS.items():
                if pattern.search(line):
                    findings.append(Finding(path, line_number, reason))
        if product_source:
            for reason, pattern in DIRECT_DIAGNOSTIC_PATTERNS.items():
                if pattern.search(line):
                    findings.append(Finding(path, line_number, reason))
    return findings


def source_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in SOURCE_SUFFIXES
        and not any(part in SKIPPED_PARTS for part in path.relative_to(root).parts)
    )


def check_repository(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    generated = root / "generated"
    if generated.exists():
        findings.append(Finding("generated", 1, "retired generated guest-code directory exists"))
    for path in source_files(root):
        relative = path.relative_to(root).as_posix()
        product_source = (
            relative.startswith("game/")
            or relative in {"bootstrap.py", "tools/run.py"}
            or relative.startswith("tools/launcher/")
        ) and not relative.startswith("tests/")
        policy_fixture = relative in {"tools/quality/structure.py", "tests/test_structure.py"}
        findings.extend(
            analyze_text(
                relative,
                path.read_text(encoding="utf-8", errors="replace"),
                product_source=product_source,
                scan_retired=not policy_fixture,
            )
        )
    cmake = root / "CMakeLists.txt"
    findings.extend(
        analyze_text(
            "CMakeLists.txt",
            cmake.read_text(encoding="utf-8", errors="replace"),
            product_source=True,
        )
    )
    shell_scripts = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.sh")
        if "external" not in path.relative_to(root).parts and path.name != "run.sh"
    )
    findings.extend(Finding(path, 1, "project automation must be Python") for path in shell_scripts)
    return findings

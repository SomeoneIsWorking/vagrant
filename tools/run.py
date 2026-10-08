#!/usr/bin/env python3
"""Launch the Vagrant Story native/Lightrec product.

Provisions the measured inputs, builds the one shipping executable and launches it; a refusal names the stage.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path("build/player")

sys.path.insert(0, str(ROOT))

from tools.launcher.logging_config import configure_logging
from tools.launcher.runtime_boundary import (
    ProductUnavailable,
    cpu_jobs,
    provision_build_and_launch,
    product_stage_names,
)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch the Vagrant Story native/dynarec port."
    )
    parser.add_argument(
        "disc",
        nargs="?",
        help="Vagrant Story (USA) CHD; otherwise use env/.env/drop-in discovery",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="provision and build the product without launching it",
    )
    return parser.parse_args(list(argv))


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    root: Path = ROOT,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    # Resolved here: a `TextIO = sys.stderr` default would bind the original stream and ignore redirection.
    out: TextIO = sys.stdout if stdout is None else stdout
    err: TextIO = sys.stderr if stderr is None else stderr
    environment = dict(os.environ if environ is None else environ)
    try:
        options = parse_args(sys.argv[1:] if argv is None else argv)
        if options.prepare_only:
            # Everything except the final launch, which opens a window and belongs to the player.
            from tools.launcher.runtime_boundary import (
                build_product,
                configured_build,
                framework_checkout,
                missing_inputs,
                provision_inputs,
            )
            import subprocess

            framework = framework_checkout(environment, root)
            provision_inputs(root, environment, options.disc)
            missing = missing_inputs()
            if missing:
                raise ProductUnavailable(
                    "provisioning finished but these measured inputs are still absent: "
                    + ", ".join(str(path) for path in missing)
                )
            subprocess.run(
                configured_build(BUILD, framework, environment), cwd=root, env=environment, check=False
            )
            build_product(BUILD, environment, cpu_jobs())
            print(f"[run] {', '.join(product_stage_names()[:-1])}: done. Product is built.", file=out)
            return 0
        code = provision_build_and_launch(
            options.disc, build=BUILD, root=root, environment=environment, jobs=cpu_jobs()
        )
    except ProductUnavailable as error:
        print(f"[run] error: {error}", file=err)
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())

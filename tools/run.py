#!/usr/bin/env python3
"""Player entry point during the break-first dynarec migration."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from tools.launcher.logging_config import configure_logging
from tools.launcher.runtime_boundary import ProductUnavailable, require_product


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch the Vagrant Story native/dynarec port."
    )
    parser.add_argument(
        "disc",
        nargs="?",
        help="Vagrant Story (USA) CHD; otherwise use env/.env/drop-in discovery",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    import sys

    args = parse_args(sys.argv[1:] if argv is None else argv)
    logger = configure_logging()
    try:
        require_product(args.disc)
    except ProductUnavailable as error:
        logger.error("%s", error)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

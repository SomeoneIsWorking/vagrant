#!/usr/bin/env python3
"""re_frontier.py — a SHIM. The engine lives in the framework; the DATA lives here.

Run it from the repo root (the engine resolves docs/re-frontier.md against the current working
directory, deliberately — an engine that resolved paths against its own location would read the
FRAMEWORK's roadmap for every game):

    python3 tools/re_frontier.py next

This repo has no copy of the tracker. `re_frontier.py`'s green-over-nothing bug was fixed FOUR times
across THREE diverged copies before the engine was hoisted into psxport/tools/port/ — so a new repo
starts on the shared engine and never grows a fork of it. See external/psxport/tools/port/README.md.
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSXPORT = os.environ.get("PSXPORT_DIR") or os.path.join(ROOT, "external", "psxport")
if not os.path.isabs(PSXPORT):
    PSXPORT = os.path.join(ROOT, PSXPORT)
ENGINE = os.path.join(PSXPORT, "tools", "port", "re_frontier.py")

if not os.path.isfile(ENGINE):
    sys.exit(f"{ENGINE} is missing — run `git submodule update --init external/psxport` "
             f"(or set PSXPORT_DIR). This shim has no fallback ON PURPOSE: a local reimplementation "
             f"is exactly the divergence the hoist removed.")

sys.argv[0] = ENGINE
runpy.run_path(ENGINE, run_name="__main__")

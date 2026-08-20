#!/usr/bin/env python3
"""resolve_disc.py — THE one implementation of "where is this port's disc image?".

Resolution order, highest priority first (the same order every other port in this workspace uses):

  1. a CLI argument                          python3 tools/resolve_disc.py /path/to/disc.chd
  2. $PSXPORT_VAGRANT_DISC                   the per-game env key, also GameConfig::discEnvVar
  3. .env                                    PSXPORT_VAGRANT_DISC= (or the generic PSXPORT_DISC=)
  4. a *.chd dropped in the repo root        the zero-configuration path

Prints the resolved path on stdout and nothing else, so a shell can do DISC="$(python3
tools/resolve_disc.py)". Every diagnostic goes to stderr.

REFUSES rather than returning empty: exit 2 naming all four sources it tried, and exit 2 when a
source names a path that does not exist (which is a configuration error, not "no disc" — silently
falling through to the next source is how a run ends up reading a DIFFERENT disc than the one the
operator configured).

The disc image is never in this repo and never committed. `.env` is gitignored because the path is
machine-specific.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_KEY = "PSXPORT_VAGRANT_DISC"
GENERIC_KEY = "PSXPORT_DISC"


def _from_dotenv(path):
    """Return (value, key) from .env, or (None, None). Does not evaluate the file as shell."""
    if not os.path.isfile(path):
        return None, None
    with open(path, encoding="utf-8", errors="replace") as dotenv:
        txt = dotenv.read()
    for key in (ENV_KEY, GENERIC_KEY):
        m = re.search(r"^[ \t]*" + key + r"[ \t]*=[ \t]*(.+?)[ \t]*$", txt, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('"').strip("'"), key
        # NOTE: no quote-stripping subtleties beyond this — a path with a literal quote in it is
        # rejected below by the existence check rather than silently mangled.
    return None, None


def resolve(argv_path=None, *, verbose=False):
    """Resolve the disc. Returns the path, or raises SystemExit(2) naming what it tried."""
    tried = []

    if argv_path:
        tried.append(("CLI argument", argv_path))
    env = os.environ.get(ENV_KEY) or os.environ.get(GENERIC_KEY)
    if env:
        tried.append((f"${ENV_KEY}", env))
    dot, dotkey = _from_dotenv(os.path.join(ROOT, ".env"))
    if dot:
        tried.append((f".env ({dotkey})", dot))
    drops = sorted(f for f in os.listdir(ROOT) if f.lower().endswith(".chd"))
    for d in drops:
        tried.append(("*.chd in the repo root", os.path.join(ROOT, d)))

    for source, path in tried:
        if os.path.isfile(path):
            if verbose:
                print(f"[disc] {source}: {path}", file=sys.stderr)
            return path
        print(f"[disc] {source} names {path!r} — NO SUCH FILE", file=sys.stderr)
        raise SystemExit(2)

    print(
        "[disc] no disc image. Tried, in order: a CLI argument, "
        f"${ENV_KEY}, .env, and a *.chd in {ROOT}. "
        "Provide the game's own disc image — it is never shipped with this repo.",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    print(resolve(sys.argv[1] if len(sys.argv) > 1 else None, verbose=True))

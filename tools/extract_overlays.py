#!/usr/bin/env python3
"""Provision the exact code overlays consumed by the static recompiler.

The disc names Vagrant Story's modules ``*.PRG`` while psxport's generic emitter
consumes ``*.BIN`` files from one directory.  This tool owns that boundary: it
extracts each explicitly supported module, verifies it against rood-reverse's
SHA-bound matching target, and writes the emitter-facing name under gitignored
``scratch/``.  Adding a module requires adding its disc path and identity here;
the emitter directory is never treated as an open-ended cache.
"""

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import discdump
from resolve_disc import resolve

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "scratch/bin/overlays"


@dataclass(frozen=True)
class Overlay:
    stem: str
    disc_path: str
    reference_config: Path

    @property
    def output(self):
        return OUT_DIR / f"{self.stem}.BIN"


OVERLAYS = (
    Overlay(
        stem="TITLE",
        disc_path="TITLE/TITLE.PRG",
        reference_config=ROOT
        / "external/rood-reverse/config/TITLE/TITLE.PRG/splat.yaml",
    ),
)


class OverlayError(RuntimeError):
    """An overlay input could not be tied to the owned disc bytes."""


def reference_sha1(config):
    if not config.is_file():
        raise OverlayError(f"overlay identity config is absent: {config}")
    for line in config.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha1:"):
            return line.split(":", 1)[1].strip()
    raise OverlayError(f"overlay identity config has no sha1: {config}")


def provision(disc_path=None, *, reader=None):
    disc_path = resolve(disc_path, verbose=True)
    reader = reader or discdump.find()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []

    for overlay in OVERLAYS:
        extracted = discdump.get(disc_path, overlay.disc_path, str(OUT_DIR), dd=reader)
        if not extracted:
            raise OverlayError(f"disc contains no readable {overlay.disc_path}")
        extracted = Path(extracted)
        if extracted != overlay.output:
            extracted.replace(overlay.output)

        data = overlay.output.read_bytes()
        got = hashlib.sha1(data).hexdigest()
        wanted = reference_sha1(overlay.reference_config)
        if got != wanted:
            raise OverlayError(
                f"{overlay.disc_path} sha1 {got} does not match the exact decomp target {wanted}"
            )
        print(
            f"[overlay] {overlay.disc_path} -> {overlay.output.relative_to(ROOT)}  "
            f"{len(data)} bytes  sha1 {got}"
        )
        outputs.append(overlay.output)

    expected = {overlay.output.name for overlay in OVERLAYS}
    unexpected = sorted(
        path.name for path in OUT_DIR.glob("*.BIN") if path.name not in expected
    )
    if unexpected:
        raise OverlayError(
            "emitter input directory contains unowned module(s): "
            + ", ".join(unexpected)
        )
    print(f"[overlay] verified {len(outputs)} of {len(OVERLAYS)} required module(s)")
    return outputs


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1:
        print("usage: extract_overlays.py [/path/to/disc.chd]", file=sys.stderr)
        return 2
    try:
        provision(argv[0] if argv else None)
    except (OSError, OverlayError) as error:
        print(f"[overlay] error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

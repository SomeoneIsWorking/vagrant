#!/usr/bin/env python3
"""Keep Vagrant Story's generated resident and reached overlays aligned with their inputs."""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "scratch/bin/vagrant/SLUS_010.40"
OVERLAY_DIR = ROOT / "scratch/bin/overlays"
OVERLAYS = tuple(
    OVERLAY_DIR / name for name in ("BATTLE.BIN", "INITBTL.BIN", "TITLE.BIN")
)
SEEDS = ROOT / "game/recomp_seeds.json"
GENERATED = ROOT / "generated"
HASH_FILE = GENERATED / ".recomp.hash"
VERSION_FILE = GENERATED / ".recomp_version"


class RecompError(RuntimeError):
    """The substrate cannot be proven current."""


def say(message):
    print(f"[ensure-recomp] {message}", file=sys.stderr)


def recompiler_sources(psxport_dir):
    recomp = psxport_dir / "tools/recomp"
    return [recomp / name for name in ("emit.py", "decode.py", "psexe.py")]


def recomp_version(emit):
    match = re.search(
        r'^RECOMP_VERSION\s*=\s*"([^"]+)"', emit.read_text(), re.MULTILINE
    )
    if not match:
        raise RecompError(f"could not read RECOMP_VERSION from {emit}")
    return match.group(1)


def input_hash(paths):
    digest = hashlib.sha256()
    for path in paths:
        if not path.is_file():
            raise RecompError(f"required recomp input is absent: {path}")
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path(path.name)
        digest.update(str(label).encode())
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def generated_complete():
    manifest = GENERATED / "rec_sources.cmake"
    if not manifest.is_file():
        return False
    listed = re.findall(r"^\s*(\S+\.c)\s*$", manifest.read_text(), re.MULTILINE)
    required = {
        "overlay_table.c",
        "ov_battle_disp.c",
        "ov_initbtl_disp.c",
        "ov_title_disp.c",
    }
    if not required.issubset(listed) or not all(
        (GENERATED / name).is_file() for name in listed
    ):
        return False
    table = (GENERATED / "overlay_table.c").read_text()
    battle_dispatch = (GENERATED / "ov_battle_disp.c").read_text()
    initbtl_dispatch = (GENERATED / "ov_initbtl_disp.c").read_text()
    title_dispatch = (GENERATED / "ov_title_disp.c").read_text()
    return (
        '"BATTLE", ov_battle_dispatch, ov_battle_func_index' in table
        and '"INITBTL", ov_initbtl_dispatch, ov_initbtl_func_index' in table
        and '"TITLE", ov_title_dispatch, ov_title_func_index' in table
        and "const int g_rec_overlay_count = 3;" in table
        and "ov_battle_func_800798A4" in battle_dispatch
        and "ov_initbtl_func_800FA35C" in initbtl_dispatch
        and "ov_title_func_80071334" in title_dispatch
    )


def ensure(psxport_dir):
    sources = recompiler_sources(psxport_dir)
    version = recomp_version(sources[0])
    present = sorted(OVERLAY_DIR.glob("*.BIN")) if OVERLAY_DIR.is_dir() else []
    if present != sorted(OVERLAYS):
        expected = ", ".join(path.name for path in OVERLAYS)
        actual = ", ".join(path.name for path in present) or "none"
        raise RecompError(
            f"overlay input inventory is {actual}; expected exactly {expected}. "
            "Run tools/extract_overlays.py against the owned disc."
        )
    wanted = f"{version}:{input_hash([EXE, *OVERLAYS, SEEDS, *sources])}"
    have = HASH_FILE.read_text().strip() if HASH_FILE.is_file() else ""
    stamp = VERSION_FILE.read_text().strip() if VERSION_FILE.is_file() else ""
    force = os.environ.get("PSXPORT_FORCE_RECOMP", "") not in ("", "0")

    if not force and have == wanted and stamp == version and generated_complete():
        say(f"recomp up to date (version {version}) — nothing to do")
        return

    reason = "forced" if force else "inputs or generated output changed"
    say(f"{reason} — emitting resident + reached-overlay substrate (version {version})")
    GENERATED.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("PSXPORT_SHARDS", "8")
    command = [
        sys.executable,
        str(sources[0]),
        str(EXE),
        str(GENERATED / "recompiled.c"),
        "--seeds",
        str(SEEDS),
        "--overlays",
        str(OVERLAY_DIR),
    ]
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if result.returncode:
        raise RecompError("resident + reached-overlay substrate emission failed")
    if not generated_complete():
        raise RecompError("emitter returned success but generated/ is incomplete")
    actual_stamp = VERSION_FILE.read_text().strip() if VERSION_FILE.is_file() else ""
    if actual_stamp != version:
        raise RecompError(
            f"emitter stamped version {actual_stamp!r}, expected {version!r}"
        )
    HASH_FILE.write_text(wanted + "\n")
    say(f"recomp current (version {version})")


def main():
    psxport = Path(os.environ.get("PSXPORT_DIR", ROOT / "external/psxport")).resolve()
    try:
        ensure(psxport)
    except (OSError, RecompError) as error:
        print(f"[ensure-recomp] error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

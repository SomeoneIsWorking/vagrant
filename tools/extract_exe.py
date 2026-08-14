#!/usr/bin/env python3
"""extract_exe.py — put this game's boot executable in scratch/, from YOUR disc, and check it.

  python3 tools/extract_exe.py [/path/to/disc.chd]

Extracts SLUS_010.40 (the boot target named in SYSTEM.CNF: `BOOT = cdrom:\\SLUS_010.40;1`, measured
2026-08-12) to scratch/bin/vagrant/, prints the PS-EXE header it read out of it, and compares its
SHA-1 against the value the rood-reverse decompilation states for its own target. Nothing extracted
is ever committed — scratch/ is gitignored, and the executable is the copyright holder's.

Extraction and recompilation remain separate operations. RE-02 documents the resident-only emitter
command; RE-03 supplies verified bases for later overlay emission. This tool provisions and verifies
only the copyrighted executable, which stays under gitignored scratch/.
"""
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discdump  # noqa: E402
from resolve_disc import resolve  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_ON_DISC = "SLUS_010.40"
OUT_DIR = os.path.join(ROOT, "scratch", "bin", "vagrant")
# The SHA-1 rood-reverse (CC0) states for its SLUS_010.40 target, read from
# external/rood-reverse/config/SLUS_010.40/splat.yaml at run time rather than copied here — a
# hardcoded copy would silently stop tracking the reference it claims to check.
REF_SPLAT = os.path.join(ROOT, "external", "rood-reverse", "config", "SLUS_010.40", "splat.yaml")


def ref_sha1():
    if not os.path.isfile(REF_SPLAT):
        return None
    for line in open(REF_SPLAT, encoding="utf-8"):
        if line.startswith("sha1:"):
            return line.split(":", 1)[1].strip()
    return None


def psexe_header(data):
    if data[:8] != b"PS-X EXE":
        return None
    f = struct.unpack("<11I", data[0x10:0x10 + 44])
    keys = ["pc0", "gp0", "t_addr", "t_size", "d_addr", "d_size",
            "b_addr", "b_size", "s_addr", "s_size", "sp_gp"]
    return dict(zip(keys, f))


def main():
    disc = resolve(sys.argv[1] if len(sys.argv) > 1 else None, verbose=True)
    dest = discdump.get(disc, EXE_ON_DISC, OUT_DIR)
    if not dest:
        print(f"[exe] {EXE_ON_DISC} was NOT found on {disc} — is this the right disc? "
              "(USA retail: SLUS-01040)", file=sys.stderr)
        return 2
    data = open(dest, "rb").read()
    got = hashlib.sha1(data).hexdigest()
    print(f"[exe] {dest}  {len(data)} bytes  sha1 {got}")

    hdr = psexe_header(data)
    if not hdr:
        print("[exe] NOT a PS-X EXE — the extracted file is not a PSX executable", file=sys.stderr)
        return 2
    print("[exe] PS-EXE header: entry pc0=0x{pc0:08X} text=0x{t_addr:08X}+0x{t_size:X} "
          "sp=0x{s_addr:08X} gp0=0x{gp0:08X}".format(**hdr))

    want = ref_sha1()
    if want is None:
        print("[exe] CANNOT CHECK the hash: external/rood-reverse is not checked out, so this run "
              "verified the file's SHAPE only (PS-X EXE + header) and NOT its identity. "
              "`git submodule update --init external/rood-reverse` to enable the check.")
        return 0
    if got == want:
        print(f"[exe] MATCH rood-reverse's target sha1 {want} — the decomp's symbol addresses are "
              "OUR addresses, with no translation (docs/references.md)")
        return 0
    print(f"[exe] MISMATCH: this disc yields {got}, rood-reverse targets {want}. A different "
          "region/revision. Its addresses do NOT necessarily apply — treat every borrowed address "
          "as unverified until measured against this executable.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

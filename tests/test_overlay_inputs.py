#!/usr/bin/env python3
"""Both-answer checks for the reached-overlay provisioning boundary."""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import extract_overlays


class OverlayInputsTest(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "scratch/tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.disc = self.root / "owned.chd"
        self.disc.write_bytes(b"disc")
        self.payload = b"matching title module"
        self.config = self.root / "splat.yaml"
        self.config.write_text(f"sha1: {hashlib.sha1(self.payload).hexdigest()}\n")
        self.output = self.root / "overlays"
        self.overlay = extract_overlays.Overlay("TITLE", "TITLE/TITLE.PRG", self.config)

    def tearDown(self):
        self.temp.cleanup()

    def fake_get(self, _disc, path, outdir, *, dd):
        self.assertEqual(path, "TITLE/TITLE.PRG")
        self.assertEqual(dd, "reader")
        result = Path(outdir) / "TITLE.PRG"
        result.write_bytes(self.payload)
        return str(result)

    def provision(self):
        with (
            mock.patch.object(extract_overlays, "OUT_DIR", self.output),
            mock.patch.object(extract_overlays, "OVERLAYS", (self.overlay,)),
            mock.patch.object(extract_overlays.discdump, "get", self.fake_get),
        ):
            return extract_overlays.provision(str(self.disc), reader="reader")

    def test_shipping_inventory_contains_every_reached_boot_overlay(self):
        self.assertEqual(
            [overlay.stem for overlay in extract_overlays.OVERLAYS],
            ["BATTLE", "INITBTL", "TITLE"],
        )
        self.assertEqual(
            [overlay.disc_path for overlay in extract_overlays.OVERLAYS],
            ["BATTLE/BATTLE.PRG", "BATTLE/INITBTL.PRG", "TITLE/TITLE.PRG"],
        )

    def test_matching_owned_image_is_renamed_and_accepted(self):
        self.assertEqual(self.provision(), [self.output / "TITLE.BIN"])
        self.assertEqual((self.output / "TITLE.BIN").read_bytes(), self.payload)

    def test_hash_mismatch_is_refused(self):
        self.config.write_text(f"sha1: {hashlib.sha1(b'other').hexdigest()}\n")
        with self.assertRaises(extract_overlays.OverlayError):
            self.provision()

    def test_unowned_runtime_image_is_refused(self):
        self.output.mkdir(parents=True)
        (self.output / "STALE.BIN").write_bytes(b"stale")
        with self.assertRaises(extract_overlays.OverlayError):
            self.provision()

if __name__ == "__main__":
    unittest.main()

"""Ensure S03 comparison cannot run against post-hoc edited evidence inputs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from s03.freeze import FreezeMismatch, verify_freeze


ROOT = Path(__file__).resolve().parents[1]


class FreezeTests(unittest.TestCase):
    def test_repository_inputs_match_precommitted_digests(self) -> None:
        verify_freeze(ROOT)

    def test_changed_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            (root / "frozen").mkdir()
            (root / "frozen/input.txt").write_text("changed", encoding="utf-8")
            (root / "FREEZE.json").write_text(
                json.dumps({"sha256": {"frozen/input.txt": "0" * 64}}), encoding="utf-8"
            )
            with self.assertRaisesRegex(FreezeMismatch, "changed: frozen/input.txt"):
                verify_freeze(root)

    def test_missing_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            (root / "FREEZE.json").write_text(
                json.dumps({"sha256": {"missing.txt": "0" * 64}}), encoding="utf-8"
            )
            with self.assertRaisesRegex(FreezeMismatch, "missing: missing.txt"):
                verify_freeze(root)


if __name__ == "__main__":
    unittest.main()

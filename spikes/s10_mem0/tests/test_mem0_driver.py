from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from s10.harness import run_admission
from s10.mem0_driver import Mem0Driver, probe_raw_retention


@unittest.skipUnless(importlib.util.find_spec("mem0"), "isolated mem0ai runtime is not installed")
class Mem0DriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spike_root = Path(__file__).resolve().parents[1]
        self.manifest = self.spike_root / "fixtures" / "manifest.json"

    def test_01_projection_path_passes_without_raw_retention(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = run_admission(
                manifest_path=self.manifest,
                canonical_root=self.manifest.parent,
                provider_root=root / "provider",
                driver=Mem0Driver(root / "provider"),
            )
        self.assertEqual(result["verdict"], "PROJECTION_PATH_PASS")
        self.assertFalse(result["checks"]["raw_interaction_persisted"])
        self.assertEqual(result["checks"]["network_attempts"], 0)
        self.assertTrue(result["checks"]["rebuild_projection_matches"])
        self.assertEqual(result["checks"]["markers_found_after_reset"], 0)
        self.assertEqual(result["checks"]["unknown_copies"], 0)
        self.assertFalse(result["retention"]["record_delete_removes_all_copies"])
        self.assertEqual(result["retention"]["required_delete_strategy"], "whole_store_rebuild")
        self.assertEqual(result["retention"]["after_fresh_rebuild"]["tombstoned"], {})

    def test_02_inference_path_retains_raw_interaction_and_purge_removes_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = probe_raw_retention(Path(temporary) / "provider")
        self.assertEqual(result["verdict"], "FAIL_RAW_RETENTION")
        self.assertTrue(result["raw_marker_present_before_purge"])
        self.assertFalse(result["raw_marker_present_after_purge"])
        self.assertEqual(result["network_attempts"], 0)


if __name__ == "__main__":
    unittest.main()

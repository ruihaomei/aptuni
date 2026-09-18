"""Filesystem fail-closed gate (with injected negative probes) and v0 -> v1 migration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from s01.fsgate import FsInfo, UnsupportedFilesystemError, check_vault_filesystem, statfs_info
from s01.migrate import load_any
from s01.records import SchemaVersionError

V0_FACT = {
    "id": "knowledge.survival-analysis.cox",
    "type": "knowledge",
    "statement": "Studied Cox proportional hazards models.",
    "evidence_level": "studied",
    "evidence": [{"source": "marginnote_survival_analysis", "node": "mn:survival:cox",
                  "path": ["Survival Analysis", "Cox Model"]}],
    "valid_from": "2026-09-09",
    "valid_until": None,
    "confidence": "high",
    "last_verified": "2026-09-18",
}


class FsGateTests(unittest.TestCase):
    def test_real_baseline_volume_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            info = statfs_info(Path(raw))
            self.assertEqual("apfs", info.fstypename)
            self.assertTrue(info.is_local)
            check_vault_filesystem(Path(raw))

    def test_injected_non_apfs_is_refused(self) -> None:
        with self.assertRaises(UnsupportedFilesystemError):
            check_vault_filesystem(Path("/tmp/x"), statfs=lambda _p: FsInfo("msdos", True))

    def test_injected_non_local_is_refused(self) -> None:
        with self.assertRaises(UnsupportedFilesystemError):
            check_vault_filesystem(Path("/tmp/x"), statfs=lambda _p: FsInfo("apfs", False))

    def test_sync_roots_are_refused(self) -> None:
        home = Path("/Users/example")
        for root in ("Library/Mobile Documents/com~apple~CloudDocs/v",
                     "Library/CloudStorage/GoogleDrive-a/v", "Dropbox/v"):
            with self.subTest(root=root):
                with self.assertRaises(UnsupportedFilesystemError):
                    check_vault_filesystem(home / root, statfs=lambda _p: FsInfo("apfs", True),
                                           home=home)


class MigrationTests(unittest.TestCase):
    def test_v0_fact_migrates_to_valid_v1(self) -> None:
        records = load_any(V0_FACT)
        fact = next(r for r in records if r.record_type == "fact")
        evidence = next(r for r in records if r.record_type == "evidence")
        self.assertEqual(1, fact.schema_version)
        self.assertEqual("studied", fact.predicate)
        self.assertAlmostEqual(0.9, fact.confidence)
        self.assertEqual((evidence.id,), fact.evidence_ids)
        self.assertIn("studied", evidence.signals)
        self.assertEqual(("Survival Analysis", "Cox Model"), evidence.provenance.locator.node_path)

    def test_migration_is_deterministic(self) -> None:
        self.assertEqual(load_any(V0_FACT), load_any(V0_FACT))

    def test_unknown_future_version_fails_with_guidance(self) -> None:
        with self.assertRaises(SchemaVersionError) as ctx:
            load_any({"schema_version": 7, "record_type": "fact"})
        self.assertIn("migration", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()

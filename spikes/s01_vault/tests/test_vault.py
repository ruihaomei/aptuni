"""Vault write protocol: commit/read, conflicts, crash boundaries, recovery, purge/restore."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from s01.records import parse_record
from s01.vault import CRASH_POINTS, ConflictError, Vault
from tests.helpers import golden_raw

SPIKE_ROOT = Path(__file__).resolve().parents[1]


def golden_records() -> list:
    return [parse_record(raw) for raw in golden_raw()]


class VaultTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(dir=os.environ.get("S01_TMP_ROOT"))
        base = Path(self._tmp.name)
        self.vault_dir = base / "vault"
        self.state_dir = base / "state"
        self.vault = Vault.init(self.vault_dir, self.state_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class CommitReadTests(VaultTestCase):
    def test_commit_then_read_returns_exact_records(self) -> None:
        records = golden_records()
        head = self.vault.commit(records, expected_seq=0)
        self.assertEqual(1, head.seq)
        self.assertEqual(records, self.vault.read_all())

    def test_stale_expected_seq_is_a_conflict_and_writes_nothing(self) -> None:
        records = golden_records()
        self.vault.commit(records[:5], expected_seq=0)
        with self.assertRaises(ConflictError):
            self.vault.commit(records[5:], expected_seq=0)
        self.assertEqual(records[:5], self.vault.read_all())

    def test_invariant_violation_rejects_whole_batch(self) -> None:
        records = golden_records()
        memory_only = [r for r in records if r.record_type == "memory"]
        with self.assertRaises(Exception):
            self.vault.commit(memory_only, expected_seq=0)
        self.assertEqual([], self.vault.read_all())
        self.assertEqual(0, self.vault.head().seq)

    def test_segments_are_human_readable_jsonl(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        segment = next((self.vault_dir / "records").glob("seg-*.jsonl"))
        first = json.loads(segment.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual("module_policy", first["record_type"])

    def test_hash_chain_detects_out_of_band_segment_edit(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        segment = next((self.vault_dir / "records").glob("seg-*.jsonl"))
        segment.write_text(segment.read_text(encoding="utf-8").replace("Class rank 2.", "Class rank 1."),
                           encoding="utf-8")
        with self.assertRaises(Exception) as ctx:
            self.vault.read_all()
        self.assertIn("hash", str(ctx.exception).lower())


class CrashBoundaryTests(VaultTestCase):
    """Kill a writer at each durability boundary; the Vault must hold prior or next state."""

    def _crash_commit(self, point: str) -> int:
        code = (
            "import sys, json; from pathlib import Path;"
            "from s01.records import parse_record; from s01.vault import Vault;"
            "from tests.helpers import golden_raw;"
            "v = Vault(Path(sys.argv[1]), Path(sys.argv[2]));"
            "recs = [parse_record(r) for r in golden_raw()][5:];"
            "v.commit(recs, expected_seq=1)"
        )
        env = dict(os.environ, S01_CRASH_AT=point, PYTHONPATH=str(SPIKE_ROOT))
        result = subprocess.run(
            [sys.executable, "-c", code, str(self.vault_dir), str(self.state_dir)],
            env=env, capture_output=True, text=True, cwd=SPIKE_ROOT, check=False,
        )
        return result.returncode

    def test_every_crash_point_leaves_prior_or_next_state(self) -> None:
        records = golden_records()
        for point in CRASH_POINTS:
            with self.subTest(point=point):
                shutil.rmtree(self.vault_dir)
                shutil.rmtree(self.state_dir)
                vault = Vault.init(self.vault_dir, self.state_dir)
                vault.commit(records[:5], expected_seq=0)
                code = self._crash_commit(point)
                self.assertEqual(137, code, f"writer did not crash at {point}")
                after = Vault(self.vault_dir, self.state_dir)
                report = after.recover()
                state = after.read_all()
                self.assertIn(state, (records[:5], records), f"partial state after {point}")
                self.assertEqual([], report.remaining_orphans)
                # the next writer proceeds normally (lock was released by the kernel)
                if state == records[:5]:
                    after.commit(records[5:], expected_seq=1)
                self.assertEqual(records, after.read_all())


class PurgeRestoreTests(VaultTestCase):
    def test_purge_removes_content_and_issues_terminal_receipt(self) -> None:
        records = golden_records()
        self.vault.commit(records, expected_seq=0)
        target = "obs_00000000000000000000000002"
        receipt = self.vault.purge({target}, expected_seq=1)
        self.assertEqual("complete_managed", receipt.terminal_state)
        remaining = {r.id for r in self.vault.read_all()}
        self.assertNotIn(target, remaining)
        raw_text = "".join(p.read_text(encoding="utf-8") for p in (self.vault_dir / "records").glob("*.jsonl"))
        self.assertNotIn("用户要求回答简短", raw_text)

    def test_restore_of_pre_purge_backup_does_not_resurrect(self) -> None:
        records = golden_records()
        self.vault.commit(records, expected_seq=0)
        backup = Path(self._tmp.name) / "backup"
        self.vault.backup_to(backup)
        target = "obs_00000000000000000000000002"
        self.vault.purge({target}, expected_seq=1)
        restored = Vault.restore_from(backup, self.vault_dir, self.state_dir)
        self.assertNotIn(target, {r.id for r in restored.read_all()})
        raw_text = "".join(p.read_text(encoding="utf-8") for p in (self.vault_dir / "records").glob("*.jsonl"))
        self.assertNotIn("用户要求回答简短", raw_text)

    def test_purge_crash_at_every_point_leaves_no_purged_content_after_recover(self) -> None:
        records = golden_records()
        target = "obs_00000000000000000000000002"
        code = (
            "import sys; from pathlib import Path; from s01.vault import Vault;"
            "Vault(Path(sys.argv[1]), Path(sys.argv[2])).purge({sys.argv[3]}, expected_seq=1)"
        )
        for point in CRASH_POINTS:
            with self.subTest(point=point):
                shutil.rmtree(self.vault_dir)
                shutil.rmtree(self.state_dir)
                Vault.init(self.vault_dir, self.state_dir).commit(records, expected_seq=0)
                env = dict(os.environ, S01_CRASH_AT=point, PYTHONPATH=str(SPIKE_ROOT))
                result = subprocess.run([sys.executable, "-c", code, str(self.vault_dir),
                                         str(self.state_dir), target],
                                        env=env, capture_output=True, text=True, cwd=SPIKE_ROOT, check=False)
                self.assertEqual(137, result.returncode, result.stderr)
                vault = Vault(self.vault_dir, self.state_dir)
                vault.recover()
                self.assertNotIn(target, {r.id for r in vault.read_all()})
                raw_text = "".join(p.read_text(encoding="utf-8")
                                   for p in self.vault_dir.rglob("*") if p.is_file())
                self.assertNotIn("用户要求回答简短", raw_text, f"purged content survived {point}")

    def test_purge_of_referenced_record_rewrites_links_consistently(self) -> None:
        records = golden_records()
        self.vault.commit(records, expected_seq=0)
        self.vault.purge({"obs_00000000000000000000000002"}, expected_seq=1)
        candidate = next(r for r in self.vault.read_all() if r.id == "cnd_00000000000000000000000001")
        self.assertEqual(("obs_00000000000000000000000001",), candidate.derived_from)


if __name__ == "__main__":
    unittest.main()

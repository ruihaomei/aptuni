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

from aptuni.domain.invariants import InvariantError
from aptuni.domain.records import parse_record
from aptuni.vault.store import CRASH_POINTS, ConflictError, Vault, VaultIntegrityError
from support import golden_raw

REPO = Path(__file__).resolve().parents[2]
SUBPROCESS_PATH = os.pathsep.join([str(REPO / "src"), str(REPO / "tests")])


def golden_records() -> list:
    return [parse_record(raw) for raw in golden_raw()]


class VaultTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
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
        with self.assertRaises(InvariantError):
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
            "import os, sys; from pathlib import Path;"
            "from aptuni.domain.records import parse_record; from aptuni.vault.store import Vault;"
            "from support import golden_raw;"
            "v = Vault(Path(sys.argv[1]), Path(sys.argv[2]));"
            "v.crash_hook = lambda name: os._exit(137) if name == sys.argv[3] else None;"
            "recs = [parse_record(r) for r in golden_raw()][5:];"
            "v.commit(recs, expected_seq=1)"
        )
        env = dict(os.environ, PYTHONPATH=SUBPROCESS_PATH)
        result = subprocess.run(
            [sys.executable, "-c", code, str(self.vault_dir), str(self.state_dir), point],
            env=env, capture_output=True, text=True, check=False,
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

    def test_purge_crash_at_every_point_leaves_no_purged_content_after_recover(self) -> None:
        records = golden_records()
        target = "obs_00000000000000000000000002"
        code = (
            "import os, sys; from pathlib import Path; from aptuni.vault.store import Vault;"
            "v = Vault(Path(sys.argv[1]), Path(sys.argv[2]));"
            "v.crash_hook = lambda name: os._exit(137) if name == sys.argv[4] else None;"
            "v.purge({sys.argv[3]}, expected_seq=1)"
        )
        for point in CRASH_POINTS:
            with self.subTest(point=point):
                shutil.rmtree(self.vault_dir)
                shutil.rmtree(self.state_dir)
                Vault.init(self.vault_dir, self.state_dir).commit(records, expected_seq=0)
                env = dict(os.environ, PYTHONPATH=SUBPROCESS_PATH)
                result = subprocess.run([sys.executable, "-c", code, str(self.vault_dir),
                                         str(self.state_dir), target, point],
                                        env=env, capture_output=True, text=True, check=False)
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

    def test_purge_keeps_the_rewritten_head_chain_verifiable(self) -> None:
        records = golden_records()
        self.vault.commit(records, expected_seq=0)
        self.vault.purge({"obs_00000000000000000000000002"}, expected_seq=1)
        self.assertTrue(self.vault.verify().ok)
        head = self.vault.head()
        broken = {"format": 1, "seq": head.seq, "segments": list(head.segments), "chain": "f" * 64}
        (self.vault_dir / "HEAD.json").write_text(json.dumps(broken), encoding="utf-8")
        self.assertIn("hash chain does not match", " ".join(self.vault.verify().problems))

    def test_restore_is_atomic_chain_preserving_and_reapplies_deletion_ledger(self) -> None:
        records = golden_records()
        self.vault.commit(records, expected_seq=0)
        backup = Path(self._tmp.name) / "backup"
        shutil.copytree(self.vault_dir, backup)
        target = "obs_00000000000000000000000002"
        self.vault.purge({target}, expected_seq=1)
        live_chain = self.vault.head().chain

        restored = self.vault.restore_from(backup, expected_seq=2)
        self.assertNotIn(target, {record.id for record in restored.read_all()})
        self.assertEqual(live_chain, restored.head().chain_base)
        self.assertTrue(restored.verify().ok)

    def test_invalid_restore_never_changes_the_live_vault(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        before_head = (self.vault_dir / "HEAD.json").read_bytes()
        before_segments = {path.name: path.read_bytes() for path in (self.vault_dir / "records").iterdir()}
        backup = Path(self._tmp.name) / "bad-backup"
        shutil.copytree(self.vault_dir, backup)
        segment = next((backup / "records").glob("seg-*.jsonl"))
        segment.write_text("corrupt\n", encoding="utf-8")

        with self.assertRaises(VaultIntegrityError):
            self.vault.restore_from(backup, expected_seq=1)
        self.assertEqual(before_head, (self.vault_dir / "HEAD.json").read_bytes())
        self.assertEqual(before_segments,
                         {path.name: path.read_bytes() for path in (self.vault_dir / "records").iterdir()})
        self.assertTrue(self.vault.verify().ok)

    def test_restore_rejects_segment_path_traversal(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        backup = Path(self._tmp.name) / "traversal-backup"
        shutil.copytree(self.vault_dir, backup)
        head_path = backup / "HEAD.json"
        head = json.loads(head_path.read_text(encoding="utf-8"))
        head["segments"][0]["name"] = "../../outside.jsonl"
        head_path.write_text(json.dumps(head), encoding="utf-8")
        before = (self.vault_dir / "HEAD.json").read_bytes()
        with self.assertRaises(VaultIntegrityError):
            self.vault.restore_from(backup, expected_seq=1)
        self.assertEqual(before, (self.vault_dir / "HEAD.json").read_bytes())

    def test_restore_source_cleanup_failure_happens_before_head_publication(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        backup = Path(self._tmp.name) / "cleanup-backup"
        shutil.copytree(self.vault_dir, backup)
        before = (self.vault_dir / "HEAD.json").read_bytes()
        original = self.vault._clear_source_state
        self.vault._clear_source_state = lambda: (_ for _ in ()).throw(VaultIntegrityError("injected"))
        try:
            with self.assertRaises(VaultIntegrityError):
                self.vault.restore_from(backup, expected_seq=1)
        finally:
            self.vault._clear_source_state = original
        self.assertEqual(before, (self.vault_dir / "HEAD.json").read_bytes())

    def test_restore_crash_before_journal_preserves_source_state_and_old_head(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        backup = Path(self._tmp.name) / "pre-journal-backup"
        shutil.copytree(self.vault_dir, backup)
        source_state = self.vault_dir / "sources" / "src_00000000000000000000000001.json"
        source_state.parent.mkdir()
        source_state.write_text('{"cursor":"live"}\n', encoding="utf-8")
        before = (self.vault_dir / "HEAD.json").read_bytes()
        self.vault.crash_hook = lambda point: (_ for _ in ()).throw(RuntimeError(point)) \
            if point == "after_segment_tmp" else None

        with self.assertRaisesRegex(RuntimeError, "after_segment_tmp"):
            self.vault.restore_from(backup, expected_seq=1)

        self.assertTrue(source_state.exists())
        self.assertEqual(before, (self.vault_dir / "HEAD.json").read_bytes())
        self.assertFalse((self.state_dir / "restore-intent.json").exists())

    def test_restore_crash_after_journal_is_completed_by_open(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        backup = Path(self._tmp.name) / "journaled-backup"
        shutil.copytree(self.vault_dir, backup)
        source_state = self.vault_dir / "sources" / "src_00000000000000000000000001.json"
        source_state.parent.mkdir()
        source_state.write_text('{"cursor":"live"}\n', encoding="utf-8")
        self.vault.crash_hook = lambda point: (_ for _ in ()).throw(RuntimeError(point)) \
            if point == "after_head_tmp" else None

        with self.assertRaisesRegex(RuntimeError, "after_head_tmp"):
            self.vault.restore_from(backup, expected_seq=1)

        self.assertFalse(source_state.exists())
        self.assertTrue((self.state_dir / "restore-intent.json").exists())
        recovered = Vault.open(self.vault_dir, self.state_dir)
        self.assertEqual(2, recovered.head().seq)
        self.assertFalse((self.state_dir / "restore-intent.json").exists())
        self.assertTrue(recovered.verify().ok)


if __name__ == "__main__":
    unittest.main()


class OpenTests(VaultTestCase):
    def test_open_runs_recovery_before_serving_reads(self) -> None:
        (self.vault_dir / "records" / "seg-000099-deadbeef.jsonl").write_text("{}\n", encoding="utf-8")
        vault = Vault.open(self.vault_dir, self.state_dir)
        self.assertEqual([], vault.read_all())
        self.assertFalse((self.vault_dir / "records" / "seg-000099-deadbeef.jsonl").exists())

    def test_new_records_are_validated_against_the_full_index(self) -> None:
        records = golden_records()
        self.vault.commit(records[:5], expected_seq=0)
        with self.assertRaises(InvariantError):
            self.vault.commit([records[3]], expected_seq=1)  # duplicate id of a committed record

    def test_verify_chain_reports_intact_vault(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        self.assertTrue(self.vault.verify().ok)

    def test_format_one_head_is_read_and_next_commit_upgrades_to_format_two(self) -> None:
        head_path = self.vault_dir / "HEAD.json"
        old = json.loads(head_path.read_text(encoding="utf-8"))
        old["format"] = 1
        old.pop("chain_base", None)
        head_path.write_text(json.dumps(old), encoding="utf-8")
        opened = Vault.open(self.vault_dir, self.state_dir)
        opened.commit(golden_records(), expected_seq=0)
        upgraded = json.loads(head_path.read_text(encoding="utf-8"))
        self.assertEqual(2, upgraded["format"])
        self.assertIn("chain_base", upgraded)
        self.assertTrue(opened.verify().ok)


class LegacyHeadFormatTests(VaultTestCase):
    """Review 31 F2: HEAD format 1 predates ``chain_base``; a purged legacy Vault must still work."""

    def _make_legacy_purged_head(self) -> Path:
        """Rewrite the live HEAD as the exact artifact the pre-``chain_base`` code produced."""
        self.vault.commit(golden_records(), expected_seq=0)
        self.vault.purge({"obs_00000000000000000000000002"}, expected_seq=1)
        head_path = self.vault_dir / "HEAD.json"
        head = json.loads(head_path.read_text(encoding="utf-8"))
        head["format"] = 1
        head.pop("chain_base", None)
        head_path.write_text(json.dumps(head, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        return head_path

    def test_legacy_purged_vault_still_verifies(self) -> None:
        self._make_legacy_purged_head()
        reopened = Vault.open(self.vault_dir, self.state_dir)
        report = reopened.verify()
        self.assertTrue(report.ok, report.problems)

    def test_legacy_purged_backup_can_be_restored(self) -> None:
        self._make_legacy_purged_head()
        backup = Path(self._tmp.name) / "legacy-backup"
        shutil.copytree(self.vault_dir, backup)
        live = Vault.open(self.vault_dir, self.state_dir)
        restored = live.restore_from(backup, expected_seq=live.head().seq)
        self.assertTrue(restored.verify().ok, restored.verify().problems)

    def test_unpurged_legacy_head_is_migrated_to_the_current_format(self) -> None:
        self.vault.commit(golden_records(), expected_seq=0)
        head_path = self.vault_dir / "HEAD.json"
        head = json.loads(head_path.read_text(encoding="utf-8"))
        self.assertEqual(head["chain_base"], head.pop("chain_base"))
        head["format"] = 1
        head_path.write_text(json.dumps(head, sort_keys=True, indent=1) + "\n", encoding="utf-8")

        reopened = Vault.open(self.vault_dir, self.state_dir)
        migrated = json.loads(head_path.read_text(encoding="utf-8"))
        self.assertEqual(migrated["format"], 2)
        self.assertIn("chain_base", migrated)
        self.assertTrue(reopened.verify().ok, reopened.verify().problems)

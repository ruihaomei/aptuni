"""S04 policy boundary tests; host/model text is never approval."""

from __future__ import annotations

import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from s04.policy import PolicyCore, PolicyDenied


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.database = Path(self.tmp.name) / "journal.sqlite3"
        self.core = PolicyCore(self.database)

    def tearDown(self) -> None:
        self.core.close()
        self.tmp.cleanup()

    def test_remote_unknown_strict_local_read_denies(self) -> None:
        with self.assertRaisesRegex(PolicyDenied, "host_model_egress_denied"):
            self.core.read_identity("codex", host_class="remote_unknown", strict_local=True)

    def test_forged_principal_and_confused_deputy_deny(self) -> None:
        action = self.core.request_action("claude", "purge", "module:study")
        with self.assertRaisesRegex(PolicyDenied, "principal_mismatch"):
            self.core.terminal_approve(action.action_id, "codex")

    def test_source_or_mcp_text_cannot_approve(self) -> None:
        action = self.core.request_action("claude", "purge", "module:study")
        for channel in ("mcp", "source", "model", "hook", "worker"):
            with self.subTest(channel=channel), self.assertRaisesRegex(PolicyDenied, "terminal_only"):
                self.core.approve(action.action_id, "claude", channel=channel)

    def test_stale_epoch_digest_mismatch_replay_and_prefix_deny(self) -> None:
        action = self.core.request_action("claude", "purge", "module:study")
        with self.assertRaisesRegex(PolicyDenied, "exact_action_id_required"):
            self.core.terminal_approve(action.action_id[:8], "claude")
        with self.assertRaisesRegex(PolicyDenied, "action_digest_mismatch"):
            self.core.terminal_approve(action.action_id, "claude", expected_digest="0" * 64)
        with self.assertRaisesRegex(PolicyDenied, "scope_mismatch"):
            self.core.terminal_approve(action.action_id, "claude", expected_scope="module:other")
        self.core.bump_epoch()
        with self.assertRaisesRegex(PolicyDenied, "stale_policy_epoch"):
            self.core.terminal_approve(action.action_id, "claude")

        fresh = self.core.request_action("claude", "purge", "module:study")
        receipt = self.core.terminal_approve(fresh.action_id, "claude")
        self.assertEqual("pending", receipt.state)
        with self.assertRaisesRegex(PolicyDenied, "already_consumed"):
            self.core.terminal_approve(fresh.action_id, "claude")

    def test_concurrent_confirmation_creates_exactly_one_intent(self) -> None:
        action = self.core.request_action("claude", "purge", "module:study")
        outcomes = self.core.race_terminal_approvals(action.action_id, "claude", contenders=8)
        self.assertEqual(1, outcomes.count("approved"))
        self.assertEqual(1, self.core.intent_count(action.action_id))

    def test_revoked_egress_before_worker_cancels_without_effect(self) -> None:
        action = self.core.request_action("claude", "network_export", "module:study")
        self.core.terminal_approve(action.action_id, "claude")
        self.core.revoke_egress()
        self.assertEqual("cancelled_policy", self.core.run_worker(action.action_id))
        self.assertEqual(0, self.core.external_effect_count)

    def test_hard_crash_before_and_after_journal_commit(self) -> None:
        helper = Path(__file__).resolve().parents[1] / "crash_approve.py"
        before = self.core.request_action("claude", "purge", "module:study")
        self.core.close()
        result = subprocess.run(
            [sys.executable, str(helper), str(self.database), before.action_id, "claude", "before_commit"],
            check=False,
        )
        self.assertEqual(91, result.returncode)
        self.core = PolicyCore(self.database)
        self.assertEqual(0, self.core.intent_count(before.action_id))
        self.core.terminal_approve(before.action_id, "claude")

        after = self.core.request_action("claude", "purge", "module:study")
        self.core.close()
        result = subprocess.run(
            [sys.executable, str(helper), str(self.database), after.action_id, "claude", "after_commit"],
            check=False,
        )
        self.assertEqual(92, result.returncode)
        self.core = PolicyCore(self.database)
        self.assertEqual(1, self.core.intent_count(after.action_id))
        with self.assertRaisesRegex(PolicyDenied, "already_consumed"):
            self.core.terminal_approve(after.action_id, "claude")

    def test_effect_success_before_receipt_update_is_idempotent_on_restart(self) -> None:
        action = self.core.request_action("claude", "purge", "module:study")
        self.core.terminal_approve(action.action_id, "claude")
        with self.assertRaisesRegex(RuntimeError, "injected_crash_after_effect"):
            self.core.run_worker(action.action_id, crash_after_effect=True)
        self.assertEqual(1, self.core.external_effect_count)
        self.core.close()
        self.core = PolicyCore(self.database)
        self.assertEqual("complete", self.core.run_worker(action.action_id))
        self.assertEqual(1, self.core.external_effect_count)

    def test_candidate_never_auto_promotes(self) -> None:
        candidate = self.core.observe("synthetic statement", "idem-1")
        self.assertEqual("quarantined", candidate["review_state"])
        self.assertFalse(candidate["exposable"])
        self.assertEqual(candidate, self.core.observe("synthetic statement", "idem-1"))


if __name__ == "__main__":
    unittest.main()

"""A research run must freeze inputs and keep raw data out of the repository."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "agent_e2e_run", Path(__file__).parents[2] / "tools" / "agent_e2e_run.py",
)


class RunBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(cls.tool)

    def setUp(self):
        # Hermetic: CI runners have no Codex/Claude CLI, so stub only the host version probe.
        probe = patch.object(self.tool.subprocess, "check_output", return_value="host-cli 0.0.0-test\n")
        probe.start()
        self.addCleanup(probe.stop)

    def test_digest_mismatch_fails_before_host_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "tasks.json"
            dataset.write_text(json.dumps([["r01", "generic", False, "PRIVATE_TASK"]]))
            bundle = root / "bundle"
            bundle.mkdir()
            spec = {"host": "codex", "model": "test-model", "dataset": str(dataset),
                    "dataset_sha256": "wrong", "bundle": str(bundle), "output_dir": str(root / "out")}
            with self.assertRaisesRegex(ValueError, "digest"):
                self.tool.prepare(spec)
            self.assertFalse((root / "out").exists())

    def test_raw_outputs_cannot_be_written_under_repo(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            self.tool.private_directory(Path(__file__).parents[2] / "ignored-scratch")

    def test_research_fixture_or_server_change_rejects_frozen_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            asset = Path(directory) / "mock.py"
            asset.write_text("frozen synthetic server")
            spec = {"research_assets": [{"path": str(asset), "sha256": self.tool.digest(asset)}]}
            self.assertEqual(self.tool.verify_assets(spec), spec["research_assets"])
            asset.write_text("changed server")
            with self.assertRaisesRegex(ValueError, "research asset"):
                self.tool.verify_assets(spec)

    def test_requested_activation_is_not_proof_of_enabled_full(self):
        setup = {"events": [{"method": "item/completed", "params": {"item": {
            "type": "mcpToolCall", "tool": "aptuni_activate_context", "status": "completed",
            "arguments": {"intent": "aptuni.full", "scope": "session"},
            "result": {"structuredContent": {"activation": {"session_mode": "off"}}},
        }}}]}
        self.assertFalse(self.tool.activated(setup, "codex"))

    def test_setup_disclosure_and_later_disable_are_rejected(self):
        activation = {"method": "item/completed", "params": {"item": {
            "type": "mcpToolCall", "tool": "aptuni_activate_context", "status": "completed",
            "arguments": {"intent": "aptuni.full", "scope": "session"},
            "result": {"structuredContent": {"activation": {"session_mode": "full"},
                "context": {"items": [{"kind": "evidence", "canonical_id": "PRIVATE"}]}}},
        }}}
        self.assertFalse(self.tool.activated({"events": [activation], "result": {"status": "completed"}}, "codex"))
        activation["params"]["item"]["result"]["structuredContent"]["context"]["items"] = []
        disable = {"method": "item/completed", "params": {"item": {
            "type": "mcpToolCall", "tool": "aptuni_activation_disable",
            "result": {"structuredContent": {"mode": "off"}},
        }}}
        self.assertFalse(self.tool.activated({"events": [activation, disable],
                                              "result": {"status": "completed"}}, "codex"))

    def test_expired_turn_preserves_partial_events_as_failure(self):
        session = self.tool.Session.__new__(self.tool.Session)
        session.spec = {"host": "claude", "timeout_s": 1}
        session.send = Mock()
        session.next = Mock(return_value={"message": {"content": [{"type": "tool_use", "id": "unfinished",
                          "name": "mcp__aptuni__aptuni_search_context", "input": {"concepts": ["topic"]}}]}})
        with patch.object(self.tool.time, "monotonic", side_effect=[0, 0, 2, 2]):
            turn = session.turn("ordinary prompt")
        self.assertTrue(turn["result"]["is_error"])
        self.assertEqual(len(turn["events"]), 1)
        self.assertEqual(session.next.call_count, 1)

    def test_initialization_failure_terminates_spawned_host(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = MagicMock()
            child.stdout = []
            with patch.object(self.tool, "codex_config", return_value={}), \
                 patch.object(self.tool.subprocess, "Popen", return_value=child), \
                 patch.object(self.tool.Session, "rpc", side_effect=RuntimeError("startup failed")), \
                 self.assertRaisesRegex(RuntimeError, "startup"):
                self.tool.Session({"host": "codex", "bundle": str(root), "model": "test"}, root / "run", root)
            child.terminate.assert_called_once()
            child.wait.assert_called()

    def test_host_exit_preserves_partial_retrieval(self):
        session = self.tool.Session.__new__(self.tool.Session)
        session.spec = {"host": "claude", "timeout_s": 60}
        session.send = Mock()
        event = {"message": {"content": [{"type": "tool_use", "id": "partial",
                    "name": "mcp__aptuni__aptuni_search_context", "input": {"concepts": ["topic"]}}]}}
        session.next = Mock(side_effect=[event, RuntimeError("host exited")])
        turn = session.turn("ordinary prompt")
        self.assertTrue(turn["result"]["is_error"])
        self.assertEqual(turn["events"], [event])
        self.assertIn("host exited", turn["operational_error"])

    def test_extra_aptuni_tool_or_resource_rejects_catalog(self):
        server = {"name": "aptuni", "tools": dict.fromkeys(self.tool.TOOLS)}
        self.assertTrue(self.tool.catalog_is_confined({"data": [server]}))
        server["tools"]["aptuni_propose_memory"] = {}
        self.assertFalse(self.tool.catalog_is_confined({"data": [server]}))
        del server["tools"]["aptuni_propose_memory"]
        server["resources"] = ["PRIVATE_RESOURCE"]
        self.assertFalse(self.tool.catalog_is_confined({"data": [server]}))

    def test_freeze_manifest_has_no_task_text_and_exact_policy_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "tasks.json"
            dataset.write_text(json.dumps([["r01", "generic", False, "PRIVATE_TASK"]]))
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "AGENTS.md").write_text("current skill")
            policy = root / "policy.txt"
            policy.write_text("frozen policy")
            spec = {"host": "codex", "model": "test-model", "effort": "low", "dataset": str(dataset),
                    "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
                    "bundle": str(bundle), "policy": str(policy), "output_dir": str(root / "out")}
            tasks, manifest = self.tool.prepare(spec)
            self.assertEqual(tasks[0][3], "PRIVATE_TASK")
            self.assertNotIn("PRIVATE_TASK", str(manifest))
            self.assertEqual(manifest["policy_sha256"], hashlib.sha256(policy.read_bytes()).hexdigest())
            self.assertEqual(manifest["task_count"], 1)

    def test_policy_cannot_forbid_explicit_full_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "tasks.json"
            dataset.write_text(json.dumps([["s01", "selection", True, "PRIVATE_TASK"]]))
            bundle = root / "bundle"
            bundle.mkdir()
            policy = root / "policy.txt"
            policy.write_text("Do not alter activation or grants.")
            spec = {"host": "codex", "model": "test-model", "dataset": str(dataset),
                    "dataset_sha256": self.tool.digest(dataset), "bundle": str(bundle),
                    "policy": str(policy), "output_dir": str(root / "out")}
            with self.assertRaisesRegex(ValueError, "explicit Full setup"):
                self.tool.prepare(spec)
            policy.write_text("After explicit Full setup, keep the active session and do not change grants.")
            self.assertEqual(self.tool.prepare(spec)[1]["task_count"], 1)


if __name__ == "__main__":
    unittest.main()

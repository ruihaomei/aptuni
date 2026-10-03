"""Research accounting must not expose content or turn failed journeys into passes."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "agent_e2e", Path(__file__).parents[2] / "tools" / "agent_e2e.py",
)


class AccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert SPEC is not None and SPEC.loader is not None
        cls.tool = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(cls.tool)

    def test_claude_matches_refusals_by_id_and_excludes_setup(self) -> None:
        record = {
            "setup": {"result": {"usage": {"output_tokens": 7}}},
            "task": {
                "elapsed_s": 2.5,
                "events": [
                    {"message": {"content": [
                        {"type": "tool_use", "id": "one", "name": "mcp__aptuni__aptuni_search_context",
                         "input": {"concepts": ["PRIVATE_SENTINEL"], "modules": ["knowledge"]}},
                        {"type": "tool_use", "id": "two", "name": "mcp__aptuni__aptuni_search_context",
                         "input": {"concepts": ["方法"], "modules": ["knowledge"]}},
                    ]}},
                    {"message": {"content": [
                        {"type": "tool_result", "tool_use_id": "two", "content": "{\"items\": []}"},
                        {"type": "tool_result", "tool_use_id": "one", "is_error": True,
                         "content": "Error executing tool: mcp_module_denied"},
                    ]}},
                ],
                "result": {"is_error": False, "result": "PRIVATE_ANSWER", "usage": {
                    "input_tokens": 2, "cache_creation_input_tokens": 3,
                    "cache_read_input_tokens": 4, "output_tokens": 5,
                }},
            },
        }
        result = self.tool.summarize_record(record, "claude")
        self.assertEqual((result["retrieval_calls"], result["refused_calls"], result["extra_calls"]), (2, 1, 1))
        self.assertEqual(result["tokens"]["output"], 5)
        self.assertEqual(result["latency_s"], 2.5)
        self.assertNotIn("PRIVATE", str(result))

    def test_codex_uses_cumulative_difference_not_last_call(self) -> None:
        def usage(total: int, output: int) -> dict:
            return {"method": "thread/tokenUsage/updated", "params": {"tokenUsage": {
                "total": {"inputTokens": total, "outputTokens": output, "cachedInputTokens": total // 2},
                "last": {"inputTokens": 1, "outputTokens": 1},
            }}}
        call = {"id": "call", "type": "mcpToolCall", "tool": "aptuni_search_context",
                "arguments": {"concepts": ["PRIVATE_TOPIC"]}, "status": "completed",
                "result": {"structuredContent": {"items": []}}}
        record = {"setup": {"events": [usage(100, 10)]}, "task": {
            "elapsed_s": 3.0, "events": [usage(300, 30),
                {"method": "item/completed", "params": {"item": call}},
                {"method": "item/completed", "params": {"item": call}},
            ], "result": {"status": "completed", "items": []},
        }}
        result = self.tool.summarize_record(record, "codex")
        self.assertEqual(result["tokens"]["input_total"], 200)
        self.assertEqual(result["tokens"]["output"], 20)
        self.assertEqual(result["retrieval_calls"], 1)
        self.assertNotIn("PRIVATE", str(result))

    def test_unavailable_answer_is_a_failed_journey_and_usage_is_unknown(self) -> None:
        record = {"task": {"events": [], "result": {"is_error": True, "result": "capacity"}}}
        result = self.tool.summarize_record(record, "claude")
        self.assertFalse(result["host_completed"])
        self.assertIsNone(result["tokens"])
        self.assertIsNone(result["latency_s"])

    def test_started_but_unreturned_codex_retrieval_is_counted(self):
        record = {"task": {"result": {"status": "failed"}, "events": [
            {"method": "item/started", "params": {"item": {
                "id": "unfinished", "type": "mcpToolCall", "tool": "aptuni_search_context",
                "arguments": {"concepts": ["PRIVATE_TOPIC"]}, "status": "inProgress",
            }}},
        ]}}
        result = self.tool.summarize_record(record, "codex")
        self.assertEqual(result["retrieval_calls"], 1)
        self.assertEqual(result["unreturned_calls"], 1)
        self.assertFalse(result["host_completed"])

    def test_dataset_accounting_rejects_wrong_host_and_mixed_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "tasks.json"
            dataset.write_text(json.dumps([["r01", "generic", False, "PRIVATE_TASK"]]))
            digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
            (root / "manifest.json").write_text(json.dumps({"dataset_sha256": digest, "host": "codex"}))
            with self.assertRaisesRegex(ValueError, "manifest"):
                self.tool.summarize_dataset(dataset, digest, root, "claude")
            (root / "r01.json").write_text(json.dumps({"id": "r02", "task": {}}))
            with self.assertRaisesRegex(ValueError, "identity"):
                self.tool.summarize_dataset(dataset, digest, root, "codex")


if __name__ == "__main__":
    unittest.main()

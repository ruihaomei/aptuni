"""S04 MCP schema, budget, quarantine, and real-STDIO contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

from s04.server import create_server


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.py"
SANDBOX = "/usr/bin/sandbox-exec"
NO_NETWORK = "(version 1)(deny network*)(allow default)"


class ServerContractTests(unittest.TestCase):
    def test_schema_snapshot(self) -> None:
        async def collect() -> list[dict[str, object]]:
            return [tool.model_dump(mode="json", exclude_none=True)
                    for tool in await create_server().list_tools()]

        actual = anyio.run(collect)
        expected = json.loads((ROOT / "snapshots/tools.json").read_text(encoding="utf-8"))
        self.assertEqual(expected, actual)
        self.assertNotIn("approve", " ".join(tool["name"] for tool in actual))
        serialized = json.dumps(actual)
        for forbidden in ("nonce", "confirmation", "approval_token"):
            self.assertNotIn(forbidden, serialized)

    def test_real_stdio_negotiation_and_safe_calls(self) -> None:
        async def exercise() -> None:
            params = StdioServerParameters(
                command=SANDBOX,
                args=["-p", NO_NETWORK, sys.executable, str(SERVER)],
                cwd=str(ROOT),
            )
            async with Client(params) as client:
                self.assertIn(client.protocol_version, ("2026-07-28", "2025-11-25"))
                tools = await client.list_tools()
                self.assertEqual(5, len(tools.tools))
                identity = await client.call_tool("profile_get_identity_card", {"max_units": 80})
                self.assertFalse(identity.is_error)
                self.assertLessEqual(identity.structured_content["budget"]["used_units"], 80)
                resources = await client.list_resources()
                prompts = await client.list_prompts()
                self.assertEqual([], resources.resources)
                self.assertEqual([], prompts.prompts)
                disabled = await client.call_tool(
                    "profile_search_context", {"query": "x", "module": "disabled"}
                )
                self.assertTrue(disabled.is_error)
                invalid = await client.call_tool("profile_get_evidence", {"fact_id": "../secret"})
                self.assertTrue(invalid.is_error)
                observed = await client.call_tool(
                    "profile_observe_candidate",
                    {"statement": "Synthetic user prefers concise answers.",
                     "provenance_id": "synthetic:host-test", "idempotency_key": "host-test-1"},
                )
                self.assertEqual("quarantined", observed.structured_content["review_state"])
                self.assertFalse(observed.structured_content["exposable"])

        anyio.run(exercise)

    def test_server_shutdown_after_eof(self) -> None:
        process = subprocess.Popen(
            [sys.executable, str(SERVER)], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        assert process.stdin is not None
        process.stdin.close()
        process.wait(timeout=5)
        assert process.stdout is not None
        assert process.stderr is not None
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        process.stdout.close()
        process.stderr.close()
        self.assertEqual(b"", stdout)
        self.assertEqual(0, process.returncode, stderr.decode())

    def test_macos_profile_denies_socket_creation(self) -> None:
        result = subprocess.run(
            [SANDBOX, "-p", NO_NETWORK, sys.executable, str(SERVER), "--network-canary"],
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn(b"S04 server network socket creation denied", result.stderr)


if __name__ == "__main__":
    unittest.main()

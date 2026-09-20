"""Sanitization and evidence contracts for the manual S12 real-host runner."""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNNER: dict[str, Any] = runpy.run_path(str(ROOT / "spikes" / "s12_hosts" / "run_daily_task.py"))


def test_minimal_environment_preserves_keychain_lookup_without_credential_values(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("USER", "synthetic-user")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "secret-oauth")

    environment = RUNNER["minimal_environment"](Path("/synthetic/state"))

    assert environment["USER"] == "synthetic-user"
    assert environment["APTUNI_STATE_DIR"] == "/synthetic/state"
    assert "ANTHROPIC_API_KEY" not in environment
    assert "OPENAI_API_KEY" not in environment
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in environment


def test_prompt_uses_portable_tool_names_and_does_not_reveal_expected_evidence() -> None:
    value = RUNNER["prompt"]()

    assert "aptuni_get_identity_card" in value
    assert "aptuni_search_context" in value
    assert "mcp__aptuni__" not in value
    assert RUNNER["HANDOFF_MARKER"] not in value
    assert RUNNER["DENIED_CODE"] not in value


def test_codex_evidence_requires_completed_mcp_items_not_agent_prose() -> None:
    marker = RUNNER["HANDOFF_MARKER"]
    denied = RUNNER["DENIED_CODE"]
    prose = json.dumps({
        "type": "item.completed",
        "item": {
            "type": "agent_message",
            "text": f"aptuni_get_identity_card {marker} aptuni_search_context {denied}",
        },
    })
    identity = json.dumps({
        "type": "item.completed",
        "item": {"type": "mcp_tool_call", "tool": "aptuni_get_identity_card", "result": marker},
    })
    search = json.dumps({
        "type": "item.completed",
        "item": {"type": "mcp_tool_call", "tool": "aptuni_search_context", "error": denied},
    })

    assert RUNNER["codex_mcp_evidence"](prose) == (False, False, False, False)
    assert RUNNER["codex_mcp_evidence"]("\n".join((identity, search))) == (True, True, True, True)

"""Sanitization and evidence contracts for the manual S12 real-host runner."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
S12_ROOT = ROOT / "spikes" / "s12_hosts"
sys.path.insert(0, str(S12_ROOT))
RUNNER: dict[str, Any] = runpy.run_path(str(S12_ROOT / "run_daily_task.py"))
CONFINEMENT: dict[str, Any] = runpy.run_path(
    str(S12_ROOT / "run_claude_confinement.py")
)


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


def test_runtime_classification_rejects_project_interpreter(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    venv = project / ".venv"
    venv.mkdir()
    package = venv / "site-packages" / "aptuni"
    package.mkdir(parents=True)
    command = venv / "bin" / "python"
    command.parent.mkdir()
    command.touch()

    value = RUNNER["classify_runtime_paths"](command, package, project)

    assert value == {
        "interpreter_outside_project": False,
        "package_outside_project": False,
        "project_venv_used": True,
    }


def test_claude_confinement_settings_cover_file_tools_and_apple_events() -> None:
    protected = Path("/Users/Shared/protected")
    apple = Path("/Users/Shared/apple")
    value = CONFINEMENT["settings"](
        protected, apple, Path("/private/tmp/hook.py"), Path("/private/tmp/result.json")
    )

    assert value["permissions"]["deny"] == [
        "Read(//Users/Shared/protected)",
        "Edit(//Users/Shared/protected)",
    ]
    sandbox = value["sandbox"]
    assert sandbox["allowAppleEvents"] is False
    assert sandbox["allowUnsandboxedCommands"] is False
    assert sandbox["filesystem"]["denyRead"] == [str(protected), str(apple)]
    assert sandbox["filesystem"]["denyWrite"] == [str(protected), str(apple)]
    compile(CONFINEMENT["observer_source"](), "<observer>", "exec")

    read_prompt = CONFINEMENT["read_prompt"](protected)
    write_prompt = CONFINEMENT["write_prompt"](protected)
    apple_prompt = CONFINEMENT["apple_prompt"](apple)
    assert "Write tool" not in read_prompt
    assert "Read tool" not in write_prompt
    assert "osascript" not in read_prompt
    assert "osascript" not in write_prompt
    assert "Read tool" not in apple_prompt


def test_claude_observer_records_only_exact_sanitized_events(tmp_path: Path) -> None:
    script = tmp_path / "observer.py"
    result = tmp_path / "result.json"
    protected = "/Users/Shared/protected"
    apple = "/Users/Shared/apple"
    script.write_text(CONFINEMENT["observer_source"](), encoding="utf-8")

    events = [
        {"hook_event_name": "SessionStart", "session_id": "synthetic"},
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": protected},
        },
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": protected, "content": "private"},
        },
        {
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": f"osascript {apple}"},
            "error": "private error",
        },
    ]
    for event in events:
        subprocess.run(
            [sys.executable, str(script), str(result), protected, apple],
            input=json.dumps(event),
            text=True,
            check=True,
        )

    assert json.loads(result.read_text()) == {
        "apple_failed": True,
        "read_attempted": True,
        "session_id_present": True,
        "write_attempted": True,
    }

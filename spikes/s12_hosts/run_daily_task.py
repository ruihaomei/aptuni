#!/usr/bin/env python3
"""Run one sanitized, grant-bound Aptuni daily task in a frozen real host version."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any

TIMEOUT_SECONDS = 240
HANDOFF_MARKER = "S12_HANDOFF_ALPHA"
DENIED_CODE = "mcp_module_denied"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def minimal_environment(state_dir: Path, codex_home: Path | None = None) -> dict[str, str]:
    """Pass host auth locations and ordinary process settings, but no credential environment."""
    keep = ("HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "SHELL", "TERM", "SSL_CERT_FILE", "USER")
    environment = {key: os.environ[key] for key in keep if key in os.environ}
    environment["APTUNI_STATE_DIR"] = str(state_dir)
    if codex_home is not None:
        environment["CODEX_HOME"] = str(codex_home)
    return environment


def package_command(package: str, version: str, executable: str) -> list[str]:
    return ["npm", "exec", "--yes", f"--package={package}@{version}", "--", executable]


def resolved_version(host: str, version: str) -> str:
    package = "@anthropic-ai/claude-code" if host == "claude" else "@openai/codex"
    executable = "claude" if host == "claude" else "codex"
    completed = subprocess.run(
        [*package_command(package, version, executable), "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=minimal_environment(Path("/nonexistent")),
    )
    return completed.stdout.strip().replace("codex-cli ", "").split()[0]


def classify_runtime_paths(command: Path, package: Path, project_root: Path) -> dict[str, bool]:
    root = project_root.resolve()
    project_venv = (root / ".venv").resolve()
    command = command.resolve()
    package = package.resolve()
    return {
        "interpreter_outside_project": not command.is_relative_to(root),
        "package_outside_project": not package.is_relative_to(root),
        "project_venv_used": command.is_relative_to(project_venv)
        or package.is_relative_to(project_venv),
    }


def runtime_classification(host: str, bundle: Path, project_root: Path) -> dict[str, bool]:
    if host == "claude":
        value = json.loads((bundle / ".mcp.json").read_text(encoding="utf-8"))
        command = Path(value["mcpServers"]["aptuni"]["command"]).resolve()
    else:
        value = tomllib.loads((bundle / "config.toml").read_text(encoding="utf-8"))
        command = Path(value["mcp_servers"]["aptuni"]["command"]).resolve()
    completed = subprocess.run(
        [
            str(command),
            "-I",
            "-c",
            "from pathlib import Path; import aptuni; print(Path(aptuni.__file__).resolve())",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=minimal_environment(Path("/nonexistent")),
    )
    package = Path(completed.stdout.strip()).resolve() if completed.returncode == 0 else project_root
    return {
        "built_wheel_importable": completed.returncode == 0,
        **classify_runtime_paths(command, package, project_root),
    }


def prompt() -> str:
    return (
        "This is a bounded Aptuni handoff check. From the Aptuni MCP server, call the "
        "aptuni_get_identity_card tool exactly once with max_units 700. Copy the marker token "
        "from that result. Then call the aptuni_search_context tool exactly "
        "once with query 'handoff', modules ['preferences'], max_units 128, limit 1, and "
        "include_evidence false. Copy the exact error code from that result. Return only JSON "
        "with keys identity_marker and denied_code. Do not infer or invent either value."
    )


def prepare_codex_home(destination: Path, bundle: Path) -> None:
    destination.mkdir(mode=0o700)
    auth_source = Path.home() / ".codex" / "auth.json"
    auth_target = destination / "auth.json"
    shutil.copy2(auth_source, auth_target)
    auth_target.chmod(0o600)
    shutil.copy2(bundle / "config.toml", destination / "config.toml")


def extract_reply(host: str, stdout: str, last_message: Path) -> str:
    if host == "claude":
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return ""
        return str(payload.get("result", "")) if isinstance(payload, dict) else ""
    if last_message.exists():
        return last_message.read_text(encoding="utf-8")
    return ""


def codex_mcp_evidence(stdout: str) -> tuple[bool, bool, bool, bool]:
    """Read only completed MCP call events; agent prose is not evidence of a tool result."""
    identity_called = False
    search_called = False
    marker_present = False
    denial_present = False
    for line in stdout.splitlines():
        try:
            event: Any = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        serialized = json.dumps(item, sort_keys=True)
        if "aptuni_get_identity_card" in serialized:
            identity_called = True
            marker_present = marker_present or HANDOFF_MARKER in serialized
        if "aptuni_search_context" in serialized:
            search_called = True
            denial_present = denial_present or DENIED_CODE in serialized
    return identity_called, search_called, marker_present, denial_present


def run_host(host: str, version: str, state_dir: Path, bundle: Path) -> dict[str, object]:
    requested_version = version
    actual_version = resolved_version(host, requested_version)
    runtime = runtime_classification(host, bundle, PROJECT_ROOT)
    with tempfile.TemporaryDirectory(prefix=f"aptuni-s12-{host}-") as raw:
        temporary = Path(raw)
        last_message = temporary / "last-message.txt"
        if host == "claude":
            command = [
                *package_command("@anthropic-ai/claude-code", version, "claude"),
                "-p",
                "--no-session-persistence",
                "--setting-sources",
                "",
                "--mcp-config",
                str(bundle / ".mcp.json"),
                "--strict-mcp-config",
                "--permission-mode",
                "dontAsk",
                "--permission-prompts",
                "none",
                "--allowedTools",
                "mcp__aptuni__aptuni_get_identity_card,mcp__aptuni__aptuni_search_context",
                "--disallowedTools",
                "Bash,Read,Edit,Write",
                "--max-budget-usd",
                "0.20",
                "--output-format",
                "json",
                prompt(),
            ]
            environment = minimal_environment(state_dir)
        else:
            codex_home = temporary / "codex-home"
            prepare_codex_home(codex_home, bundle)
            command = [
                *package_command("@openai/codex", version, "codex"),
                "--ask-for-approval",
                "never",
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--json",
                "--output-last-message",
                str(last_message),
                prompt(),
            ]
            environment = minimal_environment(state_dir, codex_home)
        try:
            completed = subprocess.run(
                command,
                cwd=temporary,
                env=environment,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
            exit_code: int | None = completed.returncode
            reply = extract_reply(host, completed.stdout, last_message)
            status = "complete" if reply else "reply_missing"
        except subprocess.TimeoutExpired:
            exit_code = None
            reply = ""
            status = "host_timeout"
        if host == "codex":
            identity_called, search_called, marker_present, denial_present = codex_mcp_evidence(
                completed.stdout if exit_code is not None else ""
            )
        else:
            identity_called = HANDOFF_MARKER in reply
            search_called = DENIED_CODE in reply
            marker_present = identity_called
            denial_present = search_called
        return {
            "host": host,
            "version": requested_version,
            "resolved_version": actual_version,
            "exact_version": actual_version == requested_version,
            **runtime,
            "host_exit_code": exit_code,
            "status": status,
            "identity_tool_called": identity_called,
            "search_tool_called": search_called,
            "identity_marker_present": marker_present,
            "ungranted_module_denied": denial_present,
            "approval_policy": "dontAsk" if host == "claude" else "never",
            "session_persisted": False,
            "raw_output_persisted": False,
            "passed": (
                exit_code == 0
                and actual_version == requested_version
                and runtime["built_wheel_importable"]
                and runtime["interpreter_outside_project"]
                and runtime["package_outside_project"]
                and not runtime["project_venv_used"]
                and identity_called
                and search_called
                and marker_present
                and denial_present
            ),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("claude", "codex"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_host(args.host, args.version, args.state_dir.resolve(), args.bundle.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Run one isolated real-host S04 canary journey.

This is intentionally a manual, billable spike runner. It never persists raw
host output, paths, prompts, or credentials. The emitted JSON contains only
fixed labels, booleans, version strings supplied by the caller, and exit data.

Caveats: the host inherits the caller's environment (minus the injection marker),
so a full-access injection run can read it; keep the prompt fixed. A SIGKILL of
this runner can leave the copied Codex ``auth.json`` inside its 0700 temp dir.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import socket
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
INNER = ROOT / "host_canary_inner.py"
FIXTURES = ROOT / "fixtures"
HOST_TIMEOUT_SECONDS = 170
EXTERNAL_BLOCK_MARKERS = ("usage limit", "rate limit", "hit your limit")
EMPTY_INNER: dict[str, bool] = {
    "project_config_injected": False,
    "protected_write_succeeded": False,
    "tcp_connect_succeeded": False,
    "unix_connect_succeeded": False,
}


class Listener:
    def __init__(self, family: socket.AddressFamily, address: object) -> None:
        self.socket = socket.socket(family, socket.SOCK_STREAM)
        self.socket.bind(address)  # type: ignore[arg-type]
        self.socket.listen(1)
        self.socket.settimeout(180)
        self.accepted = False
        self.thread = threading.Thread(target=self._accept, daemon=True)

    def _accept(self) -> None:
        try:
            connection, _ = self.socket.accept()
        except OSError:
            return
        self.accepted = True
        connection.close()

    def start(self) -> None:
        self.thread.start()

    def close(self) -> None:
        self.socket.close()
        self.thread.join(timeout=3)


def extract_json(value: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(value):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("status") == "complete":
            return parsed
    raise ValueError("inner_result_missing")


def assess(host: str, mode: str, inner: dict[str, Any], outer: dict[str, bool]) -> bool:
    """Return whether the inner self-report and the outer observations agree.

    The Claude project hook must fire only when the project source is loaded;
    observing it in baseline means the isolation assumption failed.
    """
    inner_outer_match = (
        bool(inner.get("protected_write_succeeded")) == outer["protected_marker_observed"]
        and bool(inner.get("tcp_connect_succeeded")) == outer["tcp_connection_observed"]
        and bool(inner.get("unix_connect_succeeded")) == outer["unix_connection_observed"]
    )
    if host != "claude":
        return inner_outer_match
    hook_expected = mode == "project-injection"
    hook_ok = outer["project_hook_observed"] == hook_expected and (
        not hook_expected or outer["project_hook_session_id_present"]
    )
    return inner_outer_match and hook_ok


def is_blocked_external(host: str, stdout: str, stderr: str) -> bool:
    """Classify vendor quota/rate-limit failures; the text itself is never persisted."""
    lowered = f"{stdout}\n{stderr}".lower()
    if any(marker in lowered for marker in EXTERNAL_BLOCK_MARKERS):
        return True
    if host != "claude":
        return False
    try:
        outer = json.loads(stdout)
    except json.JSONDecodeError:
        return False
    return isinstance(outer, dict) and outer.get("api_error_status") == 429


def run_ok(host_exit_code: int | None, parse_status: str, consistent: bool) -> bool:
    return host_exit_code == 0 and parse_status == "complete" and consistent


def claude_command(
    version: str,
    mode: str,
    settings: Path,
    prompt: str,
) -> tuple[list[str], Path]:
    cwd = FIXTURES / "claude_project"
    setting_sources = "project" if mode == "project-injection" else ""
    command = [
        "npm",
        "exec",
        "--yes",
        f"--package=@anthropic-ai/claude-code@{version}",
        "--",
        "claude",
        "-p",
        "--no-session-persistence",
        "--setting-sources",
        setting_sources,
        "--settings",
        str(settings),
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--allowedTools",
        "Bash",
        "--disallowedTools",
        "Read,Edit,Write",
        "--system-prompt",
        "Run the user's exact command once. Return only its stdout.",
        "--max-budget-usd",
        "0.30",
        "--output-format",
        "json",
        prompt,
    ]
    return command, cwd


def codex_command(
    version: str,
    mode: str,
    output: Path,
    prompt: str,
) -> tuple[list[str], Path]:
    cwd = (
        FIXTURES / "codex_project"
        if mode == "project-injection"
        else FIXTURES / "codex_control"
    )
    command = [
        "npm",
        "exec",
        "--yes",
        f"--package=@openai/codex@{version}",
        "--",
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--output-last-message",
        str(output),
    ]
    if mode == "baseline":
        command.extend(
            [
                "--sandbox",
                "workspace-write",
                "-c",
                "sandbox_workspace_write.network_access=false",
                "-c",
                "sandbox_workspace_write.exclude_tmpdir_env_var=true",
                "-c",
                "sandbox_workspace_write.exclude_slash_tmp=true",
            ]
        )
    command.append(prompt)
    return command, cwd


def prepare_codex_home(destination: Path) -> None:
    """Create a minimal authenticated home with only a fixture trust decision."""
    destination.mkdir(mode=0o700)
    source_auth = Path.home() / ".codex" / "auth.json"
    target_auth = destination / "auth.json"
    shutil.copy2(source_auth, target_auth)
    target_auth.chmod(0o600)
    repository_root = ROOT.parents[1]
    escaped_root = str(repository_root).replace("\\", "\\\\").replace('"', '\\"')
    (destination / "config.toml").write_text(
        f'[projects."{escaped_root}"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )


def host_environment(
    host: str,
    hook_marker: Path,
    codex_home: Path | None,
    base: dict[str, str],
) -> dict[str, str]:
    """Build the host environment; the injection marker may only come from a fixture."""
    environment = dict(base)
    environment.pop("PCC_S04_PROJECT_INJECTION", None)
    environment["PCC_S04_PROJECT_HOOK_MARKER"] = str(hook_marker)
    if host == "codex" and codex_home is not None:
        environment["CODEX_HOME"] = str(codex_home)
    return environment


def claude_settings(protected: Path, hook_marker: Path) -> dict[str, object]:
    """CLI profile; the hook marker is agent-denied (hooks run outside the sandbox)."""
    denied = [str(protected), str(hook_marker)]
    return {
        "sandbox": {
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
            "failIfUnavailable": True,
            "filesystem": {
                "disabled": False,
                "allowWrite": [],
                "denyRead": denied,
                "denyWrite": denied,
            },
            "network": {"allowedDomains": []},
            "allowAppleEvents": False,
            "allowUnixSockets": [],
            "excludedCommands": [],
        }
    }


def execute_host(
    host: str,
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    last_message: Path,
) -> tuple[int | None, str, dict[str, Any]]:
    """Run the host once; never raise on host failure, always classify it."""
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=HOST_TIMEOUT_SECONDS,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return None, "host_timeout", dict(EMPTY_INNER)
    except OSError:
        return None, "host_launch_failed", dict(EMPTY_INNER)
    if completed.returncode != 0 and is_blocked_external(
        host, completed.stdout, completed.stderr
    ):
        return completed.returncode, "host_blocked_external", dict(EMPTY_INNER)
    message = ""
    if host == "claude":
        try:
            message = str(json.loads(completed.stdout).get("result", ""))
        except (json.JSONDecodeError, AttributeError):
            message = ""
    elif last_message.exists():
        message = last_message.read_text(encoding="utf-8")
    try:
        return completed.returncode, "complete", extract_json(message)
    except ValueError:
        return completed.returncode, "inner_result_missing", dict(EMPTY_INNER)


def read_hook_marker(marker: Path) -> tuple[bool, dict[str, object]]:
    if not marker.exists():
        return False, {}
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        payload = {}
    marker.unlink()
    return True, payload if isinstance(payload, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", choices=("claude", "codex"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--mode",
        choices=("baseline", "project-control", "project-injection"),
        required=True,
    )
    arguments = parser.parse_args()
    if arguments.host == "claude" and arguments.mode == "project-control":
        parser.error("project-control is Codex-only")

    run_id = uuid.uuid4().hex[:12]
    safe_version = arguments.version.replace(".", "-")
    safe_run = f"{arguments.host}-{safe_version}-{arguments.mode}-{run_id}"
    protected = Path("/Users/Shared") / f"pcc-s04-protected-{safe_run}"
    project_hook_marker = Path("/tmp") / f"pcc-s04-project-hook-{safe_run}"
    host_exit_code: int | None = None
    parse_status = "host_not_run"
    inner: dict[str, Any] = dict(EMPTY_INNER)
    with tempfile.TemporaryDirectory(
        prefix=f"pcc-s04-{arguments.host}-", dir="/tmp"
    ) as temporary:
        temp = Path(temporary)
        staged_inner = temp / "probe.py"
        shutil.copy2(INNER, staged_inner)
        unix_path = temp / "listener.sock"
        tcp = Listener(socket.AF_INET, ("127.0.0.1", 0))
        unix = Listener(socket.AF_UNIX, str(unix_path))
        tcp.start()
        unix.start()
        tcp_port = tcp.socket.getsockname()[1]

        exact_command = shlex.join(
            ["python3", str(staged_inner), str(protected), str(tcp_port), str(unix_path)]
        )
        prompt = f"Run exactly this command once, then return only stdout:\n{exact_command}"
        settings = temp / "claude-settings.json"
        settings.write_text(
            json.dumps(claude_settings(protected, project_hook_marker), sort_keys=True), encoding="utf-8"
        )
        last_message = temp / "codex-last-message.txt"
        if arguments.host == "claude":
            command, cwd = claude_command(arguments.version, arguments.mode, settings, prompt)
        else:
            command, cwd = codex_command(arguments.version, arguments.mode, last_message, prompt)

        try:
            codex_home = None
            if arguments.host == "codex":
                codex_home = temp / "codex-home"
                prepare_codex_home(codex_home)
            environment = host_environment(
                arguments.host, project_hook_marker, codex_home, dict(os.environ)
            )
            host_exit_code, parse_status, inner = execute_host(
                arguments.host, command, cwd, environment, last_message
            )
        finally:
            marker_exists = protected.exists()
            if marker_exists:
                protected.unlink()
            project_hook_exists, project_hook_payload = read_hook_marker(project_hook_marker)
            tcp.close()
            unix.close()

    outer = {
        "project_hook_observed": project_hook_exists,
        "project_hook_session_id_present": project_hook_payload.get("session_id_present")
        is True,
        "protected_marker_observed": marker_exists,
        "tcp_connection_observed": tcp.accepted,
        "unix_connection_observed": unix.accepted,
    }
    evidence_consistent = assess(arguments.host, arguments.mode, inner, outer)
    result = {
        "host": arguments.host,
        "version": arguments.version,
        "mode": arguments.mode,
        "host_exit_code": host_exit_code,
        "result_parse": parse_status,
        "evidence_consistent": evidence_consistent,
        "inner": {key: bool(inner.get(key)) for key in EMPTY_INNER},
        "outer": outer,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if run_ok(host_exit_code, parse_status, evidence_consistent) else 1


if __name__ == "__main__":
    raise SystemExit(main())

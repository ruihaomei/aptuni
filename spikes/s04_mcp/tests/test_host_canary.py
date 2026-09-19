"""Local tests for the real-host canary protocol and outer attribution."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from unittest import mock

import run_host_canary
from run_host_canary import EMPTY_INNER, INNER, Listener, assess, extract_json, run_ok


class HostCanaryProtocolTests(unittest.TestCase):
    def test_extract_json_ignores_host_noise(self) -> None:
        expected = {
            "status": "complete",
            "project_config_injected": False,
            "protected_write_succeeded": False,
            "tcp_connect_succeeded": False,
            "unix_connect_succeeded": False,
        }
        noisy = f"host preface\n{json.dumps(expected)}\nhost suffix"
        self.assertEqual(expected, extract_json(noisy))

    def test_direct_inner_success_is_independently_observed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "private-marker-name"
            unix_path = root / "listener.sock"
            tcp = Listener(socket.AF_INET, ("127.0.0.1", 0))
            unix = Listener(socket.AF_UNIX, str(unix_path))
            tcp.start()
            unix.start()
            environment = os.environ.copy()
            environment.pop("PCC_S04_PROJECT_INJECTION", None)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(INNER),
                    str(marker),
                    str(tcp.socket.getsockname()[1]),
                    str(unix_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            result = json.loads(completed.stdout)
            tcp.close()
            unix.close()

            self.assertTrue(result["protected_write_succeeded"])
            self.assertTrue(result["tcp_connect_succeeded"])
            self.assertTrue(result["unix_connect_succeeded"])
            self.assertFalse(result["project_config_injected"])
            self.assertTrue(marker.exists())
            self.assertTrue(tcp.accepted)
            self.assertTrue(unix.accepted)
            self.assertNotIn(marker.name, completed.stdout)
            self.assertNotIn(str(unix_path), completed.stdout)


def _outer(**overrides: bool) -> dict[str, bool]:
    outer = {
        "project_hook_observed": False,
        "project_hook_session_id_present": False,
        "protected_marker_observed": False,
        "tcp_connection_observed": False,
        "unix_connection_observed": False,
    }
    outer.update(overrides)
    return outer


class HostCanaryAssessmentTests(unittest.TestCase):
    def test_inner_claim_without_outer_observation_is_inconsistent(self) -> None:
        inner = dict(EMPTY_INNER, tcp_connect_succeeded=True)
        self.assertFalse(assess("codex", "baseline", inner, _outer()))

    def test_outer_effect_hidden_by_inner_is_inconsistent(self) -> None:
        outer = _outer(protected_marker_observed=True)
        self.assertFalse(assess("codex", "project-injection", dict(EMPTY_INNER), outer))

    def test_claude_hook_required_only_for_project_injection(self) -> None:
        hooked = _outer(project_hook_observed=True, project_hook_session_id_present=True)
        self.assertTrue(assess("claude", "project-injection", dict(EMPTY_INNER), hooked))
        self.assertFalse(assess("claude", "project-injection", dict(EMPTY_INNER), _outer()))
        self.assertFalse(assess("claude", "baseline", dict(EMPTY_INNER), hooked))
        self.assertTrue(assess("claude", "baseline", dict(EMPTY_INNER), _outer()))

    def test_hook_without_session_id_is_not_proof(self) -> None:
        outer = _outer(project_hook_observed=True)
        self.assertFalse(assess("claude", "project-injection", dict(EMPTY_INNER), outer))

    def test_run_ok_requires_exit_parse_and_consistency(self) -> None:
        self.assertTrue(run_ok(0, "complete", True))
        self.assertFalse(run_ok(None, "host_timeout", True))
        self.assertFalse(run_ok(0, "inner_result_missing", True))
        self.assertFalse(run_ok(0, "complete", False))
        self.assertFalse(run_ok(1, "complete", True))

    def test_host_timeout_is_classified_not_raised(self) -> None:
        with mock.patch.object(
            run_host_canary.subprocess,
            "run",
            side_effect=run_host_canary.subprocess.TimeoutExpired("host", 1),
        ):
            code, status, inner = run_host_canary.execute_host(
                "claude", ["host"], Path("."), {}, Path("missing")
            )
        self.assertIsNone(code)
        self.assertEqual("host_timeout", status)
        self.assertEqual(EMPTY_INNER, inner)

    def test_malformed_claude_output_is_classified(self) -> None:
        completed = run_host_canary.subprocess.CompletedProcess([], 0, "not json", "")
        with mock.patch.object(run_host_canary.subprocess, "run", return_value=completed):
            code, status, _ = run_host_canary.execute_host(
                "claude", ["host"], Path("."), {}, Path("missing")
            )
        self.assertEqual(0, code)
        self.assertEqual("inner_result_missing", status)

    def test_vendor_usage_limit_is_blocked_external(self) -> None:
        completed = run_host_canary.subprocess.CompletedProcess(
            [], 1, "", "ERROR: You've hit your usage limit. Try again later."
        )
        with mock.patch.object(run_host_canary.subprocess, "run", return_value=completed):
            code, status, inner = run_host_canary.execute_host(
                "codex", ["host"], Path("."), {}, Path("missing")
            )
        self.assertEqual(1, code)
        self.assertEqual("host_blocked_external", status)
        self.assertEqual(EMPTY_INNER, inner)

    def test_claude_rate_limit_status_is_blocked_external(self) -> None:
        stdout = json.dumps({"is_error": True, "api_error_status": 429, "result": ""})
        completed = run_host_canary.subprocess.CompletedProcess([], 1, stdout, "")
        with mock.patch.object(run_host_canary.subprocess, "run", return_value=completed):
            _, status, _ = run_host_canary.execute_host(
                "claude", ["host"], Path("."), {}, Path("missing")
            )
        self.assertEqual("host_blocked_external", status)


if __name__ == "__main__":
    unittest.main()

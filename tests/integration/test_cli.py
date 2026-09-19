"""CLI end to end: the first runnable Aptuni capability."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run(state: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, APTUNI_STATE_DIR=str(state), PYTHONPATH=str(REPO / "src"))
    return subprocess.run([sys.executable, "-m", "aptuni", *args], env=env, capture_output=True,
                          text=True, check=False)


def test_init_remember_facts_module_doctor_flow() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        state = base / "state"
        init = run(state, "init", str(base / "Aptuni"))
        assert init.returncode == 0, init.stderr
        assert "Aptuni" in init.stdout

        added = run(state, "remember", "Prefers concise answers.", "--module", "preferences")
        assert added.returncode == 0, added.stderr
        fact_id = added.stdout.split()[-1]
        assert fact_id.startswith("fct_")

        listed = run(state, "facts", "--json")
        assert listed.returncode == 0, listed.stderr
        assert [f["statement"] for f in json.loads(listed.stdout)] == ["Prefers concise answers."]

        hide = run(state, "module", "set", "preferences", "--expose", "off")
        assert hide.returncode == 0, hide.stderr
        modules = run(state, "module", "list", "--json")
        assert json.loads(modules.stdout)["preferences"] == {"ingest": True, "expose": False}

        status = run(state, "status", "--json")
        assert json.loads(status.stdout)["policy_epoch"] == 2

        doctor = run(state, "doctor")
        assert doctor.returncode == 0, doctor.stdout + doctor.stderr


def test_errors_are_reported_without_tracebacks() -> None:
    with tempfile.TemporaryDirectory() as raw:
        result = run(Path(raw) / "state", "status")
        assert result.returncode == 1
        assert "aptuni init" in result.stderr
        assert "Traceback" not in result.stderr


def test_version_flag() -> None:
    with tempfile.TemporaryDirectory() as raw:
        result = run(Path(raw) / "state", "--version")
        assert result.returncode == 0
        assert "aptuni" in result.stdout

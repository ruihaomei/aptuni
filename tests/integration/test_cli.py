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


def test_folder_source_add_sync_and_inspect_flow() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        state = base / "state"
        docs = base / "materials"
        docs.mkdir()
        (docs / "profile.md").write_text("Built bilingual retrieval in Python.", encoding="utf-8")
        assert run(state, "init", str(base / "Aptuni")).returncode == 0

        added = run(
            state,
            "source",
            "add-folder",
            str(docs),
            "--module",
            "projects",
            "--role",
            "portfolio",
            "--json",
        )
        assert added.returncode == 0, added.stderr
        source_id = json.loads(added.stdout)["id"]
        assert source_id.startswith("src_")

        listed = run(state, "source", "list", "--json")
        assert [item["id"] for item in json.loads(listed.stdout)] == [source_id]

        synced = run(state, "sync", source_id, "--json")
        assert synced.returncode == 0, synced.stderr
        assert json.loads(synced.stdout)["counts"] == {"add": 1}

        evidence = run(state, "evidence", "--source", source_id, "--json")
        assert evidence.returncode == 0, evidence.stderr
        [item] = json.loads(evidence.stdout)
        assert item["module"] == "projects"
        assert item["signals"] == ["exposure"]
        assert item["relative_path"] == "profile.md"

        review = run(state, "review", "list", source_id, "--json")
        assert review.returncode == 0, review.stderr
        assert json.loads(review.stdout) == []


def test_github_source_configuration_keeps_a_token_reference_not_a_secret() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        state = base / "state"
        assert run(state, "init", str(base / "Aptuni")).returncode == 0
        added = run(
            state,
            "source",
            "add-github",
            "https://github.com/ruihaomei/ctffr-app",
            "--module",
            "projects",
            "--role",
            "maintained_research_software",
            "--token-env",
            "APTUNI_GITHUB_TOKEN",
            "--json",
        )
        assert added.returncode == 0, added.stderr
        payload = json.loads(added.stdout)
        assert payload["type"] == "github"
        assert payload["roots"] == [
            "https://github.com/ruihaomei/ctffr-app",
            "api:https://api.github.com",
            "env:APTUNI_GITHUB_TOKEN",
        ]


def test_bilingual_search_and_index_lifecycle_flow() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        state = base / "state"
        assert run(state, "init", str(base / "Aptuni")).returncode == 0
        added = run(state, "remember", "Applied 生存分析 with Python.", "--module", "knowledge")
        record_id = added.stdout.split()[-1]

        searched = run(state, "search", "生存", "--json")
        assert searched.returncode == 0, searched.stderr
        assert [item["id"] for item in json.loads(searched.stdout)] == [record_id]

        status = run(state, "index", "status", "--json")
        assert status.returncode == 0, status.stderr
        assert json.loads(status.stdout)["state"] == "ready"
        deleted = run(state, "index", "delete")
        assert deleted.returncode == 0, deleted.stderr
        assert json.loads(run(state, "index", "status", "--json").stdout)["state"] == "missing"


def test_bounded_identity_and_context_flow() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        state = base / "state"
        assert run(state, "init", str(base / "Aptuni")).returncode == 0
        run(state, "remember", "Statistics graduate student.", "--module", "identity")
        fact = run(state, "remember", "Applied causal inference in Python.", "--module", "knowledge")
        fact_id = fact.stdout.split()[-1]

        identity = json.loads(run(state, "identity", "--budget", "600", "--json").stdout)
        assert identity["layers"] == ["L0"]
        context = run(
            state,
            "context",
            "causal inference",
            "--module",
            "knowledge",
            "--budget",
            "1200",
            "--json",
        )
        assert context.returncode == 0, context.stderr
        payload = json.loads(context.stdout)
        assert payload["audience"] == "owner_cli"
        assert payload["used_units"] <= 1200
        assert any(item["canonical_id"] == fact_id for item in payload["items"])

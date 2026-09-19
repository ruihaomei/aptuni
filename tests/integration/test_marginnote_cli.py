"""MarginNote CLI: discovery persists nothing, evidence links back to the card, pipes stay quiet."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from marginnote_fixture import base_cards, build_store, nid

REPO = Path(__file__).resolve().parents[2]


def run(state: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, APTUNI_STATE_DIR=str(state), PYTHONPATH=f"{REPO / 'src'}{os.pathsep}{REPO / 'tests'}")
    return subprocess.run([sys.executable, "-m", "aptuni", *args], env=env, capture_output=True, text=True,
                          check=False, stdin=subprocess.DEVNULL)


def test_discover_add_sync_evidence_round_trip(tmp_path: Path) -> None:
    state = tmp_path / "state"
    container = tmp_path / "container"
    store = build_store(container / "Library" / "Private Documents" / "MN4NotebookDatabase" / "0"
                        / "MarginNotes.sqlite", base_cards())
    found = run(state, "source", "discover-marginnote", "--container", str(container), "--json")
    assert found.returncode == 0, found.stderr
    listing = json.loads(found.stdout)
    assert listing["status"] == "found" and listing["stores"][0]["status"] == "supported"
    assert {n["id"] for n in listing["stores"][0]["notebooks"]} == {"NB-A", "NB-B"}
    assert not state.exists(), "discovery must not persist anything"

    assert run(state, "init", str(tmp_path / "Aptuni")).returncode == 0
    added = run(state, "source", "add-marginnote", "--store", str(store), "--notebook", "NB-A",
                "--module", "knowledge", "--role", "study-notes", "--json")
    assert added.returncode == 0, added.stderr
    source_id = json.loads(added.stdout)["id"]
    assert run(state, "sync", source_id).returncode == 0
    evidence = json.loads(run(state, "evidence", "--source", source_id, "--json").stdout)
    links = {e["open_url"] for e in evidence}
    assert f"marginnote4app://note/{nid(2)}" in links
    assert all("SECRET-BODY" not in (e["excerpt"] or "") for e in evidence)


def test_missing_library_is_reported_without_a_traceback(tmp_path: Path) -> None:
    done = run(tmp_path / "state", "source", "discover-marginnote", "--container", str(tmp_path / "none"))
    assert done.returncode == 2 and "not_found" in done.stdout and "Traceback" not in done.stderr


def test_closed_pipe_is_not_reported_as_a_vault_problem(tmp_path: Path) -> None:
    state = tmp_path / "state"
    run(state, "init", str(tmp_path / "Aptuni"))
    env = dict(os.environ, APTUNI_STATE_DIR=str(state), PYTHONPATH=str(REPO / "src"))
    done = subprocess.run(f"{sys.executable} -m aptuni plugin list | head -1", shell=True, env=env,
                          capture_output=True, text=True, check=False)
    assert "Vault" not in done.stderr and "Traceback" not in done.stderr

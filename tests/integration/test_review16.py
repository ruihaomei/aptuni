"""Regressions for review 16 (M1 Slice 1): each test reproduces a reviewer finding."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from aptuni.application import service as service_module
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import SchemaVersionError, parse_record
from aptuni.vault.store import Vault
from support import golden_raw

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def base() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as raw:
        yield Path(raw)


def two_services(base: Path) -> tuple[AptuniService, AptuniService]:
    first = AptuniService(Workspace(state_dir=base / "state"))
    first.init(base / "Aptuni")
    return first, AptuniService(Workspace(state_dir=base / "state"))


# F1 -------------------------------------------------------------------------------------------
def test_concurrent_policy_change_is_not_lost(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a, b = two_services(base)
    original = service_module.with_switch

    def racing(*args: Any, **kwargs: Any) -> Any:
        monkeypatch.setattr(service_module, "with_switch", original)
        b.set_module("goals", ingest=False)  # another writer commits first
        return original(*args, **kwargs)

    monkeypatch.setattr(service_module, "with_switch", racing)
    with pytest.raises(AptuniError) as error:
        a.set_module("behavior", expose=False)
    assert error.value.code == "concurrent_write"
    a.set_module("behavior", expose=False)  # retry on fresh state succeeds
    modules = AptuniService(Workspace(state_dir=base / "state")).status().modules
    assert modules["behavior"] == (True, False)
    assert modules["goals"] == (False, True)


def test_write_based_on_stale_ingest_check_is_rejected(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a, b = two_services(base)
    original = service_module.can_ingest

    def racing(*args: Any, **kwargs: Any) -> bool:
        monkeypatch.setattr(service_module, "can_ingest", original)
        result = original(*args, **kwargs)
        b.set_module("experience", ingest=False)
        return result

    monkeypatch.setattr(service_module, "can_ingest", racing)
    with pytest.raises(AptuniError) as error:
        a.remember("Worked at ACME.", module="experience")
    assert error.value.code == "concurrent_write"
    assert AptuniService(Workspace(state_dir=base / "state")).facts() == []


# F2 -------------------------------------------------------------------------------------------
def test_init_refuses_a_non_empty_folder(base: Path) -> None:
    target = base / "project"
    (target / "records").mkdir(parents=True)
    (target / "records" / "tax-2025.pdf").write_text("keep me", encoding="utf-8")
    service = AptuniService(Workspace(state_dir=base / "state"))
    with pytest.raises(AptuniError) as error:
        service.init(target)
    assert error.value.code == "vault_dir_not_empty"
    assert (target / "records" / "tax-2025.pdf").exists()


def test_recovery_never_deletes_foreign_files(base: Path) -> None:
    service = AptuniService(Workspace(state_dir=base / "state"))
    service.init(base / "Aptuni")
    records = base / "Aptuni" / "records"
    (records / "notes.pdf").write_text("user file", encoding="utf-8")
    (records / "folder").mkdir()
    again = AptuniService(Workspace(state_dir=base / "state"))
    assert again.status().seq == 1  # opens fine
    assert (records / "notes.pdf").exists() and (records / "folder").exists()
    report = again.doctor()
    assert not report.ok
    assert any("notes.pdf" in problem for problem in report.problems)


# F3 -------------------------------------------------------------------------------------------
def test_correction_respects_the_ingest_switch(base: Path) -> None:
    a, _ = two_services(base)
    fact = a.remember("Class rank 2.", module="experience")
    a.set_module("experience", ingest=False)
    with pytest.raises(AptuniError) as error:
        a.correct(fact.id, "Class rank 1.")
    assert error.value.code == "module_ingest_disabled"


# F4, F5 ---------------------------------------------------------------------------------------
def test_purged_ids_cannot_be_recommitted(base: Path) -> None:
    vault = Vault.init(base / "v", base / "s")
    records = [parse_record(raw) for raw in golden_raw()]
    vault.commit(records, expected_seq=0)
    target = "obs_00000000000000000000000002"
    vault.purge({target}, expected_seq=1)
    again = next(r for r in records if r.id == target)
    with pytest.raises(InvariantError):
        vault.commit([again], expected_seq=vault.head().seq)


def test_torn_ledger_tail_does_not_brick_open(base: Path) -> None:
    vault = Vault.init(base / "v", base / "s")
    vault.commit([parse_record(raw) for raw in golden_raw()], expected_seq=0)
    vault.purge({"obs_00000000000000000000000002"}, expected_seq=1)
    with open(base / "s" / "deletion-ledger.jsonl", "a", encoding="utf-8") as handle:
        handle.write('{"id": "led_trunc')
    reopened = Vault.open(base / "v", base / "s")
    assert "obs_00000000000000000000000002" not in {r.id for r in reopened.read_all()}



@pytest.mark.parametrize("purged", [
    {"fct_00000000000000000000000004"},
    {"fct_00000000000000000000000003", "fct_00000000000000000000000004"},
])
def test_purge_after_torn_ledger_tail_keeps_every_entry(base: Path, purged: set[str]) -> None:
    """Review 19 N1: a torn fragment must not swallow the next purge's first ledger entry."""
    from aptuni.domain.ids import sha256_text

    records = [parse_record(raw) for raw in golden_raw()]
    vault = Vault.init(base / "v", base / "s")
    vault.commit(records, expected_seq=0)
    vault.purge({"obs_00000000000000000000000002"}, expected_seq=1)
    with open(base / "s" / "deletion-ledger.jsonl", "a", encoding="utf-8") as handle:
        handle.write('{"id": "led_trunc')
    opened = Vault.open(base / "v", base / "s")
    opened.purge(purged, expected_seq=opened.head().seq)
    reopened = Vault.open(base / "v", base / "s")
    assert {sha256_text(rid) for rid in purged} <= reopened.ledger_digests()
    again = next(r for r in records if r.id in purged)
    with pytest.raises(InvariantError):
        reopened.commit([again], expected_seq=reopened.head().seq)


@pytest.mark.parametrize(("label", "setup"), [
    ("config vault is int", lambda base: (base / "state" / "config.json").write_text('{"version":1,"vault":5}')),
    ("config is a list", lambda base: (base / "state" / "config.json").write_text("[]")),
    ("config invalid utf-8", lambda base: (base / "state" / "config.json").write_bytes(b"\xff\xfe")),
    ("stray HEAD temp dir", lambda base: (base / "Aptuni" / ".HEAD.x.tmp").mkdir()),
])
def test_malformed_state_never_prints_a_traceback(base: Path, label: str, setup: Any) -> None:
    """Review 19 N2: the CLI maps every unsafe-state failure to a fixed, content-free message."""
    env = dict(os.environ, APTUNI_STATE_DIR=str(base / "state"), PYTHONPATH=str(REPO / "src"))
    env.pop("APTUNI_DEBUG", None)
    subprocess.run([sys.executable, "-m", "aptuni", "init", str(base / "Aptuni")], env=env, check=True,
                   capture_output=True)
    setup(base)
    done = subprocess.run([sys.executable, "-m", "aptuni", "status"], env=env, capture_output=True, text=True,
                          check=False)
    assert "Traceback" not in done.stderr, label
    assert done.returncode != 0 or "Vault" in done.stdout, label


# F8 -------------------------------------------------------------------------------------------
def test_pending_or_quarantined_facts_are_never_exposable() -> None:
    raws = golden_raw()
    fact = next(r for r in raws if r["id"] == "fct_00000000000000000000000004")
    fact["review_status"] = "pending_review"
    exposed = {r.id for r in RecordSet([parse_record(r) for r in raws]).exposable()}
    assert "fct_00000000000000000000000004" not in exposed


# F9 -------------------------------------------------------------------------------------------
def test_integrity_errors_reach_the_cli_without_a_traceback(base: Path) -> None:
    env = dict(os.environ, APTUNI_STATE_DIR=str(base / "state"), PYTHONPATH=str(REPO / "src"))
    run = [sys.executable, "-m", "aptuni"]
    subprocess.run([*run, "init", str(base / "Aptuni")], env=env, check=True, capture_output=True)
    segment = next((base / "Aptuni" / "records").glob("seg-*.jsonl"))
    segment.write_text(segment.read_text(encoding="utf-8").replace("true", "false", 1), encoding="utf-8")
    result = subprocess.run([*run, "status"], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "doctor" in result.stderr


# F10 ------------------------------------------------------------------------------------------
def test_schema_version_must_be_the_integer_one() -> None:
    raw = golden_raw()[3] | {"schema_version": True}
    with pytest.raises(SchemaVersionError):
        parse_record(raw)


def test_non_finite_numbers_are_rejected() -> None:
    raw = next(r for r in golden_raw() if r["record_type"] == "fact") | {"object": float("nan")}
    with pytest.raises(ValueError):
        parse_record(raw)


def test_vault_root_is_private(base: Path) -> None:
    service = AptuniService(Workspace(state_dir=base / "state"))
    service.init(base / "Aptuni")
    assert (base / "Aptuni").stat().st_mode & 0o077 == 0

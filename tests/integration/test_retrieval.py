"""Disposable SQLite projection: bilingual search, policy, freshness, and rebuild safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.retrieval.sqlite import ProjectionDocument, SqliteProjection


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    app = AptuniService(Workspace(tmp_path / "state"))
    app.init(tmp_path / "Aptuni")
    return app


def canonical_bytes(service: AptuniService) -> dict[str, bytes]:
    vault = service.vault()
    return {path.name: path.read_bytes() for path in sorted(vault.records_dir.glob("seg-*.jsonl"))}


def test_search_hydrates_current_canonical_records_and_honors_module_filter(service: AptuniService) -> None:
    old = service.remember("Studied 生存分析 and Kaplan-Meier curves.", "knowledge")
    service.remember("Prefers concise answers.", "preferences")
    assert [hit.id for hit in service.search("生存", limit=5)] == [old.id]
    assert service.search("concise", module="knowledge") == []

    new = service.correct(old.id, "Applied 生存分析 in a course project.")
    assert [hit.id for hit in service.search("生存")] == [new.id]
    assert service.search("Kaplan") == []


def test_exposure_change_rebuilds_before_search_and_final_filter_denies_hidden_data(
    service: AptuniService,
) -> None:
    service.remember("Private Bayesian posterior notes.", "knowledge")
    assert service.search("Bayesian")
    service.set_module("knowledge", expose=False)
    assert service.search("Bayesian") == []


def test_policy_change_during_query_retries_and_never_returns_the_now_hidden_record(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service.remember("Sensitive causal inference notes.", "knowledge")
    service.search("causal")  # establish a ready index
    original = SqliteProjection.search
    changed = False

    def race(self: SqliteProjection, *args: object, **kwargs: object) -> list[object]:
        nonlocal changed
        if not changed:
            changed = True
            service.set_module("knowledge", expose=False)
        return original(self, *args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(SqliteProjection, "search", race)
    assert service.search("causal") == []


def test_projection_delete_and_rebuild_never_change_canonical_bytes(service: AptuniService) -> None:
    service.remember("Uses Python and SQLite FTS5.", "skills")
    before = canonical_bytes(service)
    service.rebuild_index()
    status = service.index_status()
    assert status.state == "ready" and status.records == 1 and status.bytes > 0
    assert status.path.stat().st_mode & 0o077 == 0
    service.delete_index()
    assert service.index_status().state == "missing"
    assert [hit.text for hit in service.search("SQLite")] == ["Uses Python and SQLite FTS5."]
    assert canonical_bytes(service) == before


def test_query_validation_and_fts_metacharacters_fail_cleanly(service: AptuniService) -> None:
    service.remember("Uses SQLite.", "skills")
    assert service.search('" OR NOT * : ^') == []
    with pytest.raises(AptuniError) as error:
        service.search("SQLite", limit=0)
    assert error.value.code == "invalid_search"


def test_corrupt_projection_is_rebuilt_from_canonical_records(service: AptuniService) -> None:
    record = service.remember("Bayesian posterior calibration.", "knowledge")
    service.rebuild_index()
    service.index_status().path.write_bytes(b"not a sqlite database")
    assert service.index_status().state == "corrupt"
    assert [hit.id for hit in service.search("Bayesian")] == [record.id]
    assert service.index_status().state == "ready"


def test_projection_lives_outside_the_vault(service: AptuniService) -> None:
    service.remember("Causal inference with propensity scores.", "knowledge")
    service.search("causal")
    status = service.index_status()
    assert status.path.is_relative_to(service.workspace.state_dir.resolve())
    assert not status.path.is_relative_to(service.vault().root.resolve())


def test_older_rebuild_cannot_replace_a_newer_projection(tmp_path: Path) -> None:
    projection = SqliteProjection(tmp_path / "state")
    newer = [ProjectionDocument("fct_new", "fact", "knowledge", None, "newer content")]
    older = [ProjectionDocument("fct_old", "fact", "knowledge", None, "older content")]
    projection.rebuild(newer, vault_seq=5)
    projection.rebuild(older, vault_seq=4)
    assert projection.status().vault_seq == 5
    assert [row.record_id for row in projection.search("newer")] == ["fct_new"]
    assert projection.search("older") == []


def _projection(tmp_path: Path, texts: dict[str, str]) -> SqliteProjection:
    projection = SqliteProjection(tmp_path / "state")
    documents = [ProjectionDocument(record_id, "fact", "knowledge", None, text) for record_id, text in texts.items()]
    projection.rebuild(documents, vault_seq=1)
    return projection


def test_task_shaped_queries_fall_back_to_ranked_any_term_matches(tmp_path: Path) -> None:
    projection = _projection(tmp_path, {
        "fct_ds": "Data science intern; built churn models with XGBoost.",
        "fct_tea": "Likes green tea in the afternoon.",
        "fct_survival": "学习过生存分析和 Cox 比例风险模型。",
    })
    hits = [row.record_id for row in projection.search("help me prepare for a data science interview")]
    assert hits == ["fct_ds"]
    assert [row.record_id for row in projection.search("教我生存分析")] == ["fct_survival"]


def test_all_term_matches_rank_before_fallback_matches(tmp_path: Path) -> None:
    projection = _projection(tmp_path, {
        "fct_both": "Survival analysis with Cox models.",
        "fct_one": "Survival skills for camping.",
    })
    assert next(row.record_id for row in projection.search("survival analysis")) == "fct_both"
    assert [row.record_id for row in projection.search("survival analysis", limit=1)] == ["fct_both"]

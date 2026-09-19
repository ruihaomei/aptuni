"""MarginNote 4 source end to end through the application service (ADR-0015)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from marginnote_fixture import base_cards, build_store, nid, unknown_digest


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    app = AptuniService(Workspace(tmp_path / "state"))
    app.init(tmp_path / "Aptuni")
    return app


def test_sync_emits_studied_digest_evidence_and_is_incremental(service: AptuniService, tmp_path: Path) -> None:
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", base_cards())
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes",
                                           primary_for=("knowledge.studied",))
    first = service.sync(source.id)
    assert first.evidence_written == 5 and first.review_items == 0
    evidence = {e.provenance.locator.subject_id: e for e in service.evidence(source.id)}
    forest = evidence[nid(2)]
    assert forest.signals == ("studied",) and forest.subject == "Ensemble methods › Random forest"
    assert "SECRET-BODY" not in (forest.excerpt or "")
    assert service.sync(source.id).evidence_written == 0

    cards = base_cards()
    cards[4].title = "Bootstrap aggregating"
    del cards[5]
    build_store(store, cards)
    third = service.sync(source.id)
    assert third.counts.get("remove") == 1
    current = {e.provenance.locator.subject_id for e in service.evidence(source.id)}
    assert nid(5) not in current and nid(4) in current
    assert service.doctor().ok


def test_without_authority_policy_cards_are_only_exposure(service: AptuniService, tmp_path: Path) -> None:
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", base_cards())
    source = service.add_marginnote_source(store, None, ("knowledge",), "study-notes")
    service.sync(source.id)
    assert {e.signals for e in service.evidence(source.id)} == {("exposure",)}


def test_unsupported_layout_stops_before_any_withdrawal(service: AptuniService, tmp_path: Path) -> None:
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", base_cards())
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes")
    service.sync(source.id)
    before = {e.id for e in service.evidence(source.id)}
    build_store(store, {}, digest=unknown_digest())
    with pytest.raises(AptuniError) as caught:
        service.sync(source.id)
    assert caught.value.code == "marginnote_schema_unsupported"
    assert {e.id for e in service.evidence(source.id)} == before


def test_add_requires_modules_and_a_notebook_scope(service: AptuniService, tmp_path: Path) -> None:
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", base_cards())
    with pytest.raises(AptuniError):
        service.add_marginnote_source(store, (), ("knowledge",), "study-notes")
    with pytest.raises(AptuniError):
        service.add_marginnote_source(store, ("NB-A",), (), "study-notes")

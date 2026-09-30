"""ADR-0028 lineage (Review 82 B1): successor Facts and owner decisions across source generations."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from marginnote_fixture import build_store, studied_cards

BAGGING = "Ensemble methods › Random forest › Bagging"


def _service(tmp_path: Path) -> tuple[AptuniService, str, Path]:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", studied_cards())
    source = service.add_marginnote_source(
        store, ("NB-A",), ("knowledge",), "study-notes", primary_for=("knowledge.studied",),
    )
    service.sync(source.id)
    return service, source.id, store


def _retitle(service: AptuniService, source_id: str, store: Path, title: str) -> None:
    cards = studied_cards()
    cards[4].title = title
    build_store(store, cards)
    service.sync(source_id)


def _derived(service: AptuniService, leaf: str) -> list:
    return [fact for fact in service.facts()
            if fact.type == "profile.evidence_signal" and fact.subject.endswith(f"› {leaf}")]


def _bagging(service: AptuniService):
    return next(fact for fact in service.facts() if fact.subject == BAGGING)


def test_a_source_correction_writes_the_exact_successor_fact(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    original = _bagging(service)

    _retitle(service, source_id, store, "Bootstrap aggregation")

    [successor] = _derived(service, "Bootstrap aggregation")
    assert successor.supersedes == (original.id,)
    assert successor.change_kind != "assert"
    evidence = service.records().get(successor.evidence_ids[0])
    assert successor.change_kind == evidence.change_kind
    assert service.records().superseded_by(original.id) == successor.id
    assert service.doctor().ok


def test_successors_chain_across_several_generations(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    first = _bagging(service)
    _retitle(service, source_id, store, "Bootstrap aggregation")
    [second] = _derived(service, "Bootstrap aggregation")
    _retitle(service, source_id, store, "Resampled aggregation")

    [third] = _derived(service, "Resampled aggregation")
    assert second.supersedes == (first.id,)
    assert third.supersedes == (second.id,)
    assert service.doctor().ok


def test_an_owner_edit_survives_two_later_source_generations(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    corrected_id = service.edit_profile_fact(_bagging(service).id, "Studied bootstrap aggregation in depth.")

    _retitle(service, source_id, store, "Bootstrap aggregation")
    assert _derived(service, "Bootstrap aggregation") == []
    _retitle(service, source_id, store, "Resampled aggregation")

    assert _derived(service, "Resampled aggregation") == []
    assert corrected_id in {fact.id for fact in service.facts()}
    assert service.refresh_profile() == []
    assert _derived(service, "Resampled aggregation") == []
    assert service.doctor().ok


def test_an_owner_rejection_is_never_recreated_by_later_source_changes(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    rejected = _bagging(service)
    assert service.review_profile_fact(rejected.id, "reject") == "revoked"

    _retitle(service, source_id, store, "Bootstrap aggregation")
    assert _derived(service, "Bootstrap aggregation") == []
    _retitle(service, source_id, store, "Resampled aggregation")

    assert _derived(service, "Resampled aggregation") == []
    assert service.refresh_profile() == []
    assert service.sync(source_id).profile_written == 0
    assert _derived(service, "Resampled aggregation") == []
    assert service.doctor().ok


def test_accept_is_not_an_action_on_evidence_derived_facts(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    fact = _bagging(service)

    with pytest.raises(AptuniError) as unsupported:
        service.review_profile_fact(fact.id, "accept")
    assert unsupported.value.code == "profile_action_unsupported"

    service.review_profile_fact(fact.id, "reject")
    with pytest.raises(AptuniError) as after_reject:
        service.review_profile_fact(fact.id, "accept")
    assert after_reject.value.code == "profile_action_unsupported"
    assert service.profile_review_state(fact.id) == "revoked"
    with pytest.raises(AptuniError):
        service.obsidian_action(fact.id, "accept")


def _purge(service: AptuniService, record_id: str) -> None:
    preview = service.privacy_purge_preview((record_id,))
    service.confirm_privacy_purge(preview.action_id, preview.digest)


def _assert_source_keeps_working(service: AptuniService, source_id: str, store: Path, leaf: str) -> None:
    assert service.sync(source_id).profile_written == 0
    assert service.refresh_profile() == []
    _retitle(service, source_id, store, leaf)
    assert _derived(service, leaf) == [], "a purged derivation is a permanent owner withdrawal"
    assert service.sync(source_id).evidence_written == 0
    assert service.doctor().ok
    assert not list((service.vault().root).rglob("*.pending.json"))


def test_purging_one_derived_fact_withdraws_its_lineage_without_freezing_the_source(tmp_path: Path) -> None:
    """Review 83 B1: deterministic ids must never be re-derived after the ledger holds them."""
    service, source_id, store = _service(tmp_path)
    _purge(service, _bagging(service).id)
    assert not [fact for fact in service.facts() if fact.subject == BAGGING]

    _assert_source_keeps_working(service, source_id, store, "Bootstrap aggregation")
    assert len(service.facts()) >= 1, "other topics of the same source stay in Profile"


def test_purging_an_owner_edit_withdraws_the_lineage(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    corrected_id = service.edit_profile_fact(_bagging(service).id, "Studied bootstrap aggregation in depth.")
    _purge(service, corrected_id)

    _assert_source_keeps_working(service, source_id, store, "Bootstrap aggregation")


def test_purging_the_middle_of_a_successor_chain_withdraws_the_lineage(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    _retitle(service, source_id, store, "Bootstrap aggregation")
    _retitle(service, source_id, store, "Resampled aggregation")
    [middle_or_last] = _derived(service, "Resampled aggregation")
    middle = service.records().get(middle_or_last.supersedes[0])
    _purge(service, middle.id)

    _assert_source_keeps_working(service, source_id, store, "Bagged ensembles")

"""ADR-0028: approved semantic Evidence forms Profile before retrospective review."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.domain.invariants import InvariantError, RecordSet
from marginnote_fixture import build_store, studied_cards


def _service(tmp_path: Path, *, authority: bool = True) -> tuple[AptuniService, str, Path]:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", studied_cards())
    source = service.add_marginnote_source(
        store,
        ("NB-A",),
        ("knowledge",),
        "study-notes",
        primary_for=("knowledge.studied",) if authority else (),
    )
    return service, source.id, store


def test_authoritative_studied_evidence_is_immediately_available_as_profile(
    tmp_path: Path,
) -> None:
    service, source_id, _ = _service(tmp_path)

    report = service.sync(source_id)

    facts = service.facts()
    assert report.evidence_written == 5
    assert report.profile_written == 5
    assert len(facts) == 5
    assert service.memories() == [], "source material is Profile, not interaction Memory"
    assert {fact.type for fact in facts} == {"profile.evidence_signal"}
    assert {fact.predicate for fact in facts} == {"studied"}
    assert all(len(fact.evidence_ids) == 1 and not fact.memory_ids for fact in facts)
    assert service.profile_review_pending() == []
    assert all(service.profile_review_state(fact.id) == "accepted" for fact in facts)
    assert {fact.id for fact in facts} <= {record.id for record in service.exposable()}
    assert service.doctor().ok


def test_plain_exposure_never_becomes_a_profile_claim(tmp_path: Path) -> None:
    service, source_id, _ = _service(tmp_path, authority=False)

    report = service.sync(source_id)

    assert report.evidence_written == 5
    assert report.profile_written == 0
    assert service.facts() == []
    assert service.profile_review_pending() == []


def test_profile_refresh_backfills_eligible_existing_evidence(tmp_path: Path) -> None:
    service, source_id, _ = _service(tmp_path)
    service.set_review_policy(auto_promotion_enabled=False)
    report = service.sync(source_id)
    assert report.evidence_written == 5 and report.profile_written == 0

    service.set_review_policy(auto_promotion_enabled=True)
    promoted = service.refresh_profile()

    assert len(promoted) == 5
    assert {fact.type for fact in promoted} == {"profile.evidence_signal"}
    assert service.refresh_profile() == []


def test_noop_sync_backfills_profile_after_policy_is_enabled(tmp_path: Path) -> None:
    service, source_id, _ = _service(tmp_path)
    service.set_review_policy(auto_promotion_enabled=False)
    service.sync(source_id)
    service.set_review_policy(auto_promotion_enabled=True)

    report = service.sync(source_id)

    assert report.evidence_written == 0
    assert report.profile_written == 5
    assert len(service.facts()) == 5


def test_evidence_change_replaces_the_fact_and_evidence_loss_withdraws_it(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    service.sync(source_id)
    before = {fact.subject: fact.id for fact in service.facts()}

    cards = studied_cards()
    cards[4].title = "Bootstrap aggregating"
    del cards[5]
    build_store(store, cards)
    report = service.sync(source_id)

    after = {fact.subject: fact.id for fact in service.facts()}
    assert report.profile_written > 0
    assert len(after) == 4
    old_subject = "Ensemble methods › Random forest › Bagging"
    new_subject = "Ensemble methods › Random forest › Bootstrap aggregating"
    assert old_subject not in after and new_subject in after
    assert "Ensemble methods › Random forest › Feature importance" not in after
    assert before[old_subject] not in after.values()
    assert service.doctor().ok


def test_owner_rejects_or_edits_after_promotion_without_accepting_first(tmp_path: Path) -> None:
    service, source_id, _ = _service(tmp_path)
    service.sync(source_id)
    first, second = service.facts()[:2]
    profile = {
        item["id"]: item
        for item in service.obsidian_snapshot()["profile"]
    }
    assert first.id not in {
        item["id"] for item in service.obsidian_snapshot()["pending_reviews"]
    }
    assert profile[first.id]["actions"] == ["show_evidence", "edit", "reject"]

    assert service.obsidian_action(first.id, "reject")["review_state"] == "revoked"
    edit = service.obsidian_action(
        second.id,
        "edit",
        statement="Studied the corrected topic description.",
    )
    corrected_id = edit["record_id"]

    assert first.id not in {fact.id for fact in service.facts()}
    corrected = service.records().get(corrected_id)
    assert corrected.statement == "Studied the corrected topic description."
    assert corrected.supersedes == (second.id,)
    assert corrected.trust == "user_declared"
    assert corrected.id in {fact.id for fact in service.facts()}
    assert service.profile_review_pending() == []
    assert service.doctor().ok


def test_owner_correction_is_not_replaced_by_a_later_source_change(tmp_path: Path) -> None:
    service, source_id, store = _service(tmp_path)
    service.sync(source_id)
    original = next(
        fact
        for fact in service.facts()
        if fact.subject == "Ensemble methods › Random forest › Bagging"
    )
    corrected_id = service.edit_profile_fact(original.id, "Studied bootstrap aggregation in depth.")
    cards = studied_cards()
    cards[4].title = "Bootstrap aggregation"
    build_store(store, cards)

    report = service.sync(source_id)

    assert report.profile_written == 1  # its parent outline also changed and remains auto-managed
    assert corrected_id in {fact.id for fact in service.facts()}
    assert not [
        fact
        for fact in service.facts()
        if fact.type == "profile.evidence_signal" and "Bootstrap aggregation" in fact.subject
    ]


def test_removing_a_source_also_withdraws_its_derived_profile(tmp_path: Path) -> None:
    service, source_id, _ = _service(tmp_path)
    service.sync(source_id)
    assert service.facts()

    preview = service.source_removal_preview(source_id)
    service.remove_source(source_id, preview.digest)

    assert service.facts() == []
    assert not [record for record in service.exposable()
                if record.record_type == "fact" and record.provenance.source_id == source_id]
    assert service.doctor().ok


def test_doctor_rejects_a_tampered_evidence_derived_statement(tmp_path: Path) -> None:
    service, source_id, _ = _service(tmp_path)
    service.sync(source_id)
    fact = service.facts()[0]
    tampered = fact.model_copy(update={"statement": "A different unsupported statement."})
    records = [tampered if record.id == fact.id else record for record in service.records().records()]

    with pytest.raises(InvariantError, match="exactly preserve authoritative Evidence"):
        RecordSet(records).validate()

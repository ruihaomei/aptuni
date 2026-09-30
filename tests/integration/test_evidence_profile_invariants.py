"""ADR-0028 canonical admission contract (Review 82 B2): forged Evidence-derived Facts never validate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import deterministic_id, sha256_text
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import AuthorityPolicy
from marginnote_fixture import build_store, studied_cards


def _synced(tmp_path: Path, *, authority: tuple[str, ...] = ("knowledge.studied",)) -> tuple[AptuniService, str]:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", studied_cards())
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes", primary_for=authority)
    service.sync(source.id)
    return service, source.id


def _event_for(records: RecordSet, fact_id: str) -> Any:
    return next(record for record in records.records()
                if record.record_type == "review_event" and record.target_id == fact_id)


def _replace(records: RecordSet, *replacements: Any) -> list[Any]:
    by_id = {record.id: record for record in replacements}
    return [by_id.pop(record.id, record) for record in records.records()] + list(by_id.values())


def _rejects_both_ways(service: AptuniService, records: list[Any], new: list[Any]) -> None:
    with pytest.raises(InvariantError):
        RecordSet(records).validate()
    with pytest.raises(InvariantError):
        RecordSet(records).validate(only={record.id for record in new})


def test_a_forged_second_fact_for_the_same_evidence_is_rejected(tmp_path: Path) -> None:
    service, _ = _synced(tmp_path)
    records = service.records()
    fact = records.current_facts()[0]
    event = _event_for(records, fact.id)
    forged = fact.model_copy(update={
        "id": deterministic_id("fct", "forged-duplicate"), "valid_from": "1999", "confidence": 1.0,
    })
    forged_event = event.model_copy(update={"id": deterministic_id("rev", "forged-duplicate"), "target_id": forged.id})

    _rejects_both_ways(service, [*records.records(), forged, forged_event], [forged, forged_event])
    seq, _ = service.snapshot()
    with pytest.raises(AptuniError) as refused:
        service._commit([forged, forged_event], seq)
    assert refused.value.code == "invariant_violation"


@pytest.mark.parametrize("update", [
    {"valid_from": "1999"},
    {"confidence": 1.0},
    {"valid_until": "2999"},
])
def test_changed_time_or_confidence_is_rejected(tmp_path: Path, update: dict[str, Any]) -> None:
    service, _ = _synced(tmp_path)
    records = service.records()
    fact = records.current_facts()[0]
    tampered = fact.model_copy(update=update)

    _rejects_both_ways(service, _replace(records, tampered), [tampered])


def test_an_exposure_only_fact_is_rejected_even_with_matching_authority(tmp_path: Path) -> None:
    service, source_id = _synced(tmp_path, authority=())
    records = service.records()
    source = records.get(source_id).model_copy(
        update={"authority": AuthorityPolicy(version=1, primary_for=("knowledge.exposure",))})
    evidence = next(item for item in records.current_evidence(source_id) if "exposure" in item.signals)
    template_service, _ = _synced(tmp_path / "template")
    template = template_service.records().current_facts()[0]
    template_event = _event_for(template_service.records(), template.id)
    fact = template.model_copy(update={
        "id": deterministic_id("fct", f"evidence-profile:{evidence.id}"), "predicate": "exposure",
        "evidence_ids": (evidence.id,), "subject": evidence.subject, "module": evidence.module,
        "provenance": evidence.provenance.model_copy(update={"locator": None}),
        "observed_at": evidence.observed_at, "statement": f"Demonstrated work involving {evidence.subject}.",
    })
    event = template_event.model_copy(update={
        "id": deterministic_id("rev", f"evidence-profile:{evidence.id}"), "target_id": fact.id,
        "action_digest": sha256_text(f"evidence_profile|{evidence.id}|{source_id}|{fact.policy_epoch}|exposure"),
    })

    _rejects_both_ways(service, [*_replace(records, source), fact, event], [fact, event])


def test_an_event_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    service, _ = _synced(tmp_path)
    records = service.records()
    event = _event_for(records, records.current_facts()[0].id)
    tampered = event.model_copy(update={"action_digest": sha256_text("something else")})

    _rejects_both_ways(service, _replace(records, tampered), [tampered])


def test_a_successor_that_drops_its_predecessor_link_is_rejected(tmp_path: Path) -> None:
    service, source_id = _synced(tmp_path)
    store = tmp_path / "mn" / "MarginNotes.sqlite"
    cards = studied_cards()
    cards[4].title = "Bootstrap aggregation"
    build_store(store, cards)
    service.sync(source_id)
    records = service.records()
    successor = next(fact for fact in records.current_facts() if fact.subject.endswith("Bootstrap aggregation"))
    assert successor.supersedes

    orphaned = successor.model_copy(update={"supersedes": (), "change_kind": "assert"})
    _rejects_both_ways(service, _replace(records, orphaned), [orphaned])

    unrelated = next(fact for fact in records.current_facts() if fact.id != successor.id)
    wrong_link = successor.model_copy(update={"supersedes": (unrelated.id,)})
    _rejects_both_ways(service, _replace(records, wrong_link), [wrong_link])

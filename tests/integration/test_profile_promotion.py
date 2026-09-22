"""ADR-0020: conservative Memory → stable Profile Fact promotion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.domain.ids import new_id, sha256_text
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import ReviewEvent
from aptuni.domain.temporal import utc_now


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    result = AptuniService(Workspace(tmp_path / "state"))
    result.init(tmp_path / "Aptuni")
    return result


def _memory(service: AptuniService, statement: str = "Prefers reproducible experiment pipelines.") -> str:
    proposal = service.observe(statement, "knowledge")
    assert proposal.memory_id is not None
    return proposal.memory_id


def test_pin_atomically_promotes_exact_owner_lineage_to_one_profile_fact(
    service: AptuniService,
) -> None:
    memory_id = _memory(service)
    before = service.status().seq

    assert service.review_memory(memory_id, "pin") == "pinned"

    assert service.status().seq == before + 1
    pending = service.profile_review_pending()
    assert len(pending) == 1
    fact = pending[0]
    memory = service.records().get(memory_id)
    assert fact.statement == memory.statement
    assert fact.memory_ids == (memory_id,)
    assert fact.evidence_ids == memory.evidence_ids
    assert fact.provenance == memory.provenance
    assert fact.type == "profile.promoted_memory"
    assert fact.predicate == "stable_memory"
    assert service.profile_review_state(fact.id) == "auto_promoted_pending_review"
    assert fact.id in {record.id for record in service.records().exposable()}
    unit = next(item for item in service.context("reproducible pipelines", budget=4000).units
                if item.canonical_id == fact.id)
    assert unit.review_state == "auto_promoted_pending_review"


def test_pinning_is_idempotent_and_never_duplicates_a_fact(service: AptuniService) -> None:
    memory_id = _memory(service)

    service.review_memory(memory_id, "pin")
    service.review_memory(memory_id, "pin")
    assert service.refresh_profile() == []

    assert [fact.memory_ids for fact in service.facts()] == [(memory_id,)]


@pytest.mark.parametrize("switch", ["ingest", "expose"])
def test_disabled_module_permission_blocks_profile_promotion(
    service: AptuniService, switch: str,
) -> None:
    memory_id = _memory(service)
    service.set_module("knowledge", **{switch: False})

    service.review_memory(memory_id, "pin")

    assert service.facts() == []
    assert service.refresh_profile() == []


def test_profile_reject_withdraws_only_the_fact_and_preserves_memory_history(
    service: AptuniService,
) -> None:
    memory_id = _memory(service)
    service.review_memory(memory_id, "pin")
    fact = service.profile_review_pending()[0]

    assert service.review_profile_fact(fact.id, "reject") == "revoked"

    assert service.facts() == []
    assert [memory.id for memory in service.memories()] == [memory_id]
    assert service.records().get(fact.id).memory_ids == (memory_id,)
    assert fact.id not in {record.id for record in service.records().exposable()}
    assert service.refresh_profile() == []
    historical = [record for record in service.records().records()
                  if record.record_type == "fact" and memory_id in record.memory_ids]
    assert [record.id for record in historical] == [fact.id]


def test_profile_accept_settles_the_fact_and_repeats_as_a_noop(service: AptuniService) -> None:
    memory_id = _memory(service)
    service.review_memory(memory_id, "pin")
    fact = service.profile_review_pending()[0]

    assert service.review_profile_fact(fact.id, "accept") == "accepted"
    assert service.review_profile_fact(fact.id, "accept") == "accepted"

    assert service.profile_review_pending() == []
    decisions = [event for event in service.records().records()
                 if event.record_type == "review_event" and event.target_id == fact.id]
    assert [event.decision for event in decisions] == ["accept"]


def test_profile_review_refuses_an_ordinary_declared_fact(service: AptuniService) -> None:
    fact = service.remember("Maintains Aptuni.", "projects")

    with pytest.raises(AptuniError) as error:
        service.review_profile_fact(fact.id, "accept")

    assert getattr(error.value, "code", None) == "fact_not_current"


def test_policy_promotion_event_cannot_target_an_ordinary_fact(service: AptuniService) -> None:
    fact = service.remember("Maintains Aptuni.", "projects")
    seq, records = service.snapshot()
    event = ReviewEvent(
        record_type="review_event", id=new_id("rev"), schema_version=2, recorded_at=utc_now(),
        target_id=fact.id, decision="promote", actor="policy_auto",
        action_digest=sha256_text(f"invalid|{fact.id}"), policy_epoch=records.policy().epoch,
        rationale_code="policy_invalid_target", nonce_id="policy_auto",
    )

    with pytest.raises(AptuniError) as error:
        service._commit([event], seq)

    assert error.value.code == "invariant_violation"


def test_promoted_fact_cannot_change_the_linked_memory_claim(service: AptuniService) -> None:
    memory_id = _memory(service)
    service.review_memory(memory_id, "pin")
    records = service.records().records()
    fact = next(record for record in records
                if record.record_type == "fact" and memory_id in record.memory_ids)
    forged = fact.model_copy(update={
        "statement": "A different and unsupported profile claim.",
        "module": "preferences",
        "predicate": "identity",
    })
    replaced = [forged if record.id == fact.id else record for record in records]

    with pytest.raises(InvariantError, match="does not exactly preserve"):
        RecordSet(replaced).validate()


def test_memory_correction_keeps_candidate_promotion_invariants_valid(service: AptuniService) -> None:
    memory_id = _memory(service)

    service.edit_memory(memory_id, "Prefers fully reproducible experiment pipelines.")

    assert service.doctor().ok is True


def test_duplicate_profile_promotion_event_is_rejected_incrementally(service: AptuniService) -> None:
    memory_id = _memory(service)
    service.review_memory(memory_id, "pin")
    seq, records = service.snapshot()
    original = next(record for record in records.records()
                    if record.record_type == "review_event" and record.target_id == memory_id
                    and record.decision == "promote")
    duplicate = original.model_copy(update={
        "id": new_id("rev"), "recorded_at": utc_now(),
        "action_digest": sha256_text(f"duplicate|{memory_id}"),
    })

    with pytest.raises(AptuniError) as error:
        service._commit([duplicate], seq)

    assert error.value.code == "invariant_violation"
    assert service.doctor().ok is True


def test_a_host_proposed_memory_cannot_become_profile_even_after_owner_pin(
    service: AptuniService,
) -> None:
    proposal = service.observe(
        "Host thinks the user likes pipelines.", "knowledge", origin="host", principal="p1",
    )
    preview = service.memory_preview(proposal.candidate_id)
    memory_id = service.decide_memory(proposal.candidate_id, "accept", preview.digest("accept"))
    assert memory_id is not None

    service.review_memory(memory_id, "pin")

    assert service.facts() == []


def test_an_unresolved_contradiction_blocks_a_pinned_memory(service: AptuniService) -> None:
    memory_id = _memory(service)
    proposal = service.observe(
        "Host proposes the opposite preference.", "knowledge", origin="host", principal="p1",
    )
    records = service.records()
    candidate = records.get(proposal.candidate_id)
    contradictory = candidate.model_copy(update={
        "id": new_id("cnd"), "contradicts": (memory_id,), "recorded_at": utc_now(),
    })
    seq, _ = service.snapshot()
    service._commit([contradictory], seq)

    service.review_memory(memory_id, "pin")

    assert service.facts() == []


def test_refresh_promotes_an_eligible_legacy_pin_once(service: AptuniService) -> None:
    memory_id = _memory(service)
    # Simulate a pin written by Slice C before ADR-0020 by committing only the user event.
    event = ReviewEvent(
        record_type="review_event", id=new_id("rev"), schema_version=2, recorded_at=utc_now(),
        target_id=memory_id, decision="pin", actor="user_cli",
        action_digest=sha256_text(f"review|pin|{memory_id}|1"), policy_epoch=1,
        rationale_code="owner_pin", nonce_id=f"review-{memory_id}",
    )
    seq, _ = service.snapshot()
    service._commit([event], seq)

    promoted = service.refresh_profile()

    assert len(promoted) == 1
    assert promoted[0].memory_ids == (memory_id,)
    assert service.refresh_profile() == []


def test_profile_cli_refresh_and_review_json(service: AptuniService, capsys: pytest.CaptureFixture[str]) -> None:
    memory_id = _memory(service)
    service.review_memory(memory_id, "pin")

    assert run(["profile", "refresh", "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["promoted"] == []
    assert run(["profile", "review", "list", "--json"], service) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["review_state"] == "auto_promoted_pending_review"
    assert run(["profile", "review", "accept", listed[0]["id"], "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["review_state"] == "accepted"

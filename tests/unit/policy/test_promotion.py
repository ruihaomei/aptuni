"""ADR-0018 §2 eligibility and §3 derived review state."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.policy.promotion import (
    DEFAULT_REVIEW_POLICY,
    evaluate_candidate,
    review_policy_of,
    review_state_of,
)


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    return service


def _candidate(service: AptuniService, statement: str, module: str = "knowledge", **kw: object):
    proposal = service.observe(statement, module, **kw)  # type: ignore[arg-type]
    records = service.records()
    return next(r for r in records.records()
                if r.record_type == "candidate_memory" and r.id == proposal.candidate_id), records


def _accept(service: AptuniService, candidate_id: str) -> str:
    preview = service.memory_preview(candidate_id)
    memory_id = service.decide_memory(candidate_id, "accept", preview.digest("accept"))
    assert memory_id is not None
    return memory_id


class TestEligibility:
    def test_an_owner_stated_cli_observation_is_promoted(self, service: AptuniService) -> None:
        candidate, records = _candidate(service, "Prefers reproducible experiment pipelines.")

        outcome = evaluate_candidate(candidate, records, DEFAULT_REVIEW_POLICY)

        assert outcome.action == "promote"
        assert outcome.reason == "owner_stated"

    def test_a_host_proposal_still_requires_confirmation(self, service: AptuniService) -> None:
        candidate, records = _candidate(
            service, "Host thinks the user likes pipelines.", origin="host", principal="p1",
        )

        outcome = evaluate_candidate(candidate, records, DEFAULT_REVIEW_POLICY)

        assert outcome.action == "confirm"
        assert outcome.reason == "not_owner_stated"

    def test_a_sensitive_module_requires_confirmation(self, service: AptuniService) -> None:
        candidate, records = _candidate(service, "Lives with two housemates.", "relationships")

        outcome = evaluate_candidate(candidate, records, DEFAULT_REVIEW_POLICY)

        assert outcome.action == "confirm"
        assert outcome.reason == "sensitive_module"

    def test_an_empty_sensitive_set_lets_a_sensitive_module_promote(self, service: AptuniService) -> None:
        candidate, records = _candidate(service, "Lives with two housemates.", "relationships")
        policy = DEFAULT_REVIEW_POLICY.model_copy(update={"sensitive_modules": ()})

        assert evaluate_candidate(candidate, records, policy).action == "promote"

    def test_a_contradiction_with_a_memory_in_force_requires_confirmation(
        self, service: AptuniService,
    ) -> None:
        first, _ = _candidate(service, "Prefers reproducible experiment pipelines.")
        memory_id = _accept(service, first.id)
        contradicting, records = _candidate(service, "Prefers ad hoc one-off scripts.")
        contradicting = contradicting.model_copy(update={"contradicts": (memory_id,)})

        outcome = evaluate_candidate(contradicting, records, DEFAULT_REVIEW_POLICY)

        assert outcome.action == "confirm"
        assert outcome.reason == "contradicts_record_in_force"

    def test_a_contradiction_with_a_revoked_memory_does_not_block(self, service: AptuniService) -> None:
        first, _ = _candidate(service, "Prefers reproducible experiment pipelines.")
        memory_id = _accept(service, first.id)
        preview = service.memory_forget_preview(memory_id)
        service.forget_memory_confirmed(memory_id, preview.digest())

        contradicting, records = _candidate(service, "Prefers ad hoc one-off scripts.")
        contradicting = contradicting.model_copy(update={"contradicts": (memory_id,)})

        assert evaluate_candidate(contradicting, records, DEFAULT_REVIEW_POLICY).action == "promote"

    def test_a_disabled_ingest_module_fails_closed(self, service: AptuniService) -> None:
        candidate, _ = _candidate(service, "Prefers reproducible experiment pipelines.")
        service.set_module("knowledge", ingest=False)

        outcome = evaluate_candidate(candidate, service.records(), DEFAULT_REVIEW_POLICY)

        assert outcome.action == "deny"
        assert outcome.reason == "module_ingest_disabled"

    def test_a_module_that_cannot_expose_is_not_promoted(self, service: AptuniService) -> None:
        candidate, _ = _candidate(service, "Prefers reproducible experiment pipelines.")
        service.set_module("knowledge", expose=False)

        outcome = evaluate_candidate(candidate, service.records(), DEFAULT_REVIEW_POLICY)

        assert outcome.action == "deny"
        assert outcome.reason == "module_expose_disabled"

    def test_promotion_can_be_switched_off_entirely(self, service: AptuniService) -> None:
        candidate, records = _candidate(service, "Prefers reproducible experiment pipelines.")
        policy = DEFAULT_REVIEW_POLICY.model_copy(update={"auto_promotion_enabled": False})

        outcome = evaluate_candidate(candidate, records, policy)

        assert outcome.action == "confirm"
        assert outcome.reason == "auto_promotion_disabled"


class TestReviewPolicyResolution:
    def test_defaults_apply_when_no_record_exists(self, service: AptuniService) -> None:
        resolved = review_policy_of(service.records())

        assert resolved == DEFAULT_REVIEW_POLICY
        assert resolved.pending_threshold == 10
        assert resolved.interval_days == 15
        assert resolved.snooze_days == 15
        assert resolved.auto_promotion_enabled is True


class TestDerivedReviewState:
    def test_a_manually_accepted_memory_is_accepted(self, service: AptuniService) -> None:
        candidate, _ = _candidate(service, "Prefers reproducible experiment pipelines.")
        memory_id = _accept(service, candidate.id)
        records = service.records()
        memory = records.get(memory_id)

        assert review_state_of(memory, records) == "accepted"

    def test_a_revoked_memory_is_revoked(self, service: AptuniService) -> None:
        candidate, _ = _candidate(service, "Prefers reproducible experiment pipelines.")
        memory_id = _accept(service, candidate.id)
        preview = service.memory_forget_preview(memory_id)
        service.forget_memory_confirmed(memory_id, preview.digest())
        records = service.records()

        assert review_state_of(records.get(memory_id), records) == "revoked"

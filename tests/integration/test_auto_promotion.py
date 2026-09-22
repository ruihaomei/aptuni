"""ADR-0018 slice C: the owner-facing automatic-promotion and retrospective-review loop."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.domain.temporal import utc_now


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    return service


class TestAutomaticPromotion:
    def test_an_owner_observation_becomes_an_active_memory_without_confirmation(
        self, service: AptuniService,
    ) -> None:
        proposal = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        assert proposal.memory_id is not None
        assert proposal.review_state == "auto_promoted_pending_review"
        assert service.pending_memories() == []
        memory = next(r for r in service.memories() if r.id == proposal.memory_id)
        assert memory.id in {r.id for r in service.records().exposable()}
        assert [hit.id for hit in service.search("reproducible pipelines")] == [memory.id]

    def test_promotion_is_one_commit_carrying_both_the_memory_and_its_event(
        self, service: AptuniService,
    ) -> None:
        before = service.status().seq

        proposal = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        assert service.status().seq == before + 1
        records = service.records()
        promote = [r for r in records.records() if r.record_type == "review_event"
                   and r.decision == "promote"]
        assert len(promote) == 1
        assert promote[0].actor == "policy_auto"
        assert promote[0].schema_version == 2
        assert promote[0].target_id == proposal.candidate_id

    def test_a_host_proposal_still_waits_for_confirmation(self, service: AptuniService) -> None:
        proposal = service.observe(
            "Host thinks the user likes pipelines.", "knowledge", origin="host", principal="p1",
        )

        assert proposal.memory_id is None
        assert {p.candidate_id for p in service.pending_memories()} == {proposal.candidate_id}
        assert service.memories() == []

    def test_a_sensitive_module_still_waits_for_confirmation(self, service: AptuniService) -> None:
        proposal = service.observe("Lives with two housemates.", "relationships")

        assert proposal.memory_id is None
        assert {p.candidate_id for p in service.pending_memories()} == {proposal.candidate_id}

    def test_a_module_that_cannot_expose_is_not_promoted_behind_the_owners_back(
        self, service: AptuniService,
    ) -> None:
        service.set_module("knowledge", expose=False)

        proposal = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        assert proposal.memory_id is None
        assert service.memories() == []

    def test_repeating_the_same_observation_promotes_once(self, service: AptuniService) -> None:
        first = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        second = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        assert second.candidate_id == first.candidate_id
        assert second.memory_id == first.memory_id
        assert len(service.memories()) == 1
        promote = [r for r in service.records().records()
                   if r.record_type == "review_event" and r.decision == "promote"]
        assert len(promote) == 1

    def test_switching_automatic_promotion_off_restores_the_confirmation_path(
        self, service: AptuniService,
    ) -> None:
        service.set_review_policy(auto_promotion_enabled=False)

        proposal = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        assert proposal.memory_id is None
        assert {p.candidate_id for p in service.pending_memories()} == {proposal.candidate_id}


class TestRetrospectiveReview:
    def test_accept_settles_a_pending_memory_and_is_idempotent(self, service: AptuniService) -> None:
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        assert [m.id for m in service.review_pending()] == [promoted.memory_id]

        service.review_memory(promoted.memory_id, "accept")
        service.review_memory(promoted.memory_id, "accept")

        assert service.review_pending() == []
        assert service.review_state(promoted.memory_id) == "accepted"
        events = [r for r in service.records().records()
                  if r.record_type == "review_event" and r.target_id == promoted.memory_id]
        assert len(events) == 1

    def test_reject_withdraws_the_memory_but_keeps_its_history(self, service: AptuniService) -> None:
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        service.review_memory(promoted.memory_id, "reject")

        assert service.memories() == []
        assert service.review_state(promoted.memory_id) == "revoked"
        assert service.records().get(promoted.memory_id).statement.startswith("Prefers")
        assert service.search("reproducible pipelines") == []

    def test_pin_settles_the_memory_and_keeps_it_active(self, service: AptuniService) -> None:
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        service.review_memory(promoted.memory_id, "pin")

        assert service.review_pending() == []
        assert service.review_state(promoted.memory_id) == "pinned"
        assert promoted.memory_id in {m.id for m in service.memories()}

    def test_edit_supersedes_with_a_correction_and_preserves_the_original(
        self, service: AptuniService,
    ) -> None:
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        corrected_id = service.edit_memory(promoted.memory_id, "Prefers fully reproducible pipelines.")

        records = service.records()
        corrected = records.get(corrected_id)
        assert corrected.change_kind == "correction"
        assert corrected.supersedes == (promoted.memory_id,)
        assert records.get(promoted.memory_id).statement == "Prefers reproducible experiment pipelines."
        assert corrected_id in {m.id for m in records.exposable()}
        assert promoted.memory_id not in {m.id for m in records.exposable()}
        assert service.review_pending() == []
        # `memory list` must agree with `exposable()`: the replaced original is not a current memory.
        assert [m.id for m in service.memories()] == [corrected_id]
        assert promoted.memory_id not in [hit.id for hit in service.search("reproducible")]

    def test_edit_and_reject_fail_closed_on_a_withdrawn_memory(self, service: AptuniService) -> None:
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        service.review_memory(promoted.memory_id, "reject")

        for call in (
            lambda: service.edit_memory(promoted.memory_id, "Something else."),
            lambda: service.review_memory(promoted.memory_id, "accept"),
        ):
            with pytest.raises(AptuniError) as error:
                call()
            assert error.value.code == "memory_not_current"

    def test_an_unknown_memory_is_refused(self, service: AptuniService) -> None:
        with pytest.raises(AptuniError) as error:
            service.review_memory("mem_00000000000000000000000000", "accept")
        assert error.value.code == "memory_not_current"


class TestReviewReminder:
    def test_no_reminder_below_the_threshold_and_before_the_interval(
        self, service: AptuniService,
    ) -> None:
        service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        reminder = service.review_reminder()

        assert reminder.pending == 1
        assert reminder.due is False

    def test_the_threshold_makes_a_reminder_due(self, service: AptuniService) -> None:
        service.set_review_policy(pending_threshold=3)
        for index in range(3):
            service.observe(f"Prefers approach number {index}.", "knowledge")

        reminder = service.review_reminder()

        assert reminder.pending == 3
        assert reminder.due is True
        assert reminder.reason == "threshold"

    def test_the_interval_makes_a_reminder_due_even_below_the_threshold(
        self, service: AptuniService,
    ) -> None:
        service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        past = utc_now() - timedelta(days=16)

        reminder = service.review_reminder(now=utc_now(), waiting_since=past)

        assert reminder.due is True
        assert reminder.reason == "interval"

    def test_a_snooze_defers_the_reminder_for_the_configured_days(
        self, service: AptuniService,
    ) -> None:
        service.set_review_policy(pending_threshold=1)
        service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        assert service.review_reminder().due is True

        service.snooze_review()

        assert service.review_reminder().due is False
        later = utc_now() + timedelta(days=16)
        assert service.review_reminder(now=later).due is True

    def test_pinned_memories_are_never_counted(self, service: AptuniService) -> None:
        first = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        service.observe("Prefers written design notes.", "knowledge")
        service.review_memory(first.memory_id, "pin")

        assert service.review_reminder().pending == 1


class TestReviewFindings:
    """Regressions for the blocking findings in Review 56."""

    def test_an_edited_memory_is_not_exported_beside_its_correction(
        self, service: AptuniService, tmp_path: Path,
    ) -> None:
        """B1: export had no supersession filter, so the corrected-away text stayed visible."""
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        corrected_id = service.edit_memory(promoted.memory_id, "Prefers fully reproducible pipelines.")

        report = service.export(tmp_path / "export")
        text = "\n".join(path.read_text(encoding="utf-8")
                         for path in (tmp_path / "export").rglob("*") if path.is_file())

        assert report.memories == 1
        assert corrected_id in text
        assert promoted.memory_id not in text
        assert "Prefers reproducible experiment pipelines." not in text

    def test_a_repeated_decision_on_a_pinned_memory_adds_no_second_event(
        self, service: AptuniService,
    ) -> None:
        """B2: the no-op guard compared a collapsed state, so `pin` then `accept` kept appending."""
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        service.review_memory(promoted.memory_id, "pin")

        for _ in range(3):
            assert service.review_memory(promoted.memory_id, "accept") == "pinned"

        events = [r for r in service.records().records()
                  if r.record_type == "review_event" and r.target_id == promoted.memory_id]
        # ADR-0020 adds the policy `promote` event targeting the pinned Memory; repeats still add
        # only one owner `accept` event.
        assert [e.decision for e in events] == ["pin", "promote", "accept"]
        assert service.review_state(promoted.memory_id) == "pinned"

    def test_a_naive_or_hostile_reminder_marker_does_not_crash_or_silence_forever(
        self, service: AptuniService,
    ) -> None:
        """B3: a naive timestamp parsed fine and then blew up on comparison."""
        service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        marker = service.workspace.state_dir / "review" / "reminder.json"
        marker.parent.mkdir(parents=True, exist_ok=True)

        marker.write_text('{"suppressed_until": "2030-01-01T00:00:00"}\n', encoding="utf-8")
        assert service.review_reminder().pending == 1  # a naive marker is simply unreadable

        marker.write_text('{"suppressed_until": "2099-01-01T00:00:00+00:00"}\n', encoding="utf-8")
        assert service.review_reminder().due is False
        service.clear_review_snooze()
        assert service.review_reminder().reason != "snoozed"

    def test_edit_respects_a_module_that_stopped_accepting_information(
        self, service: AptuniService,
    ) -> None:
        """B6: `edit` creates content, so it must honour `ingest_enabled` like every other writer."""
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        service.set_module("knowledge", ingest=False)

        with pytest.raises(AptuniError) as error:
            service.edit_memory(promoted.memory_id, "Rewritten while ingest is off.")

        assert error.value.code == "module_ingest_disabled"
        assert [m.statement for m in service.memories()] == [
            "Prefers reproducible experiment pipelines."]

    def test_editing_an_already_superseded_memory_says_so_plainly(
        self, service: AptuniService,
    ) -> None:
        """N3: this surfaced a raw invariant message and a record id to the owner."""
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        service.edit_memory(promoted.memory_id, "First correction.")

        with pytest.raises(AptuniError) as error:
            service.edit_memory(promoted.memory_id, "Second correction.")

        assert error.value.code == "memory_not_current"
        assert promoted.memory_id not in error.value.message

    def test_the_memory_provider_rebuild_skips_a_superseded_memory(
        self, service: AptuniService,
    ) -> None:
        """N2: the projection kept text the owner had corrected away."""
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        corrected_id = service.edit_memory(promoted.memory_id, "Prefers fully reproducible pipelines.")
        projected: list[str] = []

        class CaptureClient:
            def __init__(self, root: Path) -> None:
                self.rows: list[dict[str, object]] = []

            def add(self, text: str, *, user_id: str, metadata: dict[str, object], infer: bool) -> object:
                del user_id, infer
                projected.append(str(metadata["aptuni_canonical_id"]))
                self.rows.append({"id": f"p{len(self.rows)}", "memory": text, "metadata": metadata})
                return {"results": [self.rows[-1]]}

            def get_all(self, *, filters: dict[str, str], top_k: int) -> object:
                del filters, top_k
                return {"results": self.rows}

            def search(self, query: str, *, user_id: str, limit: int) -> object:
                del query, user_id, limit
                return {"results": []}

            def close(self) -> None:
                return None

        service.rebuild_memory_provider(CaptureClient)

        assert projected == [corrected_id]

    def test_a_repeated_observation_reports_the_current_memory_not_the_replaced_one(
        self, service: AptuniService,
    ) -> None:
        """N1: `_proposal_for` took the first memory sharing the candidate id."""
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        corrected_id = service.edit_memory(promoted.memory_id, "Prefers fully reproducible pipelines.")

        again = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        assert again.memory_id == corrected_id
        assert again.review_state == "accepted"

    def test_a_host_proposal_never_reaches_the_promotion_evaluator(
        self, service: AptuniService, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """N5: make the ADR-0018 §8 guarantee structural rather than a property of two fields."""
        import aptuni.application.memory_commands as commands

        def forbidden(*_args: object, **_kwargs: object) -> list[object]:
            raise AssertionError("a host proposal must never be evaluated for promotion")

        monkeypatch.setattr(commands, "promotion_records", forbidden)
        proposal = service.observe("Host proposal.", "knowledge", origin="host", principal="p1")

        assert proposal.memory_id is None

    def test_the_context_api_marks_an_unreviewed_memory(self, service: AptuniService) -> None:
        """B5: an agent could not tell an auto-promoted memory from a confirmed one."""
        promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")

        response = service.context("pipelines", budget=4000, audience="owner_cli")
        unit = next(u for u in response.units if u.canonical_id == promoted.memory_id)

        assert unit.review_state == "auto_promoted_pending_review"
        service.review_memory(promoted.memory_id, "accept")
        response = service.context("pipelines", budget=4000, audience="owner_cli")
        assert next(u for u in response.units
                    if u.canonical_id == promoted.memory_id).review_state == "accepted"

    def test_status_and_doctor_mention_a_due_review_queue(
        self, service: AptuniService, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """B4: ADR-0018 §6 puts the reminder where the owner already looks."""
        from aptuni.cli.main import run

        service.set_review_policy(pending_threshold=1)
        service.observe("Prefers reproducible experiment pipelines.", "knowledge")
        capsys.readouterr()

        assert run(["status"], service) == 0
        status_out = capsys.readouterr().out
        assert run(["doctor"], service) == 0
        doctor_out = capsys.readouterr().out

        for printed in (status_out, doctor_out):
            assert "aptuni memory review list" in printed
        assert json.loads(_json_of(service, capsys))["review"]["due"] is True

        service.snooze_review()
        capsys.readouterr()
        assert run(["status"], service) == 0
        assert "aptuni memory review list" not in capsys.readouterr().out


def _json_of(service: AptuniService, capsys: pytest.CaptureFixture[str]) -> str:
    from aptuni.cli.main import run

    capsys.readouterr()
    assert run(["status", "--json"], service) == 0
    return capsys.readouterr().out

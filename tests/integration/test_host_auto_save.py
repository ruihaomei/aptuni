"""ADR-0018 2026-10-01 amendment: the owner may let Agent proposals save without confirmation."""

from __future__ import annotations

import json
from pathlib import Path

import anyio
import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.cli.main import main
from aptuni.domain.records import canonical_json
from aptuni.mcp.server import create_server


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    app = AptuniService(Workspace(tmp_path / "state"))
    app.init(tmp_path / "Aptuni")
    return app


def _host(service: AptuniService, statement: str, module: str = "goals"):
    return service.observe(statement, module, origin="host", principal="claude-adapter")


def test_host_proposals_wait_for_confirmation_by_default(service: AptuniService) -> None:
    proposal = _host(service, "Goal: finish the graduate applications by November.")
    assert proposal.memory_id is None
    assert len(service.pending_memories()) == 1


def test_owner_opt_in_saves_host_proposals_as_reviewable_memories(service: AptuniService) -> None:
    service.set_review_policy(auto_promote_host_proposals=True)
    proposal = _host(service, "Goal: finish the graduate applications by November.")

    assert proposal.memory_id is not None
    assert proposal.review_state == "auto_promoted_pending_review"
    records = service.records()
    assert proposal.memory_id in {record.id for record in records.exposable()}
    event = next(r for r in records.records() if r.record_type == "review_event"
                 and r.target_id == proposal.candidate_id and r.decision == "promote")
    assert event.actor == "policy_auto" and event.rationale_code == "policy_host_proposal_allowed"
    assert [memory.id for memory in service.review_pending()] == [proposal.memory_id]
    # A host-originated memory never becomes a Profile Fact (ADR-0020 is unchanged).
    assert not [r for r in records.records() if r.record_type == "fact" and r.type == "profile.promoted_memory"]


def test_opt_in_still_asks_for_sensitive_modules(service: AptuniService) -> None:
    service.set_review_policy(auto_promote_host_proposals=True)
    proposal = _host(service, "Lives in Hong Kong.", module="identity")
    assert proposal.memory_id is None


def test_policy_record_only_uses_schema_v2_when_opted_in(service: AptuniService) -> None:
    off = service.set_review_policy(pending_threshold=12)
    assert off.schema_version == 1
    assert "auto_promote_host_proposals" not in json.loads(canonical_json(off))
    on = service.set_review_policy(auto_promote_host_proposals=True)
    assert on.schema_version == 2
    assert json.loads(canonical_json(on))["auto_promote_host_proposals"] is True
    assert service.set_review_policy(auto_promote_host_proposals=False).schema_version == 1


def test_mcp_reports_a_saved_proposal(service: AptuniService) -> None:
    service.set_review_policy(auto_promote_host_proposals=True)
    access = HostContextAccess("claude-adapter", frozenset({"context.read", "memory.propose"}),
                               frozenset({"goals"}), "remote_unknown", True)
    server = create_server(service, access)

    async def exercise() -> None:
        result = await server.call_tool("aptuni_propose_memory", {"statement": "Goal: apply", "module": "goals"})
        assert result.structured_content["status"] == "saved_pending_owner_review"
        assert result.structured_content["memory_id"].startswith("mem_")

    anyio.run(exercise)


def test_cli_turns_host_auto_save_on_and_reports_it(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("APTUNI_STATE_DIR", str(service.workspace.state_dir))
    assert main(["memory", "review", "policy", "--host-proposals", "on"]) == 0
    assert "Agent proposals: saved automatically" in capsys.readouterr().out
    assert main(["memory", "review", "policy", "--auto-promotion", "off"]) == 0
    assert "Agent proposals: wait for your confirmation" in capsys.readouterr().out
    assert service.review_policy().auto_promote_host_proposals is True


def test_auto_saved_memories_awaiting_review_count_toward_the_per_agent_cap(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aptuni.application import memory_commands

    monkeypatch.setattr(memory_commands, "MAX_PENDING_PER_ORIGIN", 3)
    service.set_review_policy(auto_promote_host_proposals=True)
    for index in range(3):
        assert _host(service, f"Goal number {index}.").memory_id is not None
    with pytest.raises(AptuniError) as refused:
        _host(service, "Goal number 4.")
    assert refused.value.code == "memory_queue_full"


def test_mcp_reports_saved_only_for_a_proposal_it_auto_saved(service: AptuniService) -> None:
    access = HostContextAccess("claude-adapter", frozenset({"context.read", "memory.propose"}),
                               frozenset({"goals"}), "remote_unknown", True)
    server = create_server(service, access)

    async def exercise() -> None:
        first = await server.call_tool("aptuni_propose_memory", {"statement": "Goal: apply", "module": "goals"})
        assert first.structured_content["status"] == "pending_owner_review"
        candidate_id = first.structured_content["candidate_id"]
        service.decide_memory(candidate_id, "accept", service.memory_preview(candidate_id).digest("accept"))
        again = await server.call_tool("aptuni_propose_memory", {"statement": "Goal: apply", "module": "goals"})
        assert again.structured_content["status"] == "pending_owner_review"
        assert "memory_id" not in again.structured_content

    anyio.run(exercise)

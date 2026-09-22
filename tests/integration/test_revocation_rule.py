"""ADR-0018 §4: a Memory is revoked by `revoke`/`reject`, never by any review event at all.

Before ADR-0018 the only event that could target a memory id was a revocation, so "any event"
and "revoke or reject" agreed on every ledger the product could produce. ADR-0018 adds `accept`
and `pin` events on memory ids, which makes the old rule silently hide memories from the Mem0
projection, the hybrid semantic lane, `memories()` and the forget path. These tests pin the
corrected rule at every consumer *before* those events exist, so the split is provably
behaviour-preserving when it lands.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import pytest

from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id
from aptuni.domain.records import ReviewEvent
from aptuni.domain.temporal import utc_now
from aptuni.retrieval.sqlite import SearchRow


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    return service


def _accepted_memory(service: AptuniService, statement: str, module: str = "knowledge") -> str:
    proposal = service.observe(statement, module)
    preview = service.memory_preview(proposal.candidate_id)
    memory_id = service.decide_memory(proposal.candidate_id, "accept", preview.digest("accept"))
    assert memory_id is not None
    return memory_id


def _append_event(service: AptuniService, target_id: str, decision: str) -> None:
    """Append a raw ReviewEvent so the derivation can be tested without the confirmation path."""
    seq, records = service.snapshot()
    event = ReviewEvent(
        record_type="review_event", id=new_id("rev"), schema_version=1, recorded_at=utc_now(),
        target_id=target_id, decision=decision, actor="user_cli",  # type: ignore[arg-type]
        action_digest="sha256:" + "0" * 64, policy_epoch=records.policy().epoch,  # type: ignore[union-attr]
        rationale_code=f"owner_{decision}", nonce_id="test-nonce",
    )
    service._commit([event], seq)


def _visible_everywhere(service: AptuniService, memory_id: str, tmp_path: Path) -> dict[str, bool]:
    """Ask every consumer of the revocation rule whether it can still see this memory."""
    records = service.records()
    rebuilt: list[Any] = []

    class CaptureClient:
        def __init__(self, root: Path) -> None:
            self.rows: list[dict[str, Any]] = []

        def add(self, text: str, *, user_id: str, metadata: dict[str, Any], infer: bool) -> Any:
            del text, user_id, infer
            rebuilt.append(metadata["aptuni_canonical_id"])
            self.rows.append({"id": f"p{len(self.rows)}", "memory": text_of(metadata), "metadata": metadata})
            return {"results": [self.rows[-1]]}

        def get_all(self, *, filters: dict[str, str], top_k: int) -> Any:
            del filters, top_k
            return {"results": self.rows}

        def search(self, query: str, *, user_id: str, limit: int) -> Any:
            del query, user_id, limit
            return {"results": []}

        def close(self) -> None:
            return None

    def text_of(metadata: dict[str, Any]) -> str:
        return next(r.statement for r in records.records()
                    if r.id == metadata["aptuni_canonical_id"])

    service.rebuild_memory_provider(CaptureClient)
    return {
        "memories": memory_id in {r.id for r in service.memories()},
        "exposable": memory_id in {r.id for r in records.exposable()},
        "mem0_rebuild": memory_id in rebuilt,
        "export": memory_id in _exported_memory_ids(service, tmp_path),
    }


_EXPORT_COUNTER = itertools.count()


def _exported_memory_ids(service: AptuniService, tmp_path: Path) -> set[str]:
    target = tmp_path / f"export-{next(_EXPORT_COUNTER)}"
    service.export(target)
    text = "\n".join(path.read_text(encoding="utf-8") for path in target.rglob("*") if path.is_file())
    return {record.id for record in service.records().records()
            if record.record_type == "memory" and record.id in text}


def test_an_accept_event_on_a_memory_does_not_hide_it_anywhere(
    service: AptuniService, tmp_path: Path,
) -> None:
    """The ADR-0018 §4 counterexample: the old 'any event' rule fails every one of these."""
    memory_id = _accepted_memory(service, "Prefers reproducible experiment pipelines.")
    before = _visible_everywhere(service, memory_id, tmp_path)
    assert all(before.values()), before

    _append_event(service, memory_id, "accept")

    after = _visible_everywhere(service, memory_id, tmp_path)
    assert after == before, f"an accept event changed visibility: {before} -> {after}"


def test_a_revoke_event_on_a_memory_hides_it_everywhere(
    service: AptuniService, tmp_path: Path,
) -> None:
    memory_id = _accepted_memory(service, "Prefers reproducible experiment pipelines.")
    assert all(_visible_everywhere(service, memory_id, tmp_path).values())

    _append_event(service, memory_id, "revoke")

    assert not any(_visible_everywhere(service, memory_id, tmp_path).values())


def test_a_reject_event_on_a_memory_hides_it_everywhere(
    service: AptuniService, tmp_path: Path,
) -> None:
    """`reject` targets a candidate today, but the rule must name it or a future reject is a no-op."""
    memory_id = _accepted_memory(service, "Prefers reproducible experiment pipelines.")
    assert all(_visible_everywhere(service, memory_id, tmp_path).values())

    _append_event(service, memory_id, "reject")

    assert not any(_visible_everywhere(service, memory_id, tmp_path).values())


def test_the_hybrid_semantic_lane_uses_the_same_revoked_set_as_the_service(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-0004's semantic lane must not derive revocation independently and drift (plan case 5)."""
    kept = _accepted_memory(service, "Prefers reproducible experiment pipelines.")
    revoked = _accepted_memory(service, "Prefers ad hoc one-off scripts.", "preferences")
    _append_event(service, kept, "accept")
    _append_event(service, revoked, "revoke")

    monkeypatch.setattr(
        AptuniService,
        "_semantic_search",
        lambda *_a, **_k: [SearchRow(kept, 1.0), SearchRow(revoked, 0.9)],
    )
    hits = {hit.id for hit in service.search("unmatched semantic query", hybrid=True)}

    assert kept in hits, "an accepted memory must stay in the semantic lane"
    assert revoked not in hits
    assert {r.id for r in service.memories()} & {kept, revoked} == {kept}


def test_candidate_decisions_keep_their_current_meaning(service: AptuniService) -> None:
    """Splitting the rule must not change what 'this candidate is still pending' means."""
    first = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
    second = service.observe("Prefers written design notes.", "knowledge")
    assert {p.candidate_id for p in service.pending_memories()} == {first.candidate_id, second.candidate_id}

    preview = service.memory_preview(first.candidate_id)
    service.decide_memory(first.candidate_id, "accept", preview.digest("accept"))
    rejected = service.memory_preview(second.candidate_id)
    service.decide_memory(second.candidate_id, "reject", rejected.digest("reject"))

    assert service.pending_memories() == []

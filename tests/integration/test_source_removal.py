"""The owner can stop using an approved source (ADR-0027, Beta Day 0 2026-09-29).

``aptuni source remove SOURCE_ID`` previews, then on a typed APPLY records one owner ``revoke``
review event for the source and retracts every current evidence item it contributed. History is
kept; agents see none of it; the source cannot be synced again; setup re-approves the location as a
new source; and ADR-0010 purge still deletes everything including the removal event.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.domain.ids import new_id
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import ReviewEvent
from aptuni.domain.temporal import utc_now


def _setup(tmp_path: Path) -> tuple[AptuniService, str, Path]:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    root = tmp_path / "notes"
    root.mkdir()
    (root / "a.md").write_text("removal marker alpha", encoding="utf-8")
    (root / "b.md").write_text("removal marker beta", encoding="utf-8")
    source = service.add_folder_source(root, ("knowledge",), "notes")
    service.sync(source.id)
    return service, source.id, root


def _exposed_from(service: AptuniService, source_id: str) -> list[object]:
    return [record for record in service.exposable()
            if record.record_type == "evidence" and record.provenance.source_id == source_id]


def test_the_preview_says_what_will_happen_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, source_id, root = _setup(tmp_path)
    before = service.status().seq
    monkeypatch.setattr("builtins.input", lambda *args: "no")

    assert run(["source", "remove", source_id, "--lang", "zh-CN"], service) == 1

    out = capsys.readouterr().out
    assert str(root) in out and "2 条证据" in out and "privacy purge preview" in out
    assert service.status().seq == before and [s.id for s in service.sources()] == [source_id]


def test_apply_revokes_the_source_and_retracts_its_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, source_id, _ = _setup(tmp_path)
    assert len(_exposed_from(service, source_id)) == 2
    monkeypatch.setattr("builtins.input", lambda *args: "APPLY")

    assert run(["source", "remove", source_id, "--lang", "en"], service) == 0

    assert "Removed" in capsys.readouterr().out
    assert service.sources() == []
    assert service.evidence(source_id) == []
    assert _exposed_from(service, source_id) == []
    assert service.search("removal marker") == [] or all(
        "removal marker" not in str(hit) for hit in service.search("removal marker"))
    records = service.records().records()
    (event,) = [r for r in records if r.record_type == "review_event" and r.target_id == source_id]
    assert (event.decision, event.actor, event.rationale_code) == ("revoke", "user_cli", "source_removed")
    assert sum(r.record_type == "evidence" and r.change_kind == "retraction" for r in records) == 2
    assert any(r.record_type == "source_config" and r.id == source_id for r in records), "history is kept"
    assert service.doctor().ok


def test_a_preview_made_stale_by_a_sync_is_refused(tmp_path: Path) -> None:
    service, source_id, root = _setup(tmp_path)
    preview = service.source_removal_preview(source_id)
    (root / "c.md").write_text("added after preview", encoding="utf-8")
    service.sync(source_id)

    with pytest.raises(AptuniError) as stale:
        service.remove_source(source_id, preview.digest)

    assert stale.value.code == "confirmation_stale"
    assert [s.id for s in service.sources()] == [source_id]


def test_a_removed_source_cannot_be_synced_or_removed_again(tmp_path: Path) -> None:
    service, source_id, _ = _setup(tmp_path)
    service.remove_source(source_id, service.source_removal_preview(source_id).digest)

    with pytest.raises(AptuniError) as sync:
        service.sync(source_id)
    with pytest.raises(AptuniError) as again:
        service.source_removal_preview(source_id)

    assert sync.value.code == "source_removed" and again.value.code == "source_removed"


def test_the_same_location_can_be_approved_again_as_a_new_source(tmp_path: Path) -> None:
    service, source_id, root = _setup(tmp_path)
    service.remove_source(source_id, service.source_removal_preview(source_id).digest)

    fresh = service.add_folder_source(root, ("knowledge",), "notes")
    service.sync(fresh.id)

    assert fresh.id != source_id and [s.id for s in service.sources()] == [fresh.id]
    assert len(_exposed_from(service, fresh.id)) == 2
    assert service.doctor().ok


def test_purge_still_deletes_a_removed_source_with_its_removal_event(tmp_path: Path) -> None:
    service, source_id, _ = _setup(tmp_path)
    service.remove_source(source_id, service.source_removal_preview(source_id).digest)

    preview = service.privacy_purge_preview((source_id,))
    service.confirm_privacy_purge(preview.action_id, preview.digest)

    assert not any(getattr(r, "target_id", None) == source_id or r.id == source_id
                   for r in service.records().records())
    assert service.doctor().ok


def test_invariants_reject_a_malformed_source_revocation_and_surviving_evidence(tmp_path: Path) -> None:
    service, source_id, _ = _setup(tmp_path)
    records = service.records().records()
    base = {"record_type": "review_event", "schema_version": 1, "recorded_at": utc_now(),
            "target_id": source_id, "actor": "user_cli", "action_digest": "sha256:" + "0" * 64,
            "policy_epoch": 1, "nonce_id": "n"}

    accept = ReviewEvent(**base, id=new_id("rev"), decision="accept", rationale_code="source_removed")
    with pytest.raises(InvariantError):
        RecordSet([*records, accept]).validate()

    bare = ReviewEvent(**base, id=new_id("rev"), decision="revoke", rationale_code="source_removed")
    with pytest.raises(InvariantError, match="still has current evidence"):
        RecordSet([*records, bare]).validate()


def test_owner_review_counts_ignore_source_removals(tmp_path: Path) -> None:
    from aptuni.application.evaluation import owner_review_decisions

    service, source_id, _ = _setup(tmp_path)
    before = owner_review_decisions(service.records())
    service.remove_source(source_id, service.source_removal_preview(source_id).digest)
    assert owner_review_decisions(service.records()) == before


def test_remove_repairs_evidence_an_older_build_synced_after_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review 80 B2: 0.2.0b3 does not honour a removal and can sync the source again."""
    service, source_id, root = _setup(tmp_path)
    service.remove_source(source_id, service.source_removal_preview(source_id).digest)
    with monkeypatch.context() as older_build:
        older_build.setattr(RecordSet, "removed_source_ids", lambda _self: set())
        older_build.setattr(RecordSet, "_check_source_removal", lambda _self, _checked: None)
        (root / "a.md").write_text("edited by an older build", encoding="utf-8")
        service.sync(source_id)
    assert not service.doctor().ok, "the surviving evidence breaks the removal invariant"

    preview = service.source_removal_preview(source_id)
    assert len(preview.evidence_ids) >= 1
    service.remove_source(source_id, preview.digest)

    assert service.doctor().ok
    assert _exposed_from(service, source_id) == []
    events = [r for r in service.records().records() if r.record_type == "review_event" and r.target_id == source_id]
    assert len(events) == 1, "a repair writes only retractions, never a second removal event"
    with pytest.raises(AptuniError) as done:
        service.source_removal_preview(source_id)
    assert done.value.code == "source_removed"

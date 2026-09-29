"""ADR-0028 amendment (Review 82 B4): an owner-confirmed authority upgrade for an existing source."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run as cli_run
from marginnote_fixture import base_cards, build_store

STUDIED = "knowledge.studied"


def _released_vault(tmp_path: Path) -> tuple[AptuniService, str, Path]:
    """The User #1 state: a MarginNote source approved with empty authority and exposure Evidence."""
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", base_cards())
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes")
    service.sync(source.id)
    return service, source.id, store


def test_the_released_empty_authority_state_forms_no_profile(tmp_path: Path) -> None:
    service, source_id, _ = _released_vault(tmp_path)

    assert service.refresh_profile() == []
    assert service.sync(source_id).profile_written == 0
    assert service.facts() == []


def test_preview_writes_nothing_and_names_the_exact_effect(tmp_path: Path) -> None:
    service, source_id, _ = _released_vault(tmp_path)
    before = len(service.records())

    preview = service.source_authority_preview(source_id, STUDIED)

    assert preview.source.id == source_id
    assert preview.dimension == STUDIED
    assert len(preview.evidence_ids) == 5
    assert len(service.records()) == before


def test_confirmed_upgrade_rederives_evidence_and_forms_profile_preserving_lineage(tmp_path: Path) -> None:
    service, source_id, _ = _released_vault(tmp_path)
    old = {item.id: item for item in service.records().current_evidence(source_id)}
    preview = service.source_authority_preview(source_id, STUDIED)

    result = service.grant_source_authority(source_id, STUDIED, preview.digest)

    assert result.evidence_written == 5 and result.profile_written == 5
    records = service.records()
    current = records.current_evidence(source_id)
    assert all(item.signals == ("studied",) and item.change_kind == "correction" for item in current)
    assert {item.supersedes[0] for item in current} == set(old)
    assert all(old_id in records.ids() for old_id in old), "history is preserved"
    facts = service.facts()
    assert len(facts) == 5 and {fact.predicate for fact in facts} == {"studied"}
    assert {fact.evidence_ids[0] for fact in facts} == {item.id for item in current}
    assert next(s for s in service.sources() if s.id == source_id).authority.primary_for == (STUDIED,)
    assert service.doctor().ok


def test_upgrade_is_idempotent_stale_safe_and_later_syncs_stay_studied(tmp_path: Path) -> None:
    service, source_id, store = _released_vault(tmp_path)
    stale = service.source_authority_preview(source_id, STUDIED)
    cards = base_cards()
    cards[3].title = "Gradient boosting"
    build_store(store, cards)
    service.sync(source_id)

    with pytest.raises(AptuniError) as refused:
        service.grant_source_authority(source_id, STUDIED, stale.digest)
    assert refused.value.code == "confirmation_stale"
    assert service.facts() == []

    fresh = service.source_authority_preview(source_id, STUDIED)
    service.grant_source_authority(source_id, STUDIED, fresh.digest)
    with pytest.raises(AptuniError) as again:
        service.source_authority_preview(source_id, STUDIED)
    assert again.value.code == "source_authority_present"

    cards[3].title = "AdaBoost"
    build_store(store, cards)
    report = service.sync(source_id)
    assert report.evidence_written >= 1 and report.profile_written == report.evidence_written
    assert all(item.signals == ("studied",) for item in service.records().current_evidence(source_id)
               if item.change_kind != "retraction")
    assert service.sync(source_id).profile_written == 0
    assert service.doctor().ok


def test_unsupported_or_removed_sources_are_refused(tmp_path: Path) -> None:
    service, source_id, _ = _released_vault(tmp_path)
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "a.md").write_text("Survival analysis.", encoding="utf-8")
    other = service.add_folder_source(folder, ("knowledge",), "study-notes")

    with pytest.raises(AptuniError) as unsupported:
        service.source_authority_preview(other.id, STUDIED)
    assert unsupported.value.code == "source_authority_unsupported"
    with pytest.raises(AptuniError) as wrong_dimension:
        service.source_authority_preview(source_id, "knowledge.demonstrated")
    assert wrong_dimension.value.code == "source_authority_unsupported"

    removal = service.source_removal_preview(source_id)
    service.remove_source(source_id, removal.digest)
    with pytest.raises(AptuniError) as removed:
        service.source_authority_preview(source_id, STUDIED)
    assert removed.value.code == "source_removed"


def test_cli_cancellation_leaves_the_source_exposure_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    service, source_id, _ = _released_vault(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "no")

    assert cli_run(["source", "authorize", source_id, "--grant", STUDIED, "--lang", "en"], service) == 1

    out = capsys.readouterr().out
    assert "5" in out and "Profile" in out
    assert service.facts() == []
    assert next(s for s in service.sources() if s.id == source_id).authority.primary_for == ()


def test_cli_apply_upgrades_in_chinese(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    service, source_id, _ = _released_vault(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "APPLY")

    assert cli_run(["source", "authorize", source_id, "--grant", STUDIED, "--lang", "zh-CN"], service) == 0

    out = capsys.readouterr().out
    assert "Profile" in out and "证据" in out
    assert len(service.facts()) == 5


def test_purging_an_upgraded_source_deletes_its_grant_evidence_and_profile(tmp_path: Path) -> None:
    service, source_id, _ = _released_vault(tmp_path)
    preview = service.source_authority_preview(source_id, STUDIED)
    service.grant_source_authority(source_id, STUDIED, preview.digest)
    assert service.facts()

    purge = service.privacy_purge_preview((source_id,))
    service.confirm_privacy_purge(purge.action_id, purge.digest)

    records = service.records()
    assert service.facts() == []
    assert not [record for record in records.records()
                if getattr(record, "target_id", None) == source_id
                or getattr(getattr(record, "provenance", None), "source_id", None) == source_id]
    assert service.doctor().ok


def test_the_expose_switch_hides_evidence_derived_profile_from_hosts(tmp_path: Path) -> None:
    service, source_id, _ = _released_vault(tmp_path)
    preview = service.source_authority_preview(source_id, STUDIED)
    service.grant_source_authority(source_id, STUDIED, preview.digest)
    fact_ids = {fact.id for fact in service.facts()}
    assert fact_ids <= {record.id for record in service.exposable()}

    service.set_module("knowledge", expose=False)

    assert not fact_ids & {record.id for record in service.exposable()}


def test_a_topic_that_reads_as_a_proficiency_claim_stays_evidence_and_never_blocks_the_batch(
    tmp_path: Path,
) -> None:
    """User #1 (0.2.0b5): two of 26,417 notes had 'mastery'/'proficient' in their titles; the upgrade
    was refused as a whole because 'Studied … mastery …' trips the no-proficiency guard."""
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    cards = base_cards()
    cards[4].title = "Mastery learning"
    cards[5].title = "Proficient readers"
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", cards)
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes")
    service.sync(source.id)
    preview = service.source_authority_preview(source.id, STUDIED)

    result = service.grant_source_authority(source.id, STUDIED, preview.digest)

    assert result.evidence_written == 5 and result.profile_written == 3
    subjects = {fact.subject for fact in service.facts()}
    assert not any("Mastery" in subject or "Proficient" in subject for subject in subjects)
    assert any("Mastery" in item.subject for item in service.evidence(source.id)), "still reference Evidence"
    assert service.doctor().ok

    fresh = AptuniService(Workspace(tmp_path / "fresh-state"))
    fresh.init(tmp_path / "fresh-vault")
    authoritative = fresh.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes",
                                                primary_for=(STUDIED,))
    assert fresh.sync(authoritative.id).profile_written == 3

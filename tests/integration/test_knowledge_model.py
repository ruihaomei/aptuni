"""ADR-0029: item-level classification, the authority ceiling and the owner-confirmed migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.source_authority import _rederived
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run as cli_run
from aptuni.domain.invariants import RecordSet
from aptuni.policy.evidence_profile import derive_evidence_profile
from marginnote_fixture import base_cards, build_store

STUDIED = "knowledge.studied"


def _vault(tmp_path: Path, *, authority: tuple[str, ...] = (STUDIED,), cards=None):  # type: ignore[no-untyped-def]
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", cards or base_cards())
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes", primary_for=authority)
    service.sync(source.id)
    return service, source.id, store


def _signals(service: AptuniService, source_id: str) -> dict[str, tuple[str, ...]]:
    return {item.subject.split(" › ")[-1]: item.signals
            for item in service.records().current_evidence(source_id) if item.change_kind != "retraction"}


def _exposed_facts(service: AptuniService) -> set[str]:
    return {r.statement for r in service.exposable() if r.record_type == "fact"}


def test_each_card_is_classified_on_its_own_under_the_ceiling(tmp_path: Path) -> None:
    service, source_id, _ = _vault(tmp_path)

    assert _signals(service, source_id) == {
        "Ensemble methods": ("studied",),  # organises sub-concepts
        "Random forest": ("studied",),  # children, merged excerpt and an annotation
        "Boosting": ("exposure",), "Bagging": ("exposure",), "Out-of-bag error": ("exposure",),  # isolated
    }
    assert _exposed_facts(service) == {"Studied Ensemble methods.", "Studied Ensemble methods › Random forest."}
    assert service.doctor().ok


def test_a_card_that_gains_or_loses_an_annotation_is_reclassified_at_sync(tmp_path: Path) -> None:
    service, source_id, store = _vault(tmp_path)
    cards = base_cards()
    cards[4].comments = True
    build_store(store, cards)

    service.sync(source_id)  # the annotation also changes both ancestors' summaries (successor Facts)
    assert _signals(service, source_id)["Bagging"] == ("studied",)
    assert "Studied Ensemble methods › Random forest › Bagging." in _exposed_facts(service)

    build_store(store, base_cards())
    service.sync(source_id)
    assert _signals(service, source_id)["Bagging"] == ("exposure",)
    assert not any("Bagging" in statement for statement in _exposed_facts(service)), "no current support"
    assert service.doctor().ok


def test_the_vault_refuses_evidence_beyond_its_source_ceiling(tmp_path: Path) -> None:
    service, source_id, _ = _vault(tmp_path)
    seq, records = service.snapshot()
    boosting = next(e for e in records.current_evidence(source_id) if e.subject.endswith("Boosting"))

    for forged in (("applied",), ("demonstrated",)):
        with pytest.raises(AptuniError) as refused:
            service._commit([_rederived(boosting, "forged", forged)], seq)
        assert refused.value.code == "invariant_violation" and "beyond its source authority" in str(refused.value)

    bare, bare_id, _ = _vault(tmp_path / "bare", authority=())
    seq, records = bare.snapshot()
    item = records.current_evidence(bare_id)[0]
    with pytest.raises(AptuniError) as unauthorised:
        bare._commit([_rederived(item, "forged", ("studied",))], seq)
    assert unauthorised.value.code == "invariant_violation"


def _legacy_blanket(service: AptuniService, source_id: str) -> None:
    """Reproduce ADR-0028's source-wide label: every card re-derived as studied, with its Facts."""
    seq, records = service.snapshot()
    source = next(s for s in service.sources() if s.id == source_id)
    corrections = [_rederived(item, "legacy", ("studied",)) for item in records.current_evidence(source_id)
                   if item.signals == ("exposure",)]
    profile = derive_evidence_profile(corrections, records, {source_id: source}, purged=frozenset())
    service._commit([*corrections, *profile], seq)


def test_reclassify_migrates_blanket_labels_after_an_owner_confirmation(tmp_path: Path) -> None:
    service, source_id, _ = _vault(tmp_path)
    _legacy_blanket(service, source_id)
    assert len(_exposed_facts(service)) == 5
    before = len(service.records())

    preview = service.source_reclassify_preview(source_id)

    assert len(preview.changes) == 3 and preview.downgrades == 3 and preview.upgrades == 0
    assert len(service.records()) == before, "the preview writes nothing"
    result = service.reclassify_source(source_id, preview.digest)
    assert result.evidence_written == 3 and result.profile_written == 0
    assert len(_exposed_facts(service)) == 2
    records = service.records()
    assert all(item.change_kind == "correction" for item in records.current_evidence(source_id)
               if item.signals == ("exposure",)), "history is kept as supersession"
    assert service.source_reclassify_preview(source_id).changes == ()
    assert service.sync(source_id).profile_written == 0, "sync does not re-derive what was reclassified"
    assert service.doctor().ok


def test_reclassify_is_stale_safe_and_keeps_owner_edits(tmp_path: Path) -> None:
    service, source_id, store = _vault(tmp_path)
    _legacy_blanket(service, source_id)
    bagging = next(f for f in service.facts() if f.statement.endswith("Bagging."))
    service.edit_profile_fact(bagging.id, "I only skimmed bagging")
    stale = service.source_reclassify_preview(source_id)
    cards = base_cards()
    cards[5].title = "OOB estimate"
    build_store(store, cards)
    service.sync(source_id)

    with pytest.raises(AptuniError) as refused:
        service.reclassify_source(source_id, stale.digest)
    assert refused.value.code == "confirmation_stale"
    fresh = service.source_reclassify_preview(source_id)
    service.reclassify_source(source_id, fresh.digest)
    assert "I only skimmed bagging" in _exposed_facts(service), "the owner's own words stay"
    assert service.doctor().ok


def test_legacy_evidence_without_the_annotation_field_uses_the_summary(tmp_path: Path) -> None:
    cards = base_cards()
    cards[3].comments = True  # Boosting: annotated, isolated
    service, source_id, _ = _vault(tmp_path, cards=cards)
    seq, records = service.snapshot()
    boosting = next(e for e in records.current_evidence(source_id) if e.subject.endswith("Boosting"))
    locator = boosting.provenance.locator
    fields = {k: v for k, v in locator.extension.fields.items() if k != "annotated"}
    legacy = boosting.model_copy(update={"provenance": boosting.provenance.model_copy(update={
        "locator": locator.model_copy(update={"extension": locator.extension.model_copy(update={"fields": fields})}),
    })})
    service._commit([_rederived(legacy, "legacy-locator", ("exposure",))], seq)

    preview = service.source_reclassify_preview(source_id)
    assert preview.upgrades == 1 and preview.downgrades == 0, "'1 annotated' in the summary counts"


def test_cli_reclassify_cancel_changes_nothing_and_apply_migrates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    service, source_id, _ = _vault(tmp_path)
    _legacy_blanket(service, source_id)
    before = len(service.records())
    monkeypatch.setattr("builtins.input", lambda _prompt: "no")
    assert cli_run(["source", "reclassify", source_id], service) == 1
    assert len(service.records()) == before
    assert "3 current items would change: 3 lose" in capsys.readouterr().out

    monkeypatch.setattr("builtins.input", lambda _prompt: "APPLY")
    assert cli_run(["source", "reclassify", source_id, "--lang", "zh-CN"], service) == 0
    assert "重新记录 3 条证据" in capsys.readouterr().out
    assert cli_run(["source", "reclassify", source_id], service) == 0
    assert "Nothing to change" in capsys.readouterr().out


def test_authorize_studied_now_re_derives_through_the_classifier(tmp_path: Path) -> None:
    service, source_id, _ = _vault(tmp_path, authority=())
    preview = service.source_authority_preview(source_id, STUDIED)

    assert len(preview.evidence_ids) == 2, "only the cards that show study qualify"
    result = service.grant_source_authority(source_id, STUDIED, preview.digest)
    assert (result.evidence_written, result.profile_written) == (2, 2)
    assert _signals(service, source_id)["Boosting"] == ("exposure",)
    assert RecordSet(service.records().records()).effective_source(
        next(r for r in service.records().records() if r.id == source_id)).authority.primary_for == (STUDIED,)
    assert service.doctor().ok


def test_reclassify_never_recreates_a_fact_the_owner_rejected(tmp_path: Path) -> None:
    service, source_id, _ = _vault(tmp_path)
    forest = next(f for f in service.facts() if f.statement.endswith("Random forest."))
    service.review_profile_fact(forest.id, "reject")
    seq, records = service.snapshot()
    item = next(e for e in records.current_evidence(source_id) if e.subject.endswith("Random forest"))
    service._commit([_rederived(item, "legacy-exposure", ("exposure",))], seq)  # an older classifier's downgrade

    preview = service.source_reclassify_preview(source_id)
    assert preview.upgrades == 1
    assert service.reclassify_source(source_id, preview.digest).profile_written == 0
    assert not any("Random forest" in s for s in _exposed_facts(service))
    assert service.doctor().ok

"""ADR-0031: credentials stay out of Evidence, legacy copies are retracted, Context withholds the rest."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.cli.main import main
from aptuni.mcp.server import create_server

CREDENTIAL_NOTE = "Mail login: someone@example.com 密码：Zq19990717abc"  # synthetic
CLEAN_NOTE = "Markov chain revision notes and stationary distributions."


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    app = AptuniService(Workspace(tmp_path / "state"))
    app.init(tmp_path / "Aptuni")
    return app


def _folder(service: AptuniService, tmp_path: Path, files: dict[str, str]) -> tuple[str, Path]:
    root = tmp_path / "notes"
    root.mkdir(exist_ok=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    source = service.add_folder_source(root, ("knowledge",), "notes")
    return source.id, root


def _texts(service: AptuniService) -> list[str]:
    return [str(getattr(record, "excerpt", None) or "") for record in service.records().records()
            if record.record_type == "evidence"]


def test_a_new_file_with_a_credential_is_withheld_and_reported(service: AptuniService, tmp_path: Path) -> None:
    source_id, _ = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE, "notes.md": CLEAN_NOTE})
    report = service.sync(source_id)
    assert [e.subject for e in service.evidence(source_id)] == ["notes.md"]
    assert report.withheld == 1 and "credential_withheld" in report.notes
    assert not any("Zq19990717abc" in text for text in _texts(service))


def test_a_file_edited_to_hold_a_credential_retracts_the_old_version_without_copying_text(
    service: AptuniService, tmp_path: Path,
) -> None:
    source_id, root = _folder(service, tmp_path, {"info.txt": "Application checklist."})
    service.sync(source_id)
    (root / "info.txt").write_text(CREDENTIAL_NOTE, encoding="utf-8")
    service.sync(source_id)
    assert service.evidence(source_id) == []
    retraction = next(r for r in service.records().records()
                      if r.record_type == "evidence" and r.change_kind == "retraction")
    assert retraction.excerpt is None
    assert not any("Zq19990717abc" in text for text in _texts(service))


def test_legacy_evidence_with_a_credential_is_retracted_on_the_next_sync(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aptuni.application.credential_guard as guard

    source_id, _ = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE, "notes.md": CLEAN_NOTE})
    monkeypatch.setattr(guard, "contains_credential", lambda text: False)  # a pre-ADR-0031 Vault
    service.sync(source_id)
    assert len(service.evidence(source_id)) == 2
    monkeypatch.undo()
    report = service.sync(source_id)  # unchanged files: only the legacy sweep can act
    assert [e.subject for e in service.evidence(source_id)] == ["notes.md"]
    assert report.withheld == 1
    sweep = next(r for r in service.records().records()
                 if r.record_type == "evidence" and r.change_kind == "retraction")
    assert sweep.excerpt is None
    assert service.sync(source_id).withheld == 0  # idempotent


def test_removing_a_credential_file_does_not_copy_its_text_into_the_retraction(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aptuni.application.credential_guard as guard

    source_id, root = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE})
    monkeypatch.setattr(guard, "contains_credential", lambda text: False)
    service.sync(source_id)
    monkeypatch.undo()
    (root / "info.txt").unlink()
    service.sync(source_id)
    retractions = [r for r in service.records().records()
                   if r.record_type == "evidence" and r.change_kind == "retraction"]
    assert len(retractions) == 1 and retractions[0].excerpt is None


def test_context_withholds_credentials_from_agents_and_says_so(service: AptuniService) -> None:
    service.remember("My lab VM password: Tr0ub4dor&3x", "knowledge")
    service.remember("Use a password manager for lab accounts.", "knowledge")
    response = service.context("password", modules=("knowledge",), budget=4000)
    texts = [item.text for item in response.items if item.layer == "L3"]
    assert texts == ["Use a password manager for lab accounts."]
    assert response.withheld_credentials == 1
    access = HostContextAccess("claude-adapter", frozenset({"context.read"}), frozenset({"knowledge"}),
                               "remote_unknown", True)
    server = create_server(service, access)

    async def exercise() -> None:
        result = await server.call_tool("aptuni_search_context", {"query": "password", "modules": ["knowledge"]})
        payload = result.structured_content
        assert "withheld_credentials" not in payload  # no oracle for the host (Review 93 N1)
        assert "Tr0ub4dor" not in str(payload)

    anyio.run(exercise)


def test_identity_card_withholds_only_the_credential_statement(service: AptuniService) -> None:
    service.remember("API key = q8W2-x9zP-77Lm-Qa1b", "identity")
    service.remember("I am a mathematics undergraduate.", "identity")
    card = service.identity_card(budget=2000)
    assert [item.text for item in card.items] == ["I am a mathematics undergraduate."]
    assert card.withheld_credentials == 1


def test_doctor_reports_credential_like_records_without_their_text(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    import aptuni.application.credential_guard as guard

    source_id, _ = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE})
    monkeypatch.setattr(guard, "contains_credential", lambda text: False)
    service.sync(source_id)
    monkeypatch.undo()
    monkeypatch.setenv("APTUNI_STATE_DIR", str(service.workspace.state_dir))
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "1 record(s) contain credential-like text" in out and "Zq1999" not in out


def test_agent_memory_proposals_with_credentials_are_refused(service: AptuniService) -> None:
    from aptuni.application.errors import AptuniError

    for statement in ("学信网 密码：Zq19990717abc", "deploy key " + "hf_" + "a" * 32):
        with pytest.raises(AptuniError) as refused:
            service.observe(statement, "goals", origin="host", principal="claude-adapter")
        assert refused.value.code == "memory_proposal_rejected"



def test_sync_report_names_withheld_items_by_location_for_the_owner(
    service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id, _ = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE, "notes.md": CLEAN_NOTE})
    report = service.sync(source_id)
    assert report.withheld_items == ("info.txt",)
    (tmp_path / "notes" / "later.txt").write_text("**Password**: Zq1999abc!", encoding="utf-8")
    monkeypatch.setenv("APTUNI_STATE_DIR", str(service.workspace.state_dir))
    assert main(["sync", source_id]) == 0
    out = capsys.readouterr().out
    assert "later.txt" in out and "Zq1999" not in out


def test_removing_a_source_does_not_copy_credentials_into_its_retractions(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aptuni.application.credential_guard as guard

    source_id, _ = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE, "notes.md": CLEAN_NOTE})
    monkeypatch.setattr(guard, "contains_credential", lambda text: False)
    service.sync(source_id)
    monkeypatch.undo()
    preview = service.source_removal_preview(source_id)
    service.remove_source(source_id, preview.digest)
    assert sum("Zq19990717abc" in text for text in _texts(service)) == 1  # only the pre-guard original


def test_authority_regrant_retracts_rather_than_recopies_a_credential(service: AptuniService) -> None:
    from aptuni.application.credential_guard import rederive_or_withhold
    from aptuni.domain.records import Evidence

    previous = _legacy_evidence(service, "Studied 密码：Zq19990717abc")
    record = rederive_or_withhold(previous, "evd_" + "1" * 26, signals=("studied",))
    assert isinstance(record, Evidence) and record.change_kind == "retraction" and record.excerpt is None
    assert "Zq19990717abc" not in record.subject


def test_guard_retractions_scrub_credential_titles_in_the_locator(service: AptuniService) -> None:
    from aptuni.application.credential_guard import retraction_of

    previous = _legacy_evidence(service, "Wifi page", title="Wifi 密码：Zq19990717abc")
    retraction = retraction_of(previous, "evd_" + "2" * 26, episode="sync-2", policy_epoch=0)
    assert "Zq19990717abc" not in retraction.model_dump_json()


def test_retracting_a_fact_does_not_copy_its_credential(service: AptuniService) -> None:
    fact = service.remember("My lab VM password: Tr0ub4dor&3x", "knowledge")
    retraction = service.retract(fact.id)
    assert "Tr0ub4dor" not in retraction.statement


def _legacy_evidence(service: AptuniService, text: str, title: str | None = None):  # type: ignore[no-untyped-def]
    from aptuni.application.ingest import SOURCE_RETENTION
    from aptuni.domain.ids import new_id
    from aptuni.domain.records import Evidence
    from aptuni.domain.temporal import utc_now

    fields = {"relative_path": "page.md", **({"title": title} if title else {})}
    return Evidence.model_validate({
        "record_type": "evidence", "id": new_id("evd"), "schema_version": 1, "recorded_at": utc_now(),
        "valid_from": None, "valid_until": None, "module": "knowledge",
        "provenance": {"source_id": "src_" + "0" * 26, "episode": "sync-1",
                       "locator": {"provider": "folder", "subject_id": "folder-0", "extension": {
                           "schema": "folder.locator", "version": 1, "fields": fields}}},
        "trust": "untrusted_source", "retention": SOURCE_RETENTION.model_dump(),
        "policy_epoch": 0, "confidence": None, "review_status": "auto_derived", "supersedes": (),
        "change_kind": "assert", "subject": text, "signals": ("exposure",), "excerpt": text,
        "content_hash": "sha256:" + "0" * 64, "observed_at": utc_now(),
    })


def test_owner_context_json_reports_the_withheld_count(
    service: AptuniService, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service.remember("My lab VM password: Tr0ub4dor&3x", "knowledge")
    monkeypatch.setenv("APTUNI_STATE_DIR", str(service.workspace.state_dir))
    assert main(["context", "lab VM password", "--json"]) == 0
    out = capsys.readouterr().out
    assert '"withheld_credentials": 1' in out and "Tr0ub4dor" not in out


def _ingest_unguarded(service: AptuniService, source_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    import aptuni.application.credential_guard as guard

    monkeypatch.setattr(guard, "contains_credential", lambda text: False)
    service.sync(source_id)
    monkeypatch.undo()


def test_credential_history_purge_erases_only_the_credential_chain(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id, root = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE, "notes.md": CLEAN_NOTE})
    _ingest_unguarded(service, source_id, monkeypatch)
    (root / "info.txt").rename(root / "info-secret.txt")  # the owner's containment (ADR-0006 skips it)
    _ingest_unguarded(service, source_id, monkeypatch)  # pre-guard deletion copied the excerpt
    assert sum("Zq19990717abc" in text for text in _texts(service)) == 2

    preview = service.privacy_purge_preview((), credential_history=True)
    assert preview.source_ids == () and len(preview.record_ids) == 2
    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state != "incomplete_retryable"

    assert not any("Zq19990717abc" in text for text in _texts(service))
    assert service.credential_records() == []
    assert [e.subject for e in service.evidence(source_id)] == ["notes.md"]
    (root / "info.txt").write_text("Application checklist.", encoding="utf-8")
    service.sync(source_id)  # the source keeps syncing; a reused path starts a fresh lineage
    assert sorted(e.subject for e in service.evidence(source_id)) == ["info.txt", "notes.md"]
    assert service.doctor().ok


def test_credential_history_purge_never_takes_a_current_record(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id, root = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE})
    _ingest_unguarded(service, source_id, monkeypatch)
    (root / "info.txt").write_text("Mail login moved to the password manager.", encoding="utf-8")
    service.sync(source_id)  # history holds the secret; the current, clean version shares the chain
    with pytest.raises(AptuniError) as refused:
        service.privacy_purge_preview((), credential_history=True)
    assert refused.value.code == "nothing_to_purge"
    assert [e.subject for e in service.evidence(source_id)] == ["info.txt"]


def test_credential_history_purge_cli_preview_needs_no_record_ids(
    service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id, root = _folder(service, tmp_path, {"info.txt": CREDENTIAL_NOTE, "notes.md": CLEAN_NOTE})
    _ingest_unguarded(service, source_id, monkeypatch)
    (root / "info.txt").unlink()
    service.sync(source_id)
    monkeypatch.setenv("APTUNI_STATE_DIR", str(service.workspace.state_dir))
    assert main(["privacy", "purge", "preview", "--credential-history"]) == 0
    out = capsys.readouterr().out
    assert "Records after non-resurrection expansion: 2" in out and "Zq1999" not in out

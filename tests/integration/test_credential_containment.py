"""ADR-0031: credentials stay out of Evidence, legacy copies are retracted, Context withholds the rest."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest

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
        assert payload["withheld_credentials"] == 1
        assert "Tr0ub4dor" not in str(payload)

    anyio.run(exercise)


def test_identity_card_withholds_a_credential(service: AptuniService) -> None:
    service.remember("API key = q8W2-x9zP-77Lm-Qa1b", "identity")
    card = service.identity_card(budget=2000)
    assert not any("q8W2" in item.text for item in card.items) and card.withheld_credentials == 1


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

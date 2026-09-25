"""Official-MCP Notion source application and CLI flow with an injected authenticated client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.sources.notion import NotionEntity

PAGE = "11111111-1111-4111-8111-111111111111"


class FakeNotionClient:
    def __init__(self, entities: list[NotionEntity] | None = None, *, authenticated: bool = True) -> None:
        self.entities = entities or []
        self.authenticated = authenticated
        self.requested: list[tuple[str, ...]] = []

    def fetch(self, entity_urls: tuple[str, ...]) -> tuple[str, list[NotionEntity]]:
        self.requested.append(entity_urls)
        if not self.authenticated:
            raise AptuniError("notion_auth_required", "Connect this source to official Notion MCP first.")
        return "22222222-2222-4222-8222-222222222222", self.entities


def page(text: str = "# Useful note\nVisible body with a task.\n") -> NotionEntity:
    return NotionEntity(
        entity_id=PAGE,
        entity_type="page",
        canonical_url=f"https://www.notion.so/{PAGE.replace('-', '')}",
        title="Useful note",
        text=text,
        last_edited_at="2026-09-23T08:00:00.000Z",
        parent_id=None,
        truncated=False,
        unknown_block_ids=(),
        completeness_verified=True,
    )


def service_at(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    return service


def test_exact_scope_sync_emits_minimized_evidence_and_replays(monkeypatch: pytest.MonkeyPatch,
                                                               tmp_path: Path) -> None:
    service = service_at(tmp_path)
    client = FakeNotionClient([page()])
    monkeypatch.setattr(service, "_notion_client", lambda _spec: client)
    source = service.add_notion_source((PAGE,), modules=("knowledge",), role="notes")

    first = service.sync(source.id)
    second = service.sync(source.id)

    assert first.counts == {"add": 1} and second.counts == {}
    assert client.requested == [source.roots, source.roots]
    [evidence] = service.evidence(source.id)
    assert evidence.excerpt == "Useful note Visible body with a task."
    assert len(evidence.excerpt) <= 280
    assert evidence.provenance.locator.provider == "notion"
    assert evidence.provenance.locator.extension.fields["entity_id"] == PAGE


def test_sync_requires_official_mcp_auth_without_canonical_change(monkeypatch: pytest.MonkeyPatch,
                                                                  tmp_path: Path) -> None:
    service = service_at(tmp_path)
    source = service.add_notion_source((PAGE,), modules=("knowledge",), role="notes")
    before = service.snapshot()[0]
    monkeypatch.setattr(service, "_notion_client", lambda _spec: FakeNotionClient(authenticated=False))

    with pytest.raises(AptuniError) as error:
        service.sync(source.id)

    assert error.value.code == "notion_auth_required"
    assert service.snapshot()[0] == before
    assert service.evidence(source.id) == []


def test_partial_fetch_cannot_withdraw_existing_evidence(monkeypatch: pytest.MonkeyPatch,
                                                          tmp_path: Path) -> None:
    service = service_at(tmp_path)
    other = "22222222-2222-4222-8222-222222222222"
    entities = [page(), NotionEntity(**{**page().__dict__, "entity_id": other,
                                        "canonical_url": f"https://www.notion.so/{other.replace('-', '')}"})]
    client = FakeNotionClient(entities)
    monkeypatch.setattr(service, "_notion_client", lambda _spec: client)
    source = service.add_notion_source((PAGE, other), modules=("knowledge",), role="notes")
    service.sync(source.id)
    assert len(service.evidence(source.id)) == 2

    client.entities = [page("# Changed\nnew body\n")]
    report = service.sync(source.id)

    assert "coverage_partial" in report.notes
    assert report.counts == {"modify": 1}
    assert len(service.evidence(source.id)) == 2


def test_cli_add_notion_is_explicit_and_stores_no_credentials(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = service_at(tmp_path)

    assert run([
        "source", "add-notion", PAGE,
        "--module", "knowledge", "--role", "notes", "--json",
    ], service) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["type"] == "notion"
    serialized = json.dumps(result, sort_keys=True).lower()
    assert "token" not in serialized and "secret" not in serialized
    assert result["roots"] == [f"https://www.notion.so/{PAGE.replace('-', '')}"]


def test_malformed_mcp_metadata_becomes_a_sanitized_application_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    service = service_at(tmp_path)
    malformed = NotionEntity(**{**page().__dict__, "parent_id": "bad\x1b[31m-parent"})
    monkeypatch.setattr(service, "_notion_client", lambda _spec: FakeNotionClient([malformed]))
    source = service.add_notion_source((PAGE,), modules=("knowledge",), role="notes")

    with pytest.raises(AptuniError) as error:
        service.sync(source.id)

    assert error.value.code == "notion_sync_failed"
    assert "parent" not in error.value.message


def test_crash_after_canonical_commit_replays_without_duplicate_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from aptuni.application import ingest

    service = service_at(tmp_path)
    client = FakeNotionClient([page()])
    monkeypatch.setattr(service, "_notion_client", lambda _spec: client)
    source = service.add_notion_source((PAGE,), modules=("knowledge",), role="notes")
    original_save = ingest.SourceStateStore.save

    def crash(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("notion state-save crash")

    monkeypatch.setattr(ingest.SourceStateStore, "save", crash)
    with pytest.raises(RuntimeError, match="notion state-save crash"):
        service.sync(source.id)
    monkeypatch.setattr(ingest.SourceStateStore, "save", original_save)

    replay = service.sync(source.id)
    assert replay.evidence_written == 0
    assert len(service.evidence(source.id)) == 1
    assert service.doctor().ok

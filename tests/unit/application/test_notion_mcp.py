"""Official Notion MCP credential confinement and result parsing."""

from __future__ import annotations

import json
from types import SimpleNamespace

import anyio
import pytest
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.types import CallToolResult, TextContent

from aptuni.application.errors import AptuniError
from aptuni.application.notion_mcp import (
    MacKeychainTokenStorage,
    NotionMcpClient,
    _Callback,
    _entity,
    _text_result,
)
from aptuni.sources.notion import NOTION_MCP_ENDPOINT, NotionSourceSpec

PAGE = "11111111-1111-4111-8111-111111111111"


def test_official_endpoint_is_pinned() -> None:
    assert NOTION_MCP_ENDPOINT == "https://mcp.notion.com/mcp"


def test_keychain_write_never_places_secret_in_process_arguments(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[tuple[list[str], str | None]] = []

    def fake_run(argv: list[str], **kwargs):  # type: ignore[no-untyped-def]
        calls.append((argv, kwargs.get("input")))
        if "find-generic-password" in argv:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("aptuni.application.notion_mcp.platform.system", lambda: "Darwin")
    monkeypatch.setattr("aptuni.application.notion_mcp.subprocess.run", fake_run)
    marker = "SECRET-OAUTH-MARKER"

    MacKeychainTokenStorage()._write({"tokens": {"access_token": marker}})

    argv, stdin = calls[-1]
    assert marker not in " ".join(argv)
    assert argv[-1] == "-w"
    assert marker in str(stdin)


def test_fetch_result_keeps_identity_and_bounded_metadata() -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    result = SimpleNamespace(
        isError=False,
        content=[SimpleNamespace(type="text", text=json.dumps({
            "metadata": {"type": "page", "parent_id": "parent"},
            "title": "Title",
            "url": url,
            "text": "# Title\nbody",
            "page_last_edited_at": "2026-09-23T08:00:00.000Z",
            "truncated": False,
            "unknown_block_ids": [],
        }))],
    )

    entity = _entity(_text_result(result), url)

    assert entity.entity_id == PAGE
    assert entity.parent_id == "parent"
    assert entity.last_edited_at == "2026-09-23T08:00:00.000Z"


@pytest.mark.parametrize(
    "patch",
    [
        {"metadata": "not-an-object"},
        {"metadata": {"type": 7}},
        {"metadata": {"type": "page", "parent_id": 7}},
        {"page_last_edited_at": 7},
        {"truncated": "true"},
        {"unknown_block_count": "1"},
        {"unknown_block_count": True},
        {"unknown_block_count": 1, "unknown_block_ids": []},
    ],
)
def test_fetch_result_rejects_malformed_provenance_and_completeness(patch: dict[str, object]) -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    body: dict[str, object] = {
        "metadata": {"type": "page"},
        "title": "Title",
        "url": url,
        "text": "# Title\nbody",
        "page_last_edited_at": "2026-09-23T08:00:00.000Z",
        "truncated": False,
        "unknown_block_ids": [],
    }
    body.update(patch)

    with pytest.raises(AptuniError) as error:
        _entity(body, url)

    assert error.value.code == "notion_mcp_result_invalid"


def test_real_sdk_error_result_is_not_parsed_as_success() -> None:
    result = CallToolResult(content=[TextContent(type="text", text='{"secret":"do not echo"}')], isError=True)

    try:
        _text_result(result)
    except AptuniError as error:
        assert error.code == "notion_mcp_failed"
        assert "secret" not in error.message
    else:
        raise AssertionError("tool error was accepted")


def test_keychain_delete_and_failures_are_content_free(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(argv)
        return SimpleNamespace(returncode=44, stdout="PRIVATE", stderr="PRIVATE")

    monkeypatch.setattr("aptuni.application.notion_mcp.platform.system", lambda: "Darwin")
    monkeypatch.setattr("aptuni.application.notion_mcp.subprocess.run", fake_run)

    assert MacKeychainTokenStorage().delete() is False
    assert "PRIVATE" not in repr(calls)
    assert "delete-generic-password" in calls[-1]


def test_production_session_calls_only_self_identity_and_exact_approved_fetches() -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    calls: list[tuple[str, dict[str, str]]] = []

    class Session:
        async def call_tool(self, name: str, arguments: dict[str, str]) -> CallToolResult:
            calls.append((name, arguments))
            if name == "notion-get-users":
                body = {"results": [{"type": "person", "id": PAGE}], "has_more": False}
            else:
                body = {
                    "metadata": {"type": "page"}, "title": "Title", "url": url,
                    "text": "# Title\nbody", "truncated": False, "unknown_block_ids": [],
                }
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(body))])

    client = NotionMcpClient(NotionSourceSpec.build((PAGE,)))
    principal, entities = anyio.run(client._fetch_with_session, Session())  # type: ignore[arg-type]

    assert principal == PAGE and len(entities) == 1
    assert calls == [
        ("notion-get-users", {"user_id": "self"}),
        ("notion-fetch", {"id": url}),
    ]


def test_callback_propagates_state_and_times_out_without_a_request(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class Server:
        server_port = 43123
        timeout = 0

        def handle_request(self) -> None:
            return

        def server_close(self) -> None:
            return

    monkeypatch.setattr("aptuni.application.notion_mcp.HTTPServer", lambda *_args: Server())
    callback = _Callback()
    callback.values.put_nowait({"code": "code", "state": "exact-state"})
    result = anyio.run(callback.result)
    assert result.state == "exact-state"

    timed_out = _Callback()
    with pytest.raises(AptuniError) as error:
        anyio.run(timed_out.result)
    assert error.value.code == "notion_auth_timeout"


def test_keychain_storage_round_trips_refresh_material_without_files(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    storage = MacKeychainTokenStorage()
    persisted: dict[str, object] = {}
    monkeypatch.setattr(storage, "_read", lambda: dict(persisted))

    def save(value: dict[str, object]) -> None:
        persisted.clear()
        persisted.update(value)

    monkeypatch.setattr(storage, "_write", save)
    token = OAuthToken(access_token="access", refresh_token="refresh")
    client = OAuthClientInformationFull(client_id="client")
    anyio.run(storage.set_tokens, token)
    anyio.run(storage.set_client_info, client)

    assert anyio.run(storage.get_tokens) == token
    assert anyio.run(storage.get_client_info) == client
    assert anyio.run(storage.has_connection)


def test_keychain_write_failure_never_echoes_secret(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_run(_argv: list[str], **_kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(returncode=1, stdout="SECRET", stderr="SECRET")

    monkeypatch.setattr("aptuni.application.notion_mcp.platform.system", lambda: "Darwin")
    monkeypatch.setattr("aptuni.application.notion_mcp.subprocess.run", fake_run)
    with pytest.raises(AptuniError) as error:
        MacKeychainTokenStorage()._write({"access_token": "SECRET"})
    assert error.value.code == "notion_credentials_write_failed"
    assert "SECRET" not in error.value.message

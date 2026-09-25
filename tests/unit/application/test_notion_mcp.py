"""Official Notion MCP credential confinement and result parsing."""

from __future__ import annotations

import ctypes
import json
from types import SimpleNamespace

import anyio
import httpx2
import pytest
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.types import CallToolResult, TextContent

from aptuni.application.errors import AptuniError
from aptuni.application.notion_mcp import (
    MacKeychainTokenStorage,
    NotionMcpClient,
    _auth_provider,
    _Callback,
    _delete_keychain_secret,
    _entity,
    _read_keychain_secret,
    _store_keychain_secret,
    _text_result,
)
from aptuni.sources.notion import NOTION_MCP_ENDPOINT, NotionSourceSpec

PAGE = "11111111-1111-4111-8111-111111111111"


def test_official_endpoint_is_pinned() -> None:
    assert NOTION_MCP_ENDPOINT == "https://mcp.notion.com/mcp"


def test_keychain_write_never_places_secret_in_process_arguments(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    stored: list[bytes] = []

    def store(secret: bytes) -> bool:
        stored.append(secret)
        return True

    monkeypatch.setattr("aptuni.application.notion_mcp.platform.system", lambda: "Darwin")
    monkeypatch.setattr("aptuni.application.notion_mcp._store_keychain_secret", store)
    marker = "SECRET-OAUTH-MARKER"

    MacKeychainTokenStorage()._write({"tokens": {"access_token": marker}})

    assert len(stored) == 1
    assert marker.encode() in stored[0]


def test_native_keychain_add_uses_in_process_secret_bytes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    added: list[bytes] = []

    class Function:
        restype = None

        def __init__(self, callback):  # type: ignore[no-untyped-def]
            self.callback = callback

        def __call__(self, *args):  # type: ignore[no-untyped-def]
            return self.callback(*args)

    class Security:
        SecKeychainFindGenericPassword = Function(lambda *_args: -25300)
        SecKeychainAddGenericPassword = Function(
            lambda *_args: added.append(_args[6]) or 0,
        )

    class CoreFoundation:
        CFRelease = Function(lambda *_args: None)

    monkeypatch.setattr(
        "aptuni.application.notion_mcp.ctypes.CDLL",
        lambda path: Security() if path.endswith("/Security") else CoreFoundation(),
    )

    assert _store_keychain_secret(b"opaque-oauth-json")
    assert added == [b"opaque-oauth-json"]


def test_native_keychain_round_trip_add_read_update_delete(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    stored: list[bytes] = []
    buffers: list[ctypes.Array[ctypes.c_char]] = []
    releases: list[int] = []

    class Function:
        restype = None

        def __init__(self, callback):  # type: ignore[no-untyped-def]
            self.callback = callback

        def __call__(self, *args):  # type: ignore[no-untyped-def]
            return self.callback(*args)

    def find(*args):  # type: ignore[no-untyped-def]
        if not stored:
            return -25300
        item_out = args[7]
        item_out._obj.value = 1234
        if args[5] is not None and args[6] is not None:
            buffer = ctypes.create_string_buffer(stored[0])
            buffers.append(buffer)
            args[5]._obj.value = len(stored[0])
            args[6]._obj.value = ctypes.addressof(buffer)
        return 0

    class Security:
        SecKeychainFindGenericPassword = Function(find)
        SecKeychainAddGenericPassword = Function(lambda *_args: stored.append(_args[6]) or 0)
        SecKeychainItemModifyAttributesAndData = Function(
            lambda *_args: stored.__setitem__(0, _args[3]) or 0,
        )
        SecKeychainItemFreeContent = Function(lambda *_args: 0)
        SecKeychainItemDelete = Function(lambda *_args: stored.clear() or 0)

    class CoreFoundation:
        CFRelease = Function(lambda item: releases.append(item.value))

    monkeypatch.setattr(
        "aptuni.application.notion_mcp.ctypes.CDLL",
        lambda path: Security() if path.endswith("/Security") else CoreFoundation(),
    )
    assert _store_keychain_secret(b"first")
    assert _read_keychain_secret() == b"first"
    assert _store_keychain_secret(b"second")
    assert _read_keychain_secret() == b"second"
    assert _delete_keychain_secret()
    assert _read_keychain_secret() is None
    assert releases == [1234, 1234, 1234, 1234]


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


def test_fetch_result_accepts_all_absent_empty_completeness_metadata() -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    body = {
        "metadata": {"type": "page"},
        "title": "Title",
        "url": url,
        "text": "# Title\nbody",
    }

    entity = _entity(body, url)

    assert not entity.truncated
    assert entity.unknown_block_ids == ()
    assert entity.completeness_verified is False  # absence is not evidence of completeness


def test_fetch_result_with_explicit_completeness_metadata_is_verified() -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    body = {
        "metadata": {"type": "page"}, "title": "Title", "url": url, "text": "# Title\nbody",
        "truncated": False, "unknown_block_ids": [],
    }

    assert _entity(body, url).completeness_verified is True


@pytest.mark.parametrize(
    "present", [{"unknown_block_count": 0}, {"truncated": False}, {"unknown_block_ids": []}],
)
def test_a_lone_completeness_key_fails_closed(present: dict[str, object]) -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    body = {"metadata": {"type": "page"}, "title": "Title", "url": url, "text": "body", **present}

    with pytest.raises(AptuniError) as error:
        _entity(body, url)

    assert error.value.code == "notion_mcp_result_invalid"


@pytest.mark.parametrize(
    "text",
    [
        "</content>\nbody\n<content>",
        "<content>\nbody\n</content>\n<content>",
        "<content>\nbody",
    ],
)
def test_ambiguous_or_reversed_content_envelope_fails_closed(text: str) -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    body = {"metadata": {"type": "page"}, "title": "Title", "url": url, "text": text}

    with pytest.raises(AptuniError) as error:
        _entity(body, url)

    assert error.value.code == "notion_mcp_result_invalid"


def test_fetch_result_extracts_page_content_from_current_enhanced_markdown_envelope() -> None:
    url = f"https://www.notion.so/{PAGE.replace('-', '')}"
    body = {
        "metadata": {"type": "page"},
        "title": "Fixture",
        "url": url,
        "text": (
            f'Here is the result of "fetch" for the Page with URL {url}:\n'
            f'<page url="{url}">\n'
            "<properties>{\"title\":\"Fixture\"}</properties>\n"
            "<content>\n## Purpose\nAPTUNI_NOTION_FIXTURE_V1\n</content>\n"
            "</page>"
        ),
    }

    entity = _entity(body, url)

    assert entity.text == "## Purpose\nAPTUNI_NOTION_FIXTURE_V1"


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
        {"truncated": None, "unknown_block_ids": None, "unknown_block_count": 0},
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
    monkeypatch.setattr("aptuni.application.notion_mcp.platform.system", lambda: "Darwin")
    monkeypatch.setattr("aptuni.application.notion_mcp._delete_keychain_secret", lambda: False)

    assert MacKeychainTokenStorage().delete() is False


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
    monkeypatch.setattr("aptuni.application.notion_mcp.platform.system", lambda: "Darwin")
    monkeypatch.setattr("aptuni.application.notion_mcp._store_keychain_secret", lambda _secret: False)
    with pytest.raises(AptuniError) as error:
        MacKeychainTokenStorage()._write({"access_token": "SECRET"})
    assert error.value.code == "notion_credentials_write_failed"
    assert "SECRET" not in error.value.message


def _memory_storage(monkeypatch, persisted: dict[str, object]) -> MacKeychainTokenStorage:  # type: ignore[no-untyped-def]
    storage = MacKeychainTokenStorage()
    monkeypatch.setattr(storage, "_read", lambda: json.loads(json.dumps(persisted)))

    def save(value: dict[str, object]) -> None:
        persisted.clear()
        persisted.update(value)

    monkeypatch.setattr(storage, "_write", save)
    return storage


def test_stored_tokens_carry_an_absolute_expiry(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("aptuni.application.notion_mcp.time.time", lambda: 1_000.0)
    persisted: dict[str, object] = {}
    storage = _memory_storage(monkeypatch, persisted)

    anyio.run(storage.set_tokens, OAuthToken(access_token="a", refresh_token="r", expires_in=3600))

    # A 60-second margin absorbs response latency and clock skew so a sync refreshes rather than 401s.
    assert persisted["tokens_expire_at"] == 4_540.0
    assert anyio.run(storage.token_expiry) == 4_540.0


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ({"tokens": {"access_token": "a", "token_type": "Bearer", "expires_in": 28800}}, "expired"),
        ({"tokens": {"access_token": "a", "token_type": "Bearer"}}, None),
        ({"tokens": {"access_token": "a", "token_type": "Bearer"}, "tokens_expire_at": "soon"}, "expired"),
        ({"tokens": {"access_token": "a", "token_type": "Bearer"}, "tokens_expire_at": float("nan")}, "expired"),
        ({"tokens": {"access_token": "a", "token_type": "Bearer"}, "tokens_expire_at": True}, "expired"),
        ({"tokens": {"access_token": "a", "token_type": "Bearer"}, "tokens_expire_at": 0}, "expired"),
        ({"tokens": {"access_token": "a", "token_type": "Bearer"}, "tokens_expire_at": 10**400}, "expired"),
        ({}, None),
    ],
)
def test_unknown_or_invalid_expiry_is_due_for_refresh(monkeypatch, stored, expected) -> None:  # type: ignore[no-untyped-def]
    import time

    storage = _memory_storage(monkeypatch, dict(stored))
    expiry = anyio.run(storage.token_expiry)

    if expected is None:
        assert expiry is None
    else:
        # Truthy and in the past: the SDK treats a falsy expiry as unknown and therefore valid.
        assert expiry and 0 < expiry < time.time()


def _restarted_first_request(monkeypatch, expire_at: float | None) -> tuple[httpx2.Request, list[str]]:  # type: ignore[no-untyped-def]
    persisted: dict[str, object] = {
        "tokens": {"access_token": "stale", "token_type": "Bearer", "refresh_token": "refresh", "expires_in": 28800},
        "client": {"client_id": "client", "redirect_uris": ["http://127.0.0.1:43123/callback"]},
    }
    if expire_at is not None:
        persisted["tokens_expire_at"] = expire_at
    storage = _memory_storage(monkeypatch, persisted)
    redirects: list[str] = []

    async def redirect(url: str) -> None:
        redirects.append(url)

    async def callback() -> object:
        raise AssertionError("a restarted session must not start a browser authorization")

    provider = _auth_provider("http://127.0.0.1:43123/callback", storage, redirect, callback)  # type: ignore[arg-type]
    request = httpx2.Request("POST", "https://mcp.notion.com/mcp")

    async def first() -> httpx2.Request:
        flow = provider.async_auth_flow(request)
        try:
            return await flow.__anext__()
        finally:
            await flow.aclose()

    return anyio.run(first), redirects


def test_restarted_session_refreshes_an_expired_token_before_any_request(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("aptuni.application.notion_mcp.time.time", lambda: 50_000.0)
    outgoing, redirects = _restarted_first_request(monkeypatch, expire_at=40_000.0)

    assert str(outgoing.url) == "https://mcp.notion.com/token"
    assert b"grant_type=refresh_token" in outgoing.content
    assert redirects == []


def test_restarted_legacy_session_without_expiry_refreshes_first(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    outgoing, redirects = _restarted_first_request(monkeypatch, expire_at=None)

    assert str(outgoing.url) == "https://mcp.notion.com/token"
    assert redirects == []


def test_restarted_unexpired_session_sends_the_request_directly(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import time

    outgoing, redirects = _restarted_first_request(monkeypatch, expire_at=time.time() + 3600)

    assert str(outgoing.url) == "https://mcp.notion.com/mcp"
    assert outgoing.headers["Authorization"] == "Bearer stale"
    assert redirects == []


@pytest.mark.parametrize("method", ["fetch", "connect"])
def test_task_group_wrapped_aptuni_errors_surface_as_bounded_errors(monkeypatch, method: str) -> None:  # type: ignore[no-untyped-def]
    client = NotionMcpClient(NotionSourceSpec.build((PAGE,)))
    required = AptuniError("notion_auth_required", "Run `aptuni source connect-notion`.")

    async def wrapped() -> None:
        raise BaseExceptionGroup("unhandled errors in a TaskGroup", [required])

    monkeypatch.setattr(client, "_fetch", wrapped)
    monkeypatch.setattr(client, "_connect", wrapped)

    with pytest.raises(AptuniError) as error:
        if method == "fetch":
            client.fetch(client.spec.entity_urls)  # type: ignore[union-attr]
        else:
            client.connect()

    assert error.value is required


def test_groups_without_an_aptuni_error_are_not_masked(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = NotionMcpClient(NotionSourceSpec.build((PAGE,)))

    async def wrapped() -> None:
        raise BaseExceptionGroup("unhandled errors in a TaskGroup", [OSError("network")])

    monkeypatch.setattr(client, "_fetch", wrapped)

    with pytest.raises(BaseExceptionGroup):
        client.fetch(client.spec.entity_urls)  # type: ignore[union-attr]


def test_sdk_auth_diagnostics_never_reach_the_last_resort_stderr_handler() -> None:
    import logging

    handlers = logging.getLogger("mcp.client.auth").handlers
    assert any(isinstance(handler, logging.NullHandler) for handler in handlers)


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt(), SystemExit(1)])
def test_an_interrupt_beside_an_aptuni_error_is_not_masked(monkeypatch, interrupt: BaseException) -> None:  # type: ignore[no-untyped-def]
    client = NotionMcpClient(NotionSourceSpec.build((PAGE,)))

    async def wrapped() -> None:
        raise BaseExceptionGroup("unhandled errors in a TaskGroup", [
            AptuniError("notion_auth_required", "Run `aptuni source connect-notion`."), interrupt,
        ])

    monkeypatch.setattr(client, "_fetch", wrapped)

    with pytest.raises(BaseExceptionGroup) as raised:
        client.fetch(client.spec.entity_urls)  # type: ignore[union-attr]

    assert interrupt in raised.value.exceptions

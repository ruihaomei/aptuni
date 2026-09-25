"""Official hosted Notion MCP client with OAuth material confined to macOS Keychain (ADR-0021)."""

from __future__ import annotations

import ctypes
import json
import platform
import queue
import sys
import webbrowser
from collections.abc import Awaitable, Callable
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import anyio
import httpx2
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

from aptuni.application.errors import AptuniError
from aptuni.sources.notion import NOTION_MCP_ENDPOINT, NotionEntity, NotionSourceSpec

_KEYCHAIN_SERVICE = "com.aptuni.notion-mcp"
_KEYCHAIN_ACCOUNT = "default"
_FETCH_TOOL = "notion-fetch"
_IDENTITY_TOOL = "notion-get-users"
_MAX_MCP_RESULT_CHARS = 1_500_000
_ERR_SEC_ITEM_NOT_FOUND = -25300
_ERR_SEC_DUPLICATE_ITEM = -25299


def _keychain_libraries() -> tuple[Any, Any]:
    security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
    core_foundation = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    return security, core_foundation


def _release_keychain_item(core_foundation: Any, item: ctypes.c_void_p) -> None:
    if item.value is not None:
        core_foundation.CFRelease(item)


def _read_keychain_secret() -> bytes | None:
    security, core_foundation = _keychain_libraries()
    service = _KEYCHAIN_SERVICE.encode()
    account = _KEYCHAIN_ACCOUNT.encode()
    password_length = ctypes.c_uint32()
    password_data = ctypes.c_void_p()
    item = ctypes.c_void_p()
    find = security.SecKeychainFindGenericPassword
    find.restype = ctypes.c_int32
    status = int(find(
        None,
        len(service),
        service,
        len(account),
        account,
        ctypes.byref(password_length),
        ctypes.byref(password_data),
        ctypes.byref(item),
    ))
    if status == _ERR_SEC_ITEM_NOT_FOUND:
        return None
    if status != 0 or item.value is None or password_data.value is None:
        _release_keychain_item(core_foundation, item)
        raise OSError(status, "Keychain read failed")
    try:
        return ctypes.string_at(password_data.value, password_length.value)
    finally:
        security.SecKeychainItemFreeContent(None, password_data)
        _release_keychain_item(core_foundation, item)


def _store_keychain_secret(secret: bytes) -> bool:
    """Add or replace the Keychain item without exposing the secret in argv or a TTY."""
    security, core_foundation = _keychain_libraries()
    service = _KEYCHAIN_SERVICE.encode()
    account = _KEYCHAIN_ACCOUNT.encode()
    item = ctypes.c_void_p()
    find = security.SecKeychainFindGenericPassword
    find.restype = ctypes.c_int32
    status = int(find(
        None,
        len(service),
        service,
        len(account),
        account,
        None,
        None,
        ctypes.byref(item),
    ))
    if status == _ERR_SEC_ITEM_NOT_FOUND:
        add = security.SecKeychainAddGenericPassword
        add.restype = ctypes.c_int32
        add_status = int(add(
            None,
            len(service),
            service,
            len(account),
            account,
            len(secret),
            secret,
            None,
        ))
        if add_status == 0:
            return True
        if add_status != _ERR_SEC_DUPLICATE_ITEM:
            return False
        retry_item = ctypes.c_void_p()
        retry_status = int(find(
            None,
            len(service),
            service,
            len(account),
            account,
            None,
            None,
            ctypes.byref(retry_item),
        ))
        if retry_status != 0 or retry_item.value is None:
            _release_keychain_item(core_foundation, retry_item)
            return False
        try:
            modify = security.SecKeychainItemModifyAttributesAndData
            modify.restype = ctypes.c_int32
            return int(modify(retry_item, None, len(secret), secret)) == 0
        finally:
            _release_keychain_item(core_foundation, retry_item)
    if status != 0 or item.value is None:
        return False
    try:
        modify = security.SecKeychainItemModifyAttributesAndData
        modify.restype = ctypes.c_int32
        return int(modify(item, None, len(secret), secret)) == 0
    finally:
        _release_keychain_item(core_foundation, item)


def _delete_keychain_secret() -> bool:
    security, core_foundation = _keychain_libraries()
    service = _KEYCHAIN_SERVICE.encode()
    account = _KEYCHAIN_ACCOUNT.encode()
    item = ctypes.c_void_p()
    find = security.SecKeychainFindGenericPassword
    find.restype = ctypes.c_int32
    status = int(find(
        None,
        len(service),
        service,
        len(account),
        account,
        None,
        None,
        ctypes.byref(item),
    ))
    if status == _ERR_SEC_ITEM_NOT_FOUND:
        return False
    if status != 0 or item.value is None:
        _release_keychain_item(core_foundation, item)
        return False
    try:
        delete = security.SecKeychainItemDelete
        delete.restype = ctypes.c_int32
        return int(delete(item)) == 0
    finally:
        _release_keychain_item(core_foundation, item)


class MacKeychainTokenStorage(TokenStorage):
    """SDK token storage whose secret JSON never enters Aptuni-owned files or argv."""

    def _require_host(self) -> None:
        if platform.system() != "Darwin":
            raise AptuniError(
                "notion_secure_storage_unavailable",
                "Official Notion MCP credentials currently require macOS Keychain.",
            )

    def _read(self) -> dict[str, Any]:
        self._require_host()
        try:
            secret = _read_keychain_secret()
        except OSError as error:
            raise AptuniError(
                "notion_credentials_read_failed", "Could not read Notion MCP credentials from Keychain."
            ) from error
        if secret is None:
            return {}
        try:
            value = json.loads(secret.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AptuniError("notion_credentials_invalid", "The Notion MCP Keychain item is unreadable.") from error
        if not isinstance(value, dict):
            raise AptuniError("notion_credentials_invalid", "The Notion MCP Keychain item is unreadable.")
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self._require_host()
        secret = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        if not _store_keychain_secret(secret):
            raise AptuniError("notion_credentials_write_failed", "Could not save Notion MCP credentials in Keychain.")

    async def get_tokens(self) -> OAuthToken | None:
        value = await anyio.to_thread.run_sync(self._read)
        raw = value.get("tokens")
        return OAuthToken.model_validate(raw) if isinstance(raw, dict) else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        value = await anyio.to_thread.run_sync(self._read)
        value["tokens"] = tokens.model_dump(mode="json")
        await anyio.to_thread.run_sync(self._write, value)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        value = await anyio.to_thread.run_sync(self._read)
        raw = value.get("client")
        return OAuthClientInformationFull.model_validate(raw) if isinstance(raw, dict) else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        value = await anyio.to_thread.run_sync(self._read)
        value["client"] = client_info.model_dump(mode="json")
        await anyio.to_thread.run_sync(self._write, value)

    async def has_connection(self) -> bool:
        return await self.get_tokens() is not None and await self.get_client_info() is not None

    def delete(self) -> bool:
        self._require_host()
        return _delete_keychain_secret()


class _Callback:
    def __init__(self) -> None:
        self.values: queue.Queue[dict[str, str]] = queue.Queue(maxsize=1)

        callback = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlsplit(self.path)
                if parsed.path != "/callback":
                    self.send_error(404)
                    return
                params = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}
                with suppress(queue.Full):
                    callback.values.put_nowait(params)
                body = b"Notion is connected to Aptuni. You can close this tab."
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.server.timeout = 300

    @property
    def redirect_uri(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/callback"

    async def redirect(self, url: str) -> None:
        print("Open this Notion authorization URL if the browser does not open automatically:", file=sys.stderr)
        print(url, file=sys.stderr)
        await anyio.to_thread.run_sync(webbrowser.open, url)

    async def result(self) -> AuthorizationCodeResult:
        await anyio.to_thread.run_sync(self.server.handle_request)
        self.server.server_close()
        try:
            params = self.values.get_nowait()
        except queue.Empty as error:
            raise AptuniError("notion_auth_timeout", "Notion authorization timed out.") from error
        if "error" in params or "code" not in params:
            raise AptuniError("notion_auth_denied", "Notion authorization was denied or incomplete.")
        return AuthorizationCodeResult(code=params["code"], state=params.get("state"), iss=params.get("iss"))


def _metadata(redirect_uri: str) -> OAuthClientMetadata:
    return OAuthClientMetadata(
        client_name="Aptuni",
        software_id="aptuni",
        software_version="0.1.0",
        redirect_uris=[redirect_uri],
        token_endpoint_auth_method="none",
        grant_types=["authorization_code", "refresh_token"],
    )


def _noninteractive_handler() -> Callable[..., Awaitable[Any]]:
    async def fail(*_args: object, **_kwargs: object) -> Any:
        raise AptuniError(
            "notion_auth_required",
            "Run `aptuni source connect-notion`, authorize the official Notion MCP connection, then sync again.",
        )

    return fail


def _text_result(result: Any) -> dict[str, Any]:
    if getattr(result, "is_error", False):
        raise AptuniError("notion_mcp_failed", "Official Notion MCP returned an error; nothing was changed.")
    blocks = getattr(result, "content", ())
    texts = [str(block.text) for block in blocks if getattr(block, "type", None) == "text"]
    body = "\n".join(texts)
    if not body or len(body) > _MAX_MCP_RESULT_CHARS:
        raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP returned an invalid-sized result.")
    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise AptuniError(
            "notion_mcp_result_invalid", "Official Notion MCP returned an unknown result shape.",
        ) from error
    if not isinstance(value, dict):
        raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP returned an unknown result shape.")
    return value


def _entity_text(text: str) -> str:
    opening = "<content>"
    closing = "</content>"
    if opening not in text and closing not in text:
        return text
    if text.count(opening) != 1 or text.count(closing) != 1:
        raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP returned invalid content metadata.")
    start = text.index(opening) + len(opening)
    end = text.find(closing, start)
    if end < 0:
        raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP returned invalid content metadata.")
    return text[start:end].strip()


def _entity(value: dict[str, Any], expected_url: str) -> NotionEntity:
    metadata = value.get("metadata")
    if not isinstance(metadata, dict):
        raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP returned invalid entity metadata.")
    url = value.get("url")
    text = value.get("text")
    title = value.get("title")
    entity_type = metadata.get("type")
    if (not isinstance(url, str) or not isinstance(text, str) or not isinstance(title, str)
            or not isinstance(entity_type, str)):
        raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP omitted required entity fields.")
    expected = NotionSourceSpec.build((expected_url,)).entity_ids[0]
    actual = NotionSourceSpec.build((url,)).entity_ids[0]
    if actual != expected:
        raise AptuniError("notion_mcp_scope_violation", "Official Notion MCP returned a different entity.")
    completeness_keys = {"truncated", "unknown_block_ids", "unknown_block_count"}
    if completeness_keys.isdisjoint(value):
        # The current official server omits these keys; accept the page but never call it complete.
        unknown: list[str] = []
        truncated = False
        verified = False
    else:
        verified = True
        unknown_value = value.get("unknown_block_ids")
        truncated_value = value.get("truncated")
        if (not isinstance(unknown_value, list)
                or not all(isinstance(item, str) for item in unknown_value)
                or type(truncated_value) is not bool):
            raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP returned invalid block metadata.")
        unknown = unknown_value
        truncated = truncated_value
        unknown_count = value.get("unknown_block_count", len(unknown))
        if type(unknown_count) is not int or unknown_count < 0 or unknown_count != len(unknown):
            raise AptuniError(
                "notion_mcp_result_invalid", "Official Notion MCP returned invalid completeness metadata."
            )
    last_edited = (
        value["page_last_edited_at"] if "page_last_edited_at" in value else metadata.get("last_edited_at")
    )
    parent_id = metadata.get("parent_id")
    if ((last_edited is not None and not isinstance(last_edited, str))
            or (parent_id is not None and not isinstance(parent_id, str))):
        raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP returned invalid provenance metadata.")
    return NotionEntity(
        entity_id=actual,
        entity_type=entity_type,
        canonical_url=url,
        title=title,
        text=_entity_text(text),
        last_edited_at=last_edited,
        parent_id=parent_id,
        truncated=truncated,
        unknown_block_ids=tuple(unknown),
        completeness_verified=verified,
    )


class NotionMcpClient:
    def __init__(self, spec: NotionSourceSpec | None = None, storage: MacKeychainTokenStorage | None = None) -> None:
        self.spec = spec
        self.storage = storage or MacKeychainTokenStorage()

    def fetch(self, entity_urls: tuple[str, ...]) -> tuple[str, list[NotionEntity]]:
        if self.spec is None or entity_urls != self.spec.entity_urls:
            raise AptuniError("notion_mcp_scope_violation", "The Notion fetch scope changed unexpectedly.")
        return anyio.run(self._fetch)

    async def _with_session(
        self,
        redirect_uri: str,
        redirect: Callable[[str], Awaitable[None]],
        callback: Callable[[], Awaitable[AuthorizationCodeResult]],
        operation: Callable[[ClientSession], Awaitable[Any]],
    ) -> Any:
        auth = OAuthClientProvider(NOTION_MCP_ENDPOINT, _metadata(redirect_uri), self.storage, redirect, callback)
        client: httpx2.AsyncClient = create_mcp_http_client(auth=auth)
        async with (
            client,
            streamable_http_client(NOTION_MCP_ENDPOINT, http_client=client) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            if not {_FETCH_TOOL, _IDENTITY_TOOL} <= names:
                raise AptuniError(
                    "notion_mcp_contract_changed",
                    "Official Notion MCP does not expose the required identity and fetch tools.",
                )
            return await operation(session)

    @staticmethod
    async def _principal_id(session: ClientSession) -> str:
        value = _text_result(await session.call_tool(_IDENTITY_TOOL, {"user_id": "self"}))
        results = value.get("results")
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
            raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP omitted connection identity.")
        principal_id = results[0].get("id")
        if not isinstance(principal_id, str):
            raise AptuniError("notion_mcp_result_invalid", "Official Notion MCP omitted connection identity.")
        try:
            return str(UUID(principal_id))
        except ValueError as error:
            raise AptuniError(
                "notion_mcp_result_invalid", "Official Notion MCP returned an invalid connection identity."
            ) from error

    async def _fetch_with_session(self, session: ClientSession) -> tuple[str, list[NotionEntity]]:
        principal_id = await self._principal_id(session)
        entities = []
        assert self.spec is not None
        for url in self.spec.entity_urls:
            entities.append(_entity(_text_result(await session.call_tool(_FETCH_TOOL, {"id": url})), url))
        return principal_id, entities

    async def _fetch(self) -> tuple[str, list[NotionEntity]]:
        if not await self.storage.has_connection():
            raise AptuniError(
                "notion_auth_required",
                "Run `aptuni source connect-notion`, authorize official Notion MCP, then sync again.",
            )
        client_info = await self.storage.get_client_info()
        redirect_uri = str(client_info.redirect_uris[0]) if client_info and client_info.redirect_uris else "http://127.0.0.1"
        fail = _noninteractive_handler()

        async def operation(session: ClientSession) -> tuple[str, list[NotionEntity]]:
            return await self._fetch_with_session(session)

        return cast(tuple[str, list[NotionEntity]], await self._with_session(redirect_uri, fail, fail, operation))

    def connect(self) -> str:
        return anyio.run(self._connect)

    def disconnect(self) -> bool:
        return self.storage.delete()

    async def _connect(self) -> str:
        callback = _Callback()

        async def operation(session: ClientSession) -> str:
            return await self._principal_id(session)

        return cast(str, await self._with_session(callback.redirect_uri, callback.redirect, callback.result, operation))

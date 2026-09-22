"""Bounded MCP principal/scope/egress and real STDIO contract tests."""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
import sys
import textwrap
from collections import deque
from pathlib import Path

import anyio
import pytest
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.application.memory_commands import MemoryCommands
from aptuni.application.review_commands import ReviewCommands
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.mcp import server as mcp_server
from aptuni.mcp.server import create_server


def _service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    service.remember("Uses concise answers", "identity")
    service.remember("Studies survival analysis", "knowledge")
    return service


def _access(*, scopes: frozenset[str], modules: frozenset[str], egress: bool = True) -> HostContextAccess:
    return HostContextAccess("test-host", scopes, modules, "remote_unknown", egress)


def test_tool_schema_has_no_caller_authority_or_approval(tmp_path: Path) -> None:
    async def collect() -> list[dict[str, object]]:
        server = create_server(_service(tmp_path))
        return [tool.model_dump(mode="json", exclude_none=True) for tool in await server.list_tools()]

    tools = anyio.run(collect)
    assert [tool["name"] for tool in tools] == [
        "aptuni_health", "aptuni_get_identity_card", "aptuni_search_context",
        "aptuni_get_memory_review", "aptuni_propose_memory"]
    serialized = json.dumps(tools, sort_keys=True)
    for forbidden in ("principal", "approval", "nonce", "confirmation", "vault_path", "database", "accept"):
        assert forbidden not in serialized
    for tool in tools:
        assert tool["annotations"] == {
            "destructive_hint": False,
            "idempotent_hint": True,
            "open_world_hint": False,
            "read_only_hint": tool["name"] != "aptuni_propose_memory",  # proposals only; review is terminal-only
        }


def test_mcp_handlers_cannot_reach_owner_decision_or_commit_services() -> None:
    """ADR-0013 item 1: only an explicit allowlist is reachable from MCP handlers."""
    tree = ast.parse(inspect.getsource(mcp_server))
    reachable = {
        call.func.attr
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "application"
    }

    assert reachable == {
        "context", "identity_card", "memory_review_feed", "propose_from_host",
    }
    assert not reachable & {
        "_commit", "decide_memory", "edit_memory", "forget_memory_confirmed", "memory_preview",
        "observe", "review_memory", "set_review_policy", "snooze_review",
    }

    methods: dict[str, set[str]] = {}
    for cls in (AptuniService, ReviewCommands, MemoryCommands, SourceCommands):
        class_node = ast.parse(textwrap.dedent(inspect.getsource(cls))).body[0]
        assert isinstance(class_node, ast.ClassDef)
        for node in class_node.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            methods.setdefault(node.name, set()).update(
                call.func.id if isinstance(call.func, ast.Name) else call.func.attr
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, (ast.Name, ast.Attribute))
            )

    read_roots = deque(("identity_card", "context", "memory_review_feed"))
    transitive_calls: set[str] = set()
    visited: set[str] = set()
    while read_roots:
        method = read_roots.popleft()
        if method in visited:
            continue
        visited.add(method)
        calls = methods.get(method, set())
        transitive_calls.update(calls)
        read_roots.extend(calls & methods.keys())

    forbidden_sinks = {
        "_commit", "add_folder_source", "add_github_source", "add_marginnote_source",
        "add_obsidian_source",
        "cancel_memory_confirmation",
        "cancel_privacy_purge", "cancel_restore", "clear_review_snooze", "confirm_privacy_purge",
        "confirm_restore", "correct", "create_backup", "decide_memory", "delete_index",
        "delete_memory_provider", "edit_memory", "export", "forget_memory_confirmed", "init",
        "memory_forget_preview", "memory_preview", "observe", "privacy_purge_preview",
        "promotion_records", "propose_from_host", "rebuild_index", "rebuild_memory_provider",
        "remember", "restore_preview", "retract", "review_memory", "set_module",
        "set_review_policy", "snooze_review", "sync", "with_switch",
    }
    assert not transitive_calls & forbidden_sinks


def test_default_and_incomplete_authority_deny_content(tmp_path: Path) -> None:
    service = _service(tmp_path)

    async def exercise() -> None:
        with pytest.raises(ToolError, match="mcp_scope_denied"):
            await create_server(service).call_tool("aptuni_get_identity_card", {"max_units": 512})
        no_egress_access = _access(
            scopes=frozenset({"identity.read"}), modules=frozenset({"identity"}), egress=False,
        )
        no_egress = create_server(service, no_egress_access)
        with pytest.raises(ToolError, match="host_model_egress_denied"):
            await no_egress.call_tool("aptuni_get_identity_card", {"max_units": 512})

    anyio.run(exercise)


def test_exact_scopes_modules_and_evidence_are_enforced(tmp_path: Path) -> None:
    service = _service(tmp_path)
    access = _access(scopes=frozenset({"identity.read", "context.read"}), modules=frozenset({"identity", "knowledge"}))
    server = create_server(service, access)

    async def exercise() -> None:
        identity = await server.call_tool("aptuni_get_identity_card", {"max_units": 700})
        assert not identity.is_error
        assert identity.structured_content["audience"] == "host_mcp"
        context = await server.call_tool(
            "aptuni_search_context",
            {"query": "survival", "modules": ["knowledge"], "max_units": 1000},
        )
        assert not context.is_error
        assert context.structured_content["used_units"] <= 1000
        assert context.structured_content["audience"] == "host_mcp"
        with pytest.raises(ToolError, match="mcp_module_denied"):
            await server.call_tool(
                "aptuni_search_context", {"query": "concise", "modules": ["preferences"]},
            )
        with pytest.raises(ToolError, match="mcp_scope_denied"):
            await server.call_tool(
                "aptuni_search_context",
                {"query": "survival", "modules": ["knowledge"], "include_evidence": True},
            )

    anyio.run(exercise)


def test_memory_review_needs_its_exact_scope_and_filters_modules(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.set_review_policy(pending_threshold=1)
    knowledge = service.observe("Uses reproducible experiment pipelines", "knowledge")
    service.observe("Prefers compact tables", "preferences")
    before = service.snapshot()[0]

    async def exercise() -> dict[str, object]:
        without_scope = _access(
            scopes=frozenset({"context.read"}), modules=frozenset({"knowledge"}),
        )
        with pytest.raises(ToolError, match="mcp_scope_denied"):
            await create_server(service, without_scope).call_tool(
                "aptuni_get_memory_review", {"max_units": 2000, "limit": 10},
            )
        no_egress = _access(
            scopes=frozenset({"memory.review.read"}), modules=frozenset({"knowledge"}), egress=False,
        )
        with pytest.raises(ToolError, match="host_model_egress_denied"):
            await create_server(service, no_egress).call_tool(
                "aptuni_get_memory_review", {"max_units": 2000, "limit": 10},
            )
        exact = _access(
            scopes=frozenset({"memory.review.read"}), modules=frozenset({"knowledge"}),
        )
        result = await create_server(service, exact).call_tool(
            "aptuni_get_memory_review", {"max_units": 2000, "limit": 10},
        )
        assert not result.is_error
        return result.structured_content or {}

    payload = anyio.run(exercise)
    assert service.snapshot()[0] == before, "an MCP review read must never commit"
    assert payload["audience"] == "host_mcp"
    assert payload["pending"] == 1
    assert payload["truncated"] is False
    assert payload["reminder"] == {
        "due": True,
        "next_due_at": payload["reminder"]["next_due_at"],
        "pending": 1,
        "reason": "threshold",
        "threshold": 1,
    }
    assert [item["canonical_id"] for item in payload["items"]] == [knowledge.memory_id]
    assert payload["items"][0]["review_state"] == "auto_promoted_pending_review"
    assert "compact tables" not in json.dumps(payload)


def test_core_proven_local_access_does_not_need_remote_egress_grant(tmp_path: Path) -> None:
    service = _service(tmp_path)
    access = HostContextAccess(
        "test-local",
        frozenset({"identity.read"}),
        frozenset({"identity"}),
        "proven_local",
        False,
    )

    async def exercise() -> None:
        result = await create_server(service, access).call_tool("aptuni_get_identity_card", {"max_units": 700})
        assert not result.is_error
        assert result.structured_content["audience"] == "host_mcp"

    anyio.run(exercise)


def test_real_stdio_health_default_deny_and_eof_shutdown(tmp_path: Path) -> None:
    async def exercise() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "aptuni.mcp.server"],
            env={"APTUNI_STATE_DIR": str(tmp_path / "missing-state")},
        )
        async with Client(params) as client:
            tools = await client.list_tools()
            assert len(tools.tools) == 5
            health = await client.call_tool("aptuni_health", {})
            assert health.structured_content == {
                "schema_version": 1,
                "status": "ok",
                "transport": "stdio",
                "personal_access_configured": False,
            }
            denied = await client.call_tool("aptuni_get_identity_card", {"max_units": 512})
            assert denied.is_error

    anyio.run(exercise)
    process = subprocess.run(
        [sys.executable, "-m", "aptuni.mcp.server"],
        input=b"",
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert process.returncode == 0
    assert process.stdout == b""


def test_process_network_canary_is_denied() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "aptuni.mcp.server", "--network-canary"],
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode != 0
    assert b"aptuni_mcp_network_denied" in result.stderr

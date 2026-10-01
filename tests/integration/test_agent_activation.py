from __future__ import annotations

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.adapters.manager import AdapterManager
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.mcp.server import create_server


def _ready(tmp_path):
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    service.remember("I prefer concise project-first explanations", "preferences")
    service.remember("I can build Python services", "skills")
    memory = service.observe("We are building an intelligent parking system", "projects")
    access = HostContextAccess(
        "beta-host",
        frozenset({"identity.read", "context.read", "evidence.read"}),
        frozenset({"preferences", "skills", "projects"}),
        "remote_unknown",
        True,
    )
    return service, memory.memory_id, access


def test_task_profile_is_single_use_and_next_ordinary_task_is_off(tmp_path) -> None:
    service, _, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {"query": "Python", "modules": ["skills"]})
        activated = await server.call_tool(
            "aptuni_activate_context",
            {
                "intent": "aptuni.profile", "scope": "task",
                "query": "How should I learn this project?", "modules": ["preferences", "skills"],
            },
        )
        payload = activated.structured_content
        assert payload["activation"] == {
            "intent": "aptuni.profile", "scope": "task", "session_mode": "off",
        }
        assert {item["kind"] for item in payload["context"]["items"] if item["layer"] == "L3"} == {"fact"}
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {"query": "parking", "modules": ["projects"]})

    anyio.run(exercise)


def test_task_profile_can_use_relevant_cold_start_evidence_without_calling_full(tmp_path) -> None:
    service, _, access = _ready(tmp_path)
    docs = tmp_path / "notes"
    docs.mkdir()
    (docs / "parking.md").write_text(
        "Intelligent parking systems need occupancy sensors and calibrated detection.",
        encoding="utf-8",
    )
    source = service.add_folder_source(docs, modules=("projects",), role="project_notes")
    service.sync(source.id)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        result = await server.call_tool(
            "aptuni_activate_context",
            {
                "intent": "aptuni.profile", "scope": "task", "query": "parking sensors",
                "modules": ["projects"], "max_units": 5000,
            },
        )
        items = result.structured_content["context"]["items"]
        assert "evidence" in {item["kind"] for item in items}
        assert result.structured_content["activation"]["session_mode"] == "off"

    anyio.run(exercise)


def test_task_memory_is_memory_only_and_creates_no_session_state(tmp_path) -> None:
    service, memory_id, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        result = await server.call_tool(
            "aptuni_activate_context",
            {
                "intent": "aptuni.memory", "scope": "task",
                "query": "What are we building?", "modules": ["projects"],
            },
        )
        items = result.structured_content["context"]["items"]
        assert [item["canonical_id"] for item in items if item["layer"] == "L3"] == [memory_id]
        status = await server.call_tool("aptuni_activation_status", {})
        assert status.structured_content == {
            "schema_version": 1, "mode": "off",
            "granted_modules": ["preferences", "projects", "skills"], "memory_proposals": "not_granted",
        }

    anyio.run(exercise)


def test_only_full_can_persist_for_session_and_disable_restores_off(tmp_path) -> None:
    service, _, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        with pytest.raises(ToolError, match="aptuni_session_scope_invalid"):
            await server.call_tool(
                "aptuni_activate_context",
                {
                    "intent": "aptuni.profile", "scope": "session",
                    "query": "Python", "modules": ["skills"],
                },
            )
        activated = await server.call_tool(
            "aptuni_activate_context",
            {
                "intent": "aptuni.full", "scope": "session",
                "query": "parking system", "modules": ["skills", "projects"],
            },
        )
        assert activated.structured_content["activation"]["session_mode"] == "full"
        status = await server.call_tool("aptuni_activation_status", {})
        assert status.structured_content == {
            "schema_version": 1, "mode": "full", "intent": "aptuni.full",
            "granted_modules": ["preferences", "projects", "skills"], "memory_proposals": "not_granted",
        }
        ordinary = await server.call_tool(
            "aptuni_search_context", {"query": "parking system", "modules": ["projects"]},
        )
        assert not ordinary.is_error
        disabled = await server.call_tool("aptuni_activation_disable", {})
        assert disabled.structured_content == {"schema_version": 1, "mode": "off", "changed": True}
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {"query": "parking", "modules": ["projects"]})

    anyio.run(exercise)

    fresh_server = create_server(service, access, activation_required=True)

    async def fresh() -> None:
        status = await fresh_server.call_tool("aptuni_activation_status", {})
        assert status.structured_content == {
            "schema_version": 1, "mode": "off",
            "granted_modules": ["preferences", "projects", "skills"], "memory_proposals": "not_granted",
        }

    anyio.run(fresh)


def test_live_adapter_revocation_stops_an_active_full_session(tmp_path) -> None:
    service, _, _ = _ready(tmp_path)
    manager = AdapterManager(service.workspace)
    plan = manager.plan("codex", ("skills", "projects"), allow_host_model_egress=True)
    grant, _ = manager.apply(plan.action_id)
    server = create_server(
        service,
        grant.access(),
        activation_required=True,
        access_provider=lambda: manager.load_grant(grant.grant_id).access(),
    )

    async def exercise() -> None:
        await server.call_tool(
            "aptuni_activate_context",
            {
                "intent": "aptuni.full", "scope": "session", "query": "parking",
                "modules": ["projects"],
            },
        )
        assert manager.revoke(grant.grant_id)
        with pytest.raises(ToolError, match="adapter_grant_not_found"):
            await server.call_tool(
                "aptuni_search_context", {"query": "parking", "modules": ["projects"]},
            )

    anyio.run(exercise)


def test_off_denies_every_personal_mcp_surface(tmp_path) -> None:
    service, _, access = _ready(tmp_path)
    access = HostContextAccess(
        access.principal,
        access.scopes | {"memory.review.read", "memory.propose"},
        access.modules,
        access.host_class,
        access.host_model_egress,
    )
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        calls = (
            ("aptuni_get_identity_card", {}),
            ("aptuni_get_memory_review", {}),
            ("aptuni_propose_memory", {"statement": "Remember this preference", "module": "preferences"}),
        )
        for tool, arguments in calls:
            with pytest.raises(ToolError, match="aptuni_activation_required"):
                await server.call_tool(tool, arguments)

    anyio.run(exercise)


def test_task_full_returns_relevant_profile_memory_and_evidence(tmp_path) -> None:
    service, _, access = _ready(tmp_path)
    service.remember("I can design intelligent parking systems", "skills")
    docs = tmp_path / "notes"
    docs.mkdir()
    (docs / "parking.md").write_text(
        "Intelligent parking systems need occupancy sensors and calibrated detection.",
        encoding="utf-8",
    )
    source = service.add_folder_source(docs, modules=("projects",), role="project_notes")
    service.sync(source.id)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        result = await server.call_tool(
            "aptuni_activate_context",
            {
                "intent": "aptuni.full", "scope": "task", "query": "parking",
                "modules": ["skills", "projects"], "max_units": 5000,
            },
        )
        items = result.structured_content["context"]["items"]
        assert {item["kind"] for item in items if item["layer"] in {"L3", "L4"}} == {
            "fact", "memory", "evidence",
        }
        assert result.structured_content["activation"]["session_mode"] == "off"

    anyio.run(exercise)


def test_active_session_revalidates_live_module_exposure(tmp_path) -> None:
    service, _, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await server.call_tool(
            "aptuni_activate_context",
            {
                "intent": "aptuni.full", "scope": "session", "query": "parking",
                "modules": ["projects"],
            },
        )
        service.set_module("projects", expose=False)
        result = await server.call_tool(
            "aptuni_search_context", {"query": "parking", "modules": ["projects"]},
        )
        assert not [
            item for item in result.structured_content["items"]
            if item["layer"] in {"L3", "L4"}
        ]

    anyio.run(exercise)

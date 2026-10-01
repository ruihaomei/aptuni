"""Activation refusals tell the Agent what to do next without disclosing personal content."""

from __future__ import annotations

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.adapters.manager import AdapterManager
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.mcp.server import create_server

READ_SCOPES = frozenset({"identity.read", "context.read", "evidence.read"})


def _service(tmp_path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    service.remember("I can build Python services", "skills")
    return service


def _access(scopes: frozenset[str] = READ_SCOPES) -> HostContextAccess:
    return HostContextAccess("beta-host", scopes, frozenset({"skills", "goals"}), "remote_unknown", True)


def test_module_denial_names_denied_and_granted_modules(tmp_path) -> None:
    server = create_server(_service(tmp_path), _access(), activation_required=True)

    async def exercise() -> None:
        with pytest.raises(ToolError) as denied:
            await server.call_tool("aptuni_activate_context", {
                "intent": "aptuni.full", "query": "Python", "modules": ["skills", "interests", "experience"],
            })
        message = str(denied.value)
        assert ": mcp_module_denied: " in message
        assert "not granted: experience, interests" in message
        assert "granted: goals, skills" in message
        assert "Python" not in message

    anyio.run(exercise)


def test_activation_status_lists_granted_modules_without_personal_content(tmp_path) -> None:
    server = create_server(_service(tmp_path), _access(), activation_required=True)

    async def exercise() -> None:
        status = (await server.call_tool("aptuni_activation_status", {})).structured_content
        assert status == {
            "schema_version": 1, "mode": "off", "granted_modules": ["goals", "skills"],
            "memory_proposals": "not_granted",
        }

    anyio.run(exercise)


def test_proposal_without_the_scope_says_the_grant_cannot_save_before_asking_for_session(tmp_path) -> None:
    server = create_server(_service(tmp_path), _access(), activation_required=True)

    async def exercise() -> None:
        with pytest.raises(ToolError) as denied:
            await server.call_tool(
                "aptuni_propose_memory", {"statement": "Goal: apply to grad school", "module": "goals"},
            )
        message = str(denied.value)
        assert ": mcp_scope_denied: " in message
        assert "memory.propose" in message and "--allow-memory-proposals" in message
        assert "grad school" not in message

    anyio.run(exercise)


def test_proposal_after_task_full_explains_session_requirement(tmp_path) -> None:
    access = _access(READ_SCOPES | {"memory.propose"})
    server = create_server(_service(tmp_path), access, activation_required=True)

    async def exercise() -> None:
        status = (await server.call_tool("aptuni_activation_status", {})).structured_content
        assert status["memory_proposals"] == "needs_session_full"
        await server.call_tool("aptuni_activate_context", {
            "intent": "aptuni.full", "scope": "task", "query": "Python", "modules": ["skills"],
        })
        with pytest.raises(ToolError) as denied:
            await server.call_tool("aptuni_propose_memory", {"statement": "Goal: apply", "module": "goals"})
        message = str(denied.value)
        assert ": aptuni_activation_required: " in message
        assert "scope=session" in message and "task-scoped" in message
        await server.call_tool("aptuni_activate_context", {
            "intent": "aptuni.full", "scope": "session", "query": "Python", "modules": ["skills"],
        })
        status = (await server.call_tool("aptuni_activation_status", {})).structured_content
        assert status["memory_proposals"] == "available"
        proposed = await server.call_tool("aptuni_propose_memory", {"statement": "Goal: apply", "module": "goals"})
        assert proposed.structured_content["status"] == "pending_owner_review"

    anyio.run(exercise)


def test_full_skill_explains_granted_modules_and_saving() -> None:
    text = AdapterManager._skill("full", "aptuni.full", claude=True)
    assert "aptuni_activation_status" in text
    assert "aptuni_propose_memory" in text and "scope=session" in text


def test_activation_status_survives_a_revoked_grant(tmp_path) -> None:
    def revoked() -> HostContextAccess:
        raise AptuniError("grant_revoked", "The grant was revoked.")

    server = create_server(_service(tmp_path), _access(), activation_required=True, access_provider=revoked)

    async def exercise() -> None:
        status = (await server.call_tool("aptuni_activation_status", {})).structured_content
        assert status == {
            "schema_version": 1, "mode": "off", "granted_modules": [], "memory_proposals": "not_granted",
        }

    anyio.run(exercise)

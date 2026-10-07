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


@pytest.mark.parametrize("claude", [True, False])
def test_skills_ask_for_a_few_specific_concepts_not_a_full_budget(claude: bool) -> None:
    """Agent-run evaluation (2026-10-02): padded concept lists add generic noise; a few specific ones win."""
    for intent in ("aptuni.profile", "aptuni.memory", "aptuni.full"):
        text = AdapterManager._skill("aptuni-x", intent, claude=claude)
        assert "Usually 1-4 concepts" in text and "ceiling, not a target" in text
        assert "not writing a syllabus" in text and "alternate name" in text
        assert "one consolidated retrieval call" in text and "Retry at most once" in text
        assert "generic" in text and "needs no Aptuni call" in text
        assert "an OFF session stays OFF" in text and "never enable session scope" in text
        assert "already enabled Full session stays enabled" in text
        assert "studied topic is not proof of mastery" in text
        assert "granted_modules" in text
        assert "1-8 short terms" not in text


def test_activation_tool_description_matches_the_concept_guidance(tmp_path) -> None:
    server = create_server(_service(tmp_path), _access(), activation_required=True)

    async def exercise() -> None:
        tools = {tool.name: tool for tool in await server.list_tools()}
        description = " ".join((tools["aptuni_activate_context"].description or "").split())
        assert "usually 1-4" in description and "never a target" in description
        assert "1-8 short terms" not in description
        search = " ".join((tools["aptuni_search_context"].description or "").split())
        assert "task-scoped activation creates no session authorization" in search
        assert "already enabled Full session stays enabled" in search
        assert "one consolidated call" in search and "Skip generic" in search

    anyio.run(exercise)


def test_task_activation_preserves_previously_enabled_full_session(tmp_path) -> None:
    """Task scope grants nothing persistent and does not disable prior explicit session consent."""
    server = create_server(_service(tmp_path), _access(), activation_required=True)

    async def exercise() -> None:
        for intent, scope, expected_mode in (
            ("aptuni.full", "task", "off"),
            ("aptuni.full", "session", "full"),
            ("aptuni.profile", "task", "full"),
        ):
            result = (await server.call_tool("aptuni_activate_context", {
                "intent": intent, "scope": scope, "query": "Python", "modules": ["skills"],
            })).structured_content
            assert result["activation"]["session_mode"] == expected_mode
        await server.call_tool("aptuni_search_context", {"query": "Python", "modules": ["skills"]})
        await server.call_tool("aptuni_activation_disable", {})
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {"query": "Python", "modules": ["skills"]})

    anyio.run(exercise)

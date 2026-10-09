"""ADR-0032 end to end: inventory → Evidence through the real MCP server and a real Vault."""
from __future__ import annotations

import json

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.application.candidates import _inventory_unit
from aptuni.application.context import METADATA_UNITS, unit_cost
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.mcp.server import create_server

SECRET = "API_KEY: sk-" + "test" + "1234567890" * 3
FULL = {"intent": "aptuni.full", "scope": "session", "query": "session setup", "modules": ["knowledge"],
        "concepts": ["aptuni_session_setup_no_matching_record"], "max_units": 32, "limit": 1}


def _ready(tmp_path, *, scopes=("context.read", "evidence.read")):
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    notes = tmp_path / "notes"
    (notes / "recollections").mkdir(parents=True)
    (notes / "recollections" / "robotics club.md").write_text("Led the robotics club build season.", "utf-8")
    (notes / "recollections" / "volunteering.md").write_text("Tutored maths at a community centre.", "utf-8")
    (notes / "keys.md").write_text(f"Deployment notes {SECRET}", "utf-8")
    source = service.add_folder_source(notes, modules=("knowledge",), role="recollections")
    service.sync(source.id)
    access = HostContextAccess("beta-host", frozenset(scopes), frozenset({"knowledge"}), "remote_unknown", True)
    return service, access


async def _call(server, name: str, arguments: dict) -> dict:
    return (await server.call_tool(name, arguments)).structured_content


def _inventory_rows(payload: dict) -> list[dict]:
    return [row for item in payload["items"] if item["kind"] == "candidate_inventory"
            for row in json.loads(item["text"])["candidates"]]


def test_inventory_then_evidence_inside_explicit_full(tmp_path) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        listed = await _call(server, "aptuni_search_context", {
            "query": "pick two of my extracurricular experiences", "modules": ["knowledge"],
            "mode": "inventory", "categories": ["documents"], "max_units": 20000})
        rows = _inventory_rows(listed)
        assert [row["label"] for row in rows] == ["recollections/robotics club", "recollections/volunteering"]
        assert all(item["tainted"] and item["layer"] == "L4" for item in listed["items"])
        fetched = await _call(server, "aptuni_search_context", {
            "query": "compare", "modules": ["knowledge"], "mode": "evidence",
            "candidates": [row["id"] for row in rows], "max_units": 10000})
        texts = [item["text"] for item in fetched["items"]]
        assert texts == ["Led the robotics club build season.", "Tutored maths at a community centre."]
        assert all(item["kind"] == "evidence" and item["canonical_id"] for item in fetched["items"])

    anyio.run(exercise)


def test_inventory_requires_explicit_full_session(tmp_path) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {
                "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"]})

    anyio.run(exercise)


def test_inventory_needs_evidence_scope_and_granted_modules(tmp_path) -> None:
    service, narrow = _ready(tmp_path, scopes=("context.read",))
    server = create_server(service, narrow, activation_required=True)

    async def without_evidence_scope() -> None:
        with pytest.raises(ToolError, match="mcp_scope_denied"):  # Full itself needs evidence.read
            await server.call_tool("aptuni_activate_context", FULL)
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {
                "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"]})

    anyio.run(without_evidence_scope)
    granted, access = _ready(tmp_path / "second")
    server = create_server(granted, access, activation_required=True)

    async def ungranted_module() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        with pytest.raises(ToolError, match="module"):
            await server.call_tool("aptuni_search_context", {
                "query": "q", "modules": ["projects"], "mode": "inventory", "categories": ["documents"]})

    anyio.run(ungranted_module)


def test_hidden_module_and_credentials_never_reach_inventory_or_evidence(tmp_path) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        listed = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"],
            "max_units": 20000})
        rows = _inventory_rows(listed)
        assert "keys" not in {row["label"] for row in rows}
        service.set_module("knowledge", expose=False)
        hidden = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"],
            "max_units": 20000})
        assert _inventory_rows(hidden) == []
        stale = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "evidence", "candidates": [rows[0]["id"]]})
        assert stale["items"] == []

    anyio.run(exercise)


def test_budget_truncates_rows_instead_of_dropping_the_category(tmp_path) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        full = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"],
            "max_units": 20000})
        first = _inventory_rows(full)[:1]
        one_row = METADATA_UNITS + unit_cost(_inventory_unit("documents", first))
        small = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"],
            "max_units": one_row + 10})
        assert len(_inventory_rows(small)) == 1
        assert small["truncated"] is True

    anyio.run(exercise)


@pytest.mark.parametrize("arguments", [
    {"mode": "inventory"},
    {"mode": "inventory", "categories": ["documents"], "concepts": ["robotics"]},
    {"mode": "inventory", "categories": ["documents"], "candidates": ["cd-000000000000"]},
    {"mode": "evidence"},
    {"mode": "evidence", "candidates": ["cd-000000000000"], "categories": ["documents"]},
    {"mode": "search", "categories": ["documents"]},
    {"mode": "evidence", "candidates": ["not-an-id"]},
])
def test_invalid_mode_combinations_are_refused(tmp_path, arguments) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        with pytest.raises(ToolError):
            await server.call_tool("aptuni_search_context", {"query": "q", "modules": ["knowledge"], **arguments})

    anyio.run(exercise)


def test_default_search_is_unchanged(tmp_path) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        result = await _call(server, "aptuni_search_context", {
            "query": "robotics club", "modules": ["knowledge"], "concepts": ["robotics club"], "max_units": 4000})
        assert not any(item["kind"] == "candidate_inventory" for item in result["items"])
        assert any("robotics club" in item["text"] for item in result["items"])

    anyio.run(exercise)


def test_rows_that_only_look_like_a_credential_together_do_not_empty_the_category(tmp_path) -> None:
    """Review N1: the last-line guard checks a whole unit, so rows are guarded as they accumulate."""
    service, access = _ready(tmp_path)
    notes = tmp_path / "odd"
    notes.mkdir()
    for name in ("x|password|y.md", "z| |Abc123xyz9.md", "real project.md"):
        (notes / name).write_text("Plain notes.", "utf-8")
    source = service.add_folder_source(notes, modules=("knowledge",), role="odd")
    service.sync(source.id)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        listed = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"],
            "max_units": 20000})
        labels = {row["label"] for row in _inventory_rows(listed)}
        assert "real project" in labels and "recollections/robotics club" in labels
        assert listed["truncated"] is True

    anyio.run(exercise)


def test_server_without_required_activation_and_task_full_cannot_list(tmp_path) -> None:
    service, access = _ready(tmp_path)

    async def exercise() -> None:
        legacy = create_server(service, access, activation_required=False)
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await legacy.call_tool("aptuni_search_context", {
                "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"]})
        server = create_server(service, access, activation_required=True)
        await _call(server, "aptuni_activate_context", {**FULL, "scope": "task"})
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {
                "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"]})

    anyio.run(exercise)


def test_stale_and_unknown_ids_are_indistinguishable_and_credentials_never_return(tmp_path) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        rows = _inventory_rows(await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "inventory", "categories": ["documents"],
            "max_units": 20000}))
        (tmp_path / "notes" / "recollections" / "volunteering.md").unlink()
        service.sync(next(s.id for s in service.sources()))
        stale_id = next(row["id"] for row in rows if row["label"].endswith("volunteering"))
        stale = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "evidence", "candidates": [stale_id]})
        unknown = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "evidence", "candidates": ["cd-000000000000"]})
        assert {k: v for k, v in stale.items() if k != "vault_seq"} == \
            {k: v for k, v in unknown.items() if k != "vault_seq"}
        everything = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "evidence", "candidates": [r["id"] for r in rows]})
        assert all("sk-test" not in item["text"] for item in everything["items"])

    anyio.run(exercise)


def test_budget_spent_on_an_earlier_category_reports_truncation(tmp_path) -> None:
    service, access = _ready(tmp_path)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        await _call(server, "aptuni_activate_context", FULL)
        both = await _call(server, "aptuni_search_context", {
            "query": "q", "modules": ["knowledge"], "mode": "inventory",
            "categories": ["documents", "subjects"], "max_units": 400})
        assert both["truncated"] is True
        assert [json.loads(item["text"])["category"] for item in both["items"]] in (["documents"], [])

    anyio.run(exercise)

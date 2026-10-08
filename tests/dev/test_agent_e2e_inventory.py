"""Candidate Inventory research stays inside the current grant, exposure and credential guards."""
from __future__ import annotations

import json
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace as NS

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.application.context import pack_units, response_from
from aptuni.application.service import HostContextAccess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from agent_e2e_inventory import create_server

SECRET = "API_KEY: sk-" + "test" + "1234567890" * 3


def record(identifier: str, schema: str, fields: dict, *, subject: str = "Item", text: str = "Documented.",
           exposed: bool = True) -> NS:
    return NS(id=identifier, record_type="evidence", module="knowledge", exposed=exposed, excerpt=text,
              statement=None, subject=subject, trust="untrusted_source", signals=("exposure",),
              provenance=NS(source_id="fixture-source", locator=NS(extension=NS(schema_name=schema, fields=fields))))


def repo(identifier: str, number: int, path: str, *, text: str = "Documented.", exposed: bool = True) -> NS:
    return record(identifier, "github.locator",
                  {"repository_id": number, "owner_name": f"invented/Project{number}", "path": path},
                  text=text, exposed=exposed)


def card(identifier: str, subject: str, depth: int, subtree: int) -> NS:
    return record(identifier, "marginnote.locator",
                  {"notebook_id": "nb", "depth": depth, "subtree_concepts": subtree}, subject=subject)


class Service:
    def __init__(self, rows: list[NS]) -> None:
        self.rows, self.seq = rows, 66

    def snapshot(self) -> tuple[int, NS]:
        return self.seq, NS(exposable=lambda: [row for row in self.rows if row.exposed])

    @staticmethod
    def policy_of(records: NS) -> NS:
        return NS(epoch=1)

    def context(self, query: str, **kwargs: object):
        budget = kwargs["budget"]
        return response_from(pack_units((), budget), budget=budget, vault_seq=self.seq, policy_epoch=1,
                             audience="host_mcp")


def access(*, scopes: tuple[str, ...] = ("context.read", "evidence.read")) -> HostContextAccess:
    return HostContextAccess("fixture-host", frozenset(scopes), frozenset({"knowledge"}), "remote_unknown", True)


async def call(server: object, name: str = "aptuni_search_context", **args: object) -> dict:
    return (await server.call_tool(name, args)).structured_content


async def setup(server: object) -> dict:
    return await call(server, "aptuni_activate_context", intent="aptuni.full", scope="session",
                      query="unmatched-setup", modules=["knowledge"], max_units=32)


ROWS = [
    repo("ev-a-src", 1, "src/a.py"), repo("ev-a-readme", 1, "README.md", text="# Project one does X"),
    repo("ev-b1", 2, "src/b.py"), repo("ev-hidden", 3, "README.md", exposed=False),
    repo("ev-secret", 4, "README.md", text=SECRET),
    record("ev-doc", "folder.locator", {"relative_path": "recollections/club.md"}),
    card("ev-root", "Statistics", 0, 40), card("ev-child", "Statistics › Tests", 1, 5),
    card("ev-small", "Tiny topic", 0, 3),
]


def test_inventory_lists_authorized_entities_without_query_terms_then_fetches_evidence() -> None:
    async def run() -> None:
        server = create_server(Service(list(ROWS)), access, nullcontext, expected_seq=66)
        assert (await setup(server))["context"]["items"] == []
        listed = await call(server, query="choose two of my projects", modules=["knowledge"], mode="inventory",
                            categories=["repositories", "documents", "subjects"], max_units=20000)
        by_kind = {item["kind"]: json.loads(item["text"]) for item in listed["items"]}
        assert by_kind["candidate_inventory:repositories"] == [
            {"id": "r001", "label": "Project1", "evidence": 2, "about": "Project one does X"},
            {"id": "r002", "label": "Project2", "evidence": 1}]
        assert by_kind["candidate_inventory:documents"] == [{"id": "d001", "label": "recollections/club"}]
        assert by_kind["candidate_inventory:subjects"] == [{"id": "s001", "label": "Statistics", "notes": 40}]
        result = await call(server, query="compare", modules=["knowledge"], mode="evidence",
                            candidates=["r001", "s001", "d001"], max_units=10000)
        assert [item["canonical_id"] for item in result["items"]] == [
            "ev-a-readme", "ev-root", "ev-doc", "ev-a-src", "ev-child"]
        assert all(item["tainted"] for item in result["items"])
    anyio.run(run)


def test_inventory_requires_full_and_refuses_unlisted_candidates_and_extra_calls() -> None:
    async def run() -> None:
        server = create_server(Service(list(ROWS)), access, nullcontext, expected_seq=66)
        with pytest.raises(ToolError):  # OFF: no inventory before explicit Full setup
            await call(server, query="q", modules=["knowledge"], mode="inventory", categories=["repositories"])
        server = create_server(Service(list(ROWS)), access, nullcontext, expected_seq=66)
        await setup(server)
        with pytest.raises(ToolError, match="research_unknown_candidate"):
            await call(server, query="q", modules=["knowledge"], mode="evidence", candidates=["r001"])
        await call(server, query="q", modules=["knowledge"], mode="inventory", categories=["repositories"])
        with pytest.raises(ToolError, match="research_unknown_candidate"):  # documents never listed
            await call(server, query="q", modules=["knowledge"], mode="evidence", candidates=["d001"])
        with pytest.raises(ToolError, match="research_call_limit"):
            await call(server, query="q", modules=["knowledge"], mode="evidence", candidates=["r001"])
    anyio.run(run)


def test_inventory_respects_grant_scope() -> None:
    async def run() -> None:
        server = create_server(Service(list(ROWS)), lambda: access(scopes=("context.read",)), nullcontext,
                               expected_seq=66)
        with pytest.raises(ToolError):
            await setup(server)
            await call(server, query="q", modules=["knowledge"], mode="inventory", categories=["repositories"])
    anyio.run(run)

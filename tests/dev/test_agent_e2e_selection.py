"""Selection coverage research stays bounded by the current host grant."""
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
from agent_e2e_selection import create_server


def evidence(identifier: str, repo: int, *, exposed: bool = True, text: str = "Documented method.",
             path: str = "src/module.py") -> NS:
    return NS(id=identifier, record_type="evidence", module="knowledge", exposed=exposed,
              excerpt=text, statement=None, subject="Project", trust="untrusted_source", signals=("exposure",),
              provenance=NS(source_id=f"fixture-{repo}", locator=NS(extension=NS(
                  schema_name="github.locator", fields={"repository_id": repo, "path": path,
                                                        "owner_name": f"invented/Project{repo}"}))))


class Service:
    def __init__(self, rows: list[NS]) -> None:
        self.rows = rows
        self.seq = 66

    def snapshot(self) -> tuple[int, NS]:
        return self.seq, NS(exposable=lambda: [row for row in self.rows if row.exposed])

    @staticmethod
    def policy_of(records: NS) -> NS:
        return NS(epoch=1)

    def context(self, query: str, **kwargs: object):
        budget = kwargs["budget"]
        return response_from(pack_units((), budget), budget=budget,
                             vault_seq=self.seq, policy_epoch=1, audience="host_mcp")


def access(*, scopes: tuple[str, ...] = ("context.read", "evidence.read"), egress: bool = True) -> HostContextAccess:
    return HostContextAccess("fixture-host", frozenset(scopes), frozenset({"knowledge"}),
                             "remote_unknown", egress)


async def call(server: object, name: str = "aptuni_search_context", **args: object) -> dict:
    return (await server.call_tool(name, args)).structured_content


async def setup(server: object) -> dict:
    return await call(server, "aptuni_activate_context", intent="aptuni.full", scope="session",
                      query="unmatched-setup", modules=["knowledge"], max_units=32)


def test_roster_then_multiple_group_evidence_keeps_ids_and_bounds() -> None:
    async def run() -> None:
        rows = [evidence("ev-a1", 1), evidence("ev-a2", 1), evidence("ev-b1", 2), evidence("ev-b2", 2),
                evidence("ev-hidden", 3, exposed=False),
                evidence("ev-secret", 4, text="API_KEY: sk-" + "test" + "1234567890" * 3),
                NS(record_type="source_config", module="knowledge", exposed=True)]
        server = create_server(Service(rows), access, nullcontext, expected_seq=66)
        assert len(await server.list_tools()) == 4
        assert (await call(server, "aptuni_activation_status"))["mode"] == "off"
        assert (await setup(server))["context"]["items"] == []
        roster = await call(server, query="choose projects", modules=["knowledge"], mode="roster",
                            max_units=1400)
        entries = json.loads(roster["items"][0]["text"])
        assert entries == [{"anchor": "a01", "label": "Project1"},
                           {"anchor": "a02", "label": "Project2"}]
        result = await call(server, query="compare", modules=["knowledge"], mode="evidence",
                            anchors=["a01", "a02"], max_units=2600)
        assert [item["canonical_id"] for item in result["items"]] == ["ev-a1", "ev-b1", "ev-a2", "ev-b2"]
        assert all(item["tainted"] and item["source_id"] for item in result["items"])
        assert server.task_calls == 2 and server.task_used_units <= 4000
        with pytest.raises(ToolError, match="research_call_limit"):
            await call(server, query="again", modules=["knowledge"], mode="roster")
    anyio.run(run)


def test_revocation_withdrawal_snapshot_and_off_are_fail_closed() -> None:
    async def run() -> None:
        row = evidence("ev-a1", 1)
        service = Service([row])
        current = access()
        server = create_server(service, lambda: current, nullcontext, expected_seq=66)
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await call(server, query="work", modules=["knowledge"], mode="roster")
        assert server.task_calls == 1
        server = create_server(service, lambda: current, nullcontext, expected_seq=66)
        await setup(server)
        await call(server, query="work", modules=["knowledge"], mode="roster")
        current = access(scopes=("context.read",))
        with pytest.raises(ToolError, match="mcp_scope_denied"):
            await call(server, query="work", modules=["knowledge"], mode="evidence", anchors=["a01"])
        server = create_server(service, access, nullcontext, expected_seq=66)
        await setup(server)
        await call(server, query="work", modules=["knowledge"], mode="roster")
        row.exposed = False
        assert (await call(server, query="work", modules=["knowledge"], mode="evidence",
                           anchors=["a01"]))["items"] == []
        server = create_server(service, access, nullcontext, expected_seq=66)
        await setup(server)
        service.seq = 67
        with pytest.raises(ToolError, match="research_snapshot_changed"):
            await call(server, query="work", modules=["knowledge"], mode="roster")
    anyio.run(run)


def test_roster_is_bounded_and_unknown_anchor_discloses_nothing() -> None:
    async def run() -> None:
        server = create_server(Service([evidence(f"ev-{i}", i) for i in range(1, 18)]),
                               access, nullcontext, expected_seq=66)
        await setup(server)
        roster = await call(server, query="work", modules=["knowledge"], mode="roster", max_units=1400)
        entries = json.loads(roster["items"][0]["text"])
        assert 1 <= len(entries) <= 12 and roster["truncated"]
        result = await call(server, query="work", modules=["knowledge"], mode="evidence",
                            anchors=["a99"], max_units=2600)
        assert result["items"] == []
    anyio.run(run)


def test_exactly_three_records_is_not_reported_as_omitted() -> None:
    async def run() -> None:
        rows = [evidence(f"ev-{i}", 1) for i in range(3)]
        server = create_server(Service(rows), access, nullcontext, expected_seq=66)
        await setup(server)
        await call(server, query="work", modules=["knowledge"], mode="roster", max_units=1400)
        result = await call(server, query="work", modules=["knowledge"], mode="evidence",
                            anchors=["a01"], max_units=2600)
        assert len(result["items"]) == 3
        assert result["truncated"] is False
    anyio.run(run)


def test_limit_omission_is_reported() -> None:
    async def run() -> None:
        rows = [evidence("ev-a1", 1), evidence("ev-a2", 1),
                evidence("ev-b1", 2), evidence("ev-b2", 2)]
        server = create_server(Service(rows), access, nullcontext, expected_seq=66)
        await setup(server)
        await call(server, query="work", modules=["knowledge"], mode="roster", max_units=1400)
        result = await call(server, query="work", modules=["knowledge"], mode="evidence",
                            anchors=["a01", "a02"], max_units=2600, limit=1)
        assert len(result["items"]) == 1
        assert result["truncated"] is True
    anyio.run(run)


def test_readme_is_first_evidence_without_using_task_terms() -> None:
    async def run() -> None:
        rows = [evidence("ev-a", 1, path="src/a.py"),
                evidence("ev-b", 1, path="src/b.py"),
                evidence("ev-z", 1, path="README.md", text="Project overview.")]
        server = create_server(Service(rows), access, nullcontext, expected_seq=66)
        await setup(server)
        await call(server, query="work", modules=["knowledge"], mode="roster", max_units=1400)
        result = await call(server, query="work", modules=["knowledge"], mode="evidence",
                            anchors=["a01"], max_units=2600)
        assert [item["canonical_id"] for item in result["items"]] == ["ev-z", "ev-a", "ev-b"]
    anyio.run(run)

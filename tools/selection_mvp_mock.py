#!/usr/bin/env python3
"""Disposable selection experiment over invented Evidence, never the owner Vault.

All arms see the same permitted records, explicit Full setup, two or three counted
retrievals, and a shared 4000-unit cap. The candidate topology is derived from
source grouping metadata and has no relationship to physical Vault layout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any, Literal

import anyio
from agent_e2e_mock import CONTROL, READ_ONLY, Anchor, Budget, Concepts, Limit, Modules, Query, ResearchServer
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from aptuni.application.context import ContextUnit
from aptuni.domain.records import Module

Ids = Annotated[list[Annotated[str, Field(min_length=1, max_length=80)]] | None,
                Field(max_length=3)]


class SelectionServer(ResearchServer):
    def __init__(self, fixture: Path, case: str, arm: str, state_dir: Path) -> None:
        if arm not in {"baseline", "auto", "directed"}:
            raise ValueError("invalid selection arm")
        super().__init__(fixture, case, "baseline", state_dir)
        self.variant = arm
        self.visible: dict[str, str] = {}
        self.dispatch_lock = anyio.Lock()

    async def call_tool(self, name: str, arguments: dict[str, Any], context: Any = None) -> Any:
        async with self.dispatch_lock:
            retrieval = name in {"aptuni_activate_context", "aptuni_search_context"}
            setup = (name == "aptuni_activate_context" and not self.setup_consumed and self.task_calls == 0
                     and arguments.get("intent") == "aptuni.full" and arguments.get("scope") == "session"
                     and arguments.get("max_units") == 32 and arguments.get("modules") == ["knowledge"])
            self.in_setup = setup
            if setup:
                self.setup_consumed = True
            elif retrieval:
                self.task_calls += 1
                if self.task_calls > 3:
                    self.in_setup = False
                    raise ToolError("research_call_limit")
            try:
                return await MCPServer.call_tool(self, name, arguments, context)
            except Exception:
                if setup:
                    self.task_calls += 1
                raise
            finally:
                self.in_setup = False

    def retrieve(self, query: str, modules: list[Module], max_units: int, limit: int,
                 concepts: list[str] | None, mode: str = "search", anchor: str | None = None,
                 ids: list[str] | None = None, *, require_session: bool = True) -> dict[str, object]:
        if require_session and not self.full:
            raise ToolError("aptuni_activation_required")
        self.check_modules(modules)
        if self.variant == "baseline":
            if mode != "search" or anchor is not None or ids is not None:
                raise ToolError("research_invalid_mode")
            return super().retrieve(query, modules, max_units, limit, concepts, require_session=require_session)
        if mode == "search":
            return super().retrieve(query, modules, max_units, limit, concepts, require_session=require_session)
        if mode == "coverage":
            if anchor is not None or ids is not None:
                raise ToolError("research_invalid_mode")
            # Same source-group metadata for both arms. The directed arm may ask
            # for a narrower label match; an empty match is never called absence.
            rows = [(key, label) for key, label, ref in self.catalog
                    if ref in self.records and self.records[ref].permitted()
                    and self.records[ref].repository_id == key]
            if self.variant == "directed" and query.strip() != "all candidates":
                terms = [term.casefold() for term in query.split() if len(term) > 2]
                narrowed = [(key, label) for key, label in rows
                            if any(term in label.casefold() for term in terms)]
                if narrowed:
                    rows = narrowed
            rows = rows[:8]
            self.visible.update({key: key for key, _ in rows})
            packet = json.dumps([{"id": key, "label": label[:48]} for key, label in rows],
                                ensure_ascii=False, separators=(",", ":"))
            unit = ContextUnit("L1", "candidate_index", None, "knowledge", packet,
                               None, "untrusted_source", True, ())
            return self.response((unit,), min(max_units, 1000))
        if mode == "get":
            if anchor is not None or not ids or len(ids) > 3:
                raise ToolError("research_invalid_mode")
            admitted = set(ids) & self.visible.keys()
            evidence_rows = [row for row in self.records.values()
                             if row.repository_id in admitted and row.permitted()]
            evidence_rows.sort(key=lambda row: row.identifier)
            return self.response(tuple(row.unit() for row in evidence_rows[:limit]), max_units)
        raise ToolError("research_invalid_mode")


def create_server(fixture: Path, case: str, arm: str, state_dir: Path) -> SelectionServer:
    server = SelectionServer(fixture, case, arm, state_dir)

    @server.tool(name="aptuni_activation_status", annotations=READ_ONLY)
    def status() -> dict[str, object]:
        """Inspect current activation and granted modules without personal context."""
        return server.status()

    @server.tool(name="aptuni_activation_disable", annotations=CONTROL)
    def disable() -> dict[str, object]:
        """Disable Full; retrieval counters and permission stay unchanged."""
        changed, server.full = server.full, False
        return {"schema_version": 1, "mode": "off", "changed": changed}

    @server.tool(name="aptuni_activate_context", annotations=CONTROL)
    def activate(intent: Literal["aptuni.profile", "aptuni.memory", "aptuni.full"], query: Query,
                 modules: Modules, scope: Literal["task", "session"] = "task", max_units: Budget = 1500,
                 limit: Limit = 20, concepts: Concepts = None) -> dict[str, object]:
        """Use only for explicit Full session setup in this invented-record experiment."""
        server.check_modules(modules)
        if intent != "aptuni.full" or not server.in_setup or scope != "session":
            raise ToolError("research_setup_only")
        result = server.response((), 32)
        server.full = True
        return {"schema_version": 1, "activation": {"intent": intent, "scope": scope,
                "session_mode": "full"}, "context": result}

    if arm == "baseline":
        @server.tool(name="aptuni_search_context", annotations=READ_ONLY)
        def search(query: Query, modules: Modules, max_units: Budget = 1500, limit: Limit = 20,
                   include_evidence: bool = False, concepts: Concepts = None) -> dict[str, object]:
            """Return bounded relevant context inside explicitly enabled Full.
            Choose a few specific concepts. A study mention does not prove contribution.
            """
            return server.retrieve(query, modules, max_units, limit, concepts)
    else:
        @server.tool(name="aptuni_search_context", annotations=READ_ONLY)
        def navigate(query: Query, modules: Modules, max_units: Budget = 1500, limit: Limit = 20,
                     include_evidence: bool = False, concepts: Concepts = None,
                     mode: Literal["coverage", "get", "search"] = "search", ids: Ids = None,
                     anchor: Anchor = None) -> dict[str, object]:
            """Bounded knowledge retrieval inside explicit Full, with no permission controls.
            coverage lists at most eight source-group IDs and short untrusted labels;
            get hydrates at most three previously listed IDs with source citations;
            search uses ordinary context ranking. Three calls share 4000 units.
            Labels never prove contribution. Empty results do not prove absence.
            """
            return server.retrieve(query, modules, max_units, limit, concepts, mode, anchor, ids)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--arm", choices=("baseline", "auto", "directed"), required=True)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="aptuni-selection-mvp-") as directory:
        create_server(args.fixture, args.case, args.arm, Path(directory)).run(transport="stdio")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Disposable Candidate Inventory MCP for the b10 unnamed-selection study (research only).

Not a production interface. It inherits the reviewed grant, explicit-Full, module, exposure,
credential, snapshot and effect guards from the discovery seam, keeps ordinary concept search
unchanged, and adds two modes for choosing among the user's own unnamed items:

* ``inventory``: a category-scoped list of authorized candidate entities derived from existing
  provenance (GitHub repositories, folder documents, MarginNote root topics). No query terms
  are used, so the Agent need not guess candidate names.
* ``evidence``: Evidence for up to six disclosed candidate IDs, round-robin across candidates.
"""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Annotated, Any, Literal, TypeVar

from agent_e2e_discovery import DiscoveryServer, install_guard
from agent_e2e_mock import CONTROL, READ_ONLY, RETRIEVAL_TOOLS, Budget, Concepts, Limit, Modules, Query
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from aptuni.adapters.manager import AdapterManager
from aptuni.application.context import ContextUnit, pack_units, record_unit, response_from
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.mcp.server import _context_json, _tool_error
from aptuni.policy.secrets import contains_credential

Result = TypeVar("Result")
Category = Literal["repositories", "documents", "subjects"]
Categories = Annotated[list[Category] | None, Field(max_length=3)]
CandidateIds = Annotated[list[Annotated[str, Field(pattern=r"^[rds][0-9]{3}$")]] | None, Field(max_length=6)]
TASK_CALLS = 3
TASK_UNITS = 32_000
INVENTORY_UNITS = 20_000
EVIDENCE_UNITS = 10_000
PER_CANDIDATE = 3
SUBJECT_MIN_DESCENDANTS = 20
SUBJECT_LIMIT = 100
DESCRIPTOR_BYTES = 90
SEPARATOR = "›"


def _fields(record: Any) -> tuple[str | None, dict[str, Any]]:
    locator = record.provenance.locator
    if locator is None or locator.extension is None:
        return None, {}
    return locator.extension.schema_name, locator.extension.fields


def _plain(text: str) -> str:
    """Drop HTML tags, Markdown images/badges and link targets so a descriptor carries words only."""
    text = re.sub(r"<[^>]*(>|$)", " ", text)  # excerpts may end inside a tag
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return " ".join(text.replace("#", " ").split())


def _clip(text: str, limit: int) -> str:
    raw = " ".join(text.split()).encode("utf-8")
    return text if len(raw) <= limit else raw[:limit - 3].decode("utf-8", errors="ignore") + "…"


def _descendants(value: object) -> int:
    return value if isinstance(value, int) else len(value) if isinstance(value, list | tuple) else 0


def _readme_rank(record: Any) -> tuple[int, int, str]:
    """A repository's shallowest README first, then shallow paths, then stable IDs."""
    _, fields = _fields(record)
    path = fields.get("path") if isinstance(fields.get("path"), str) else ""
    readme = path.rsplit("/", 1)[-1].casefold().startswith("readme")
    return (0 if readme else 1, path.count("/") if path else 9, record.id)


def build_inventory(eligible: Sequence[Any]) -> dict[str, list[tuple[str, dict[str, object], list[Any]]]]:
    """Group exposable Evidence into candidate entities per category, using provenance only."""
    repos: dict[int, dict[str, Any]] = {}
    documents: dict[str, list[Any]] = {}
    roots: dict[tuple[str, str], dict[str, Any]] = {}
    for record in eligible:
        schema, fields = _fields(record)
        if schema in {"github.locator", "github.concept"}:
            identifier, owner_name = fields.get("repository_id"), fields.get("owner_name")
            if type(identifier) is int and isinstance(owner_name, str) \
                    and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", owner_name):
                group = repos.setdefault(identifier, {"label": owner_name.rsplit("/", 1)[-1], "records": []})
                group["records"].append(record)
        elif schema == "folder.locator" and isinstance(fields.get("relative_path"), str):
            documents.setdefault(fields["relative_path"], []).append(record)
        elif schema == "marginnote.locator":
            title = str(record.subject).split(SEPARATOR)[0].strip()
            key = (str(fields.get("notebook_id")), title.casefold())
            root = roots.setdefault(key, {"label": title, "size": 0, "records": []})
            root["records"].append(record)
            if fields.get("depth") == 0:
                root["size"] = max(root["size"], _descendants(fields.get("subtree_concepts")))
    inventory: dict[str, list[tuple[str, dict[str, object], list[Any]]]] = {
        "repositories": [], "documents": [], "subjects": []}
    for index, identifier in enumerate(sorted(repos, key=lambda key: repos[key]["label"].casefold()), 1):
        group = repos[identifier]
        records = sorted(group["records"], key=_readme_rank)
        row: dict[str, object] = {"id": f"r{index:03d}", "label": group["label"], "evidence": len(records)}
        about = getattr(records[0], "excerpt", "") or ""
        if _readme_rank(records[0])[0] == 0 and about:
            about = _plain(about)
            if about:
                row["about"] = _clip(about, DESCRIPTOR_BYTES)
        inventory["repositories"].append((row["id"], row, records))
    for index, path in enumerate(sorted(documents), 1):
        label = path.rsplit(".", 1)[0] if "." in path.rsplit("/", 1)[-1] else path
        inventory["documents"].append((f"d{index:03d}", {"id": f"d{index:03d}", "label": label},
                                       sorted(documents[path], key=lambda record: record.id)))
    seen: set[str] = set()
    ranked = sorted((root for root in roots.values() if root["size"] >= SUBJECT_MIN_DESCENDANTS),
                    key=lambda root: (-root["size"], root["label"].casefold()))
    for root in ranked:
        if root["label"].casefold() in seen or len(inventory["subjects"]) >= SUBJECT_LIMIT:
            continue
        seen.add(root["label"].casefold())
        identifier = f"s{len(inventory['subjects']) + 1:03d}"

        def depth_rank(record: Any) -> tuple[int, int, str]:
            _, fields = _fields(record)
            return (int(fields.get("depth") or 0), -_descendants(fields.get("subtree_concepts")), record.id)
        records = sorted(root["records"], key=depth_rank)
        inventory["subjects"].append((identifier, {"id": identifier, "label": root["label"],
                                                   "notes": root["size"]}, records))
    # Labels and descriptors are disclosed context: drop any that look like a credential.
    return {name: [entry for entry in rows if not contains_credential(json.dumps(entry[1], ensure_ascii=False))]
            for name, rows in inventory.items()}


class InventoryServer(DiscoveryServer):
    """Ordinary search plus a research-only inventory → evidence path; three counted calls."""

    def __init__(self, service: Any, access: Callable[[], HostContextAccess],
                 authorization: Callable[[], AbstractContextManager[Any]], expected_seq: int) -> None:
        super().__init__(service, access, authorization, expected_seq)
        self.candidates: dict[str, list[str]] = {}

    async def call_tool(self, name: str, arguments: dict[str, Any], context: Any = None) -> Any:
        async with self.dispatch_lock:
            setup = (name == "aptuni_activate_context" and not self.setup_consumed and self.task_calls == 0
                     and arguments.get("intent") == "aptuni.full" and arguments.get("scope") == "session"
                     and arguments.get("max_units") == 32 and arguments.get("modules") == ["knowledge"])
            self.in_setup = setup
            if setup:
                self.setup_consumed = True
            elif name in RETRIEVAL_TOOLS:
                self.task_calls += 1
                if self.task_calls > TASK_CALLS:
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

    def emit(self, candidates: tuple[ContextUnit, ...], budget: int, records: Any,
             *, omitted: bool = False) -> dict[str, object]:
        amount = min(budget, TASK_UNITS - self.task_used_units)
        if amount < 32:
            raise ToolError("research_unit_limit")
        packed = pack_units(candidates, amount)
        if self.service.snapshot()[0] != self.expected_seq:
            raise AptuniError("research_snapshot_changed", "Discard this development probe.")
        self.task_used_units += packed.used_units
        return _context_json(response_from(packed, budget=amount, vault_seq=self.expected_seq,
                                           policy_epoch=self.service.policy_of(records).epoch,
                                           audience="host_mcp", more_results=omitted))

    def retrieve_inventory(self, query: str, modules: list[Any], max_units: int, limit: int,
                           concepts: list[str] | None, mode: str, categories: list[str] | None,
                           candidates: list[str] | None) -> dict[str, object]:
        with self.authorization():
            _, records = self.snapshot(modules)
            if mode == "search":
                if categories or candidates:
                    raise ToolError("research_invalid_mode")
                budget = min(max_units, TASK_UNITS - self.task_used_units)
                if budget < 32:
                    raise ToolError("research_unit_limit")
                value = self.activation.session_context(query, modules=tuple(modules), budget=budget,
                                                        limit=limit, concepts=tuple(concepts or ()))
                if self.service.snapshot()[0] != self.expected_seq:
                    raise AptuniError("research_snapshot_changed", "Discard this development probe.")
                self.task_used_units += value.used_units
                return _context_json(value)
            if modules != ["knowledge"]:
                raise ToolError("research_knowledge_only")
            inventory = build_inventory(self.eligible(records, modules))
            if mode == "inventory":
                if not categories or candidates or len(set(categories)) != len(categories):
                    raise ToolError("research_inventory_categories")
                units, disclosed = [], {}
                for category in categories:
                    rows = inventory[category]
                    units.append(ContextUnit("L4", f"candidate_inventory:{category}", None, "knowledge",
                                             json.dumps([row for _, row, _ in rows], ensure_ascii=False,
                                                        separators=(",", ":")),
                                             None, "untrusted_source", True, ()))
                    disclosed.update({identifier: [record.id for record in group] for identifier, _, group in rows})
                result = self.emit(tuple(units), min(max_units, INVENTORY_UNITS), records)
                kept = {item["kind"].split(":", 1)[1] for item in result["items"]}
                self.candidates.update({key: value for key, value in disclosed.items()
                                        if {"r": "repositories", "d": "documents", "s": "subjects"}[key[0]] in kept})
                if len(kept) < len(categories):
                    result["more_results"] = True
                return result
            if mode != "evidence" or not candidates or categories or len(set(candidates)) != len(candidates):
                raise ToolError("research_evidence_sequence")
            current = {record.id: record for _, rows in inventory.items() for _, _, group in rows for record in group}
            groups = [[current[ref] for ref in self.candidates.get(key, []) if ref in current] for key in candidates]
            if any(not group for group in groups):
                raise ToolError("research_unknown_candidate")
            ordered: list[Any] = []
            for index in range(PER_CANDIDATE):
                ordered.extend(group[index] for group in groups if index < len(group))
            admitted = ordered[:min(limit, PER_CANDIDATE * len(groups))]
            return self.emit(tuple(record_unit(record) for record in admitted), min(max_units, EVIDENCE_UNITS),
                             records, omitted=any(len(group) > PER_CANDIDATE for group in groups))


def create_server(service: Any, access: Callable[[], HostContextAccess],
                  authorization: Callable[[], AbstractContextManager[Any]], *,
                  expected_seq: int) -> InventoryServer:
    server = InventoryServer(service, access, authorization, expected_seq)

    def safe(operation: Callable[[], Result]) -> Result:
        try:
            return operation()
        except AptuniError as error:
            raise _tool_error(error) from None
        except ToolError:
            raise
        except Exception:
            raise ToolError("research_backend_failed") from None

    @server.tool(name="aptuni_activation_status", annotations=READ_ONLY)
    def status() -> dict[str, object]:
        """Inspect session activation and the grant's modules without returning personal context."""
        return safe(server.status)

    @server.tool(name="aptuni_activation_disable", annotations=CONTROL)
    def disable() -> dict[str, object]:
        """Disable explicit session Full activation; subsequent ordinary tasks are Aptuni-OFF."""
        return server.activation.disable()

    @server.tool(name="aptuni_activate_context", annotations=CONTROL)
    def activate(intent: Literal["aptuni.profile", "aptuni.memory", "aptuni.full"], query: Query,
                 modules: Modules, scope: Literal["task", "session"] = "task", max_units: Budget = 1500,
                 limit: Limit = 20, concepts: Concepts = None) -> dict[str, object]:
        """Explicit owner Full setup only in this research seam; no automatic OFF-to-Full."""
        def operation() -> dict[str, object]:
            with authorization():
                server.snapshot(modules, require_full=False)
                if not server.in_setup or intent != "aptuni.full" or scope != "session" \
                        or modules != ["knowledge"]:
                    raise ToolError("research_session_setup_only")
                try:
                    value = server.activation.activate(intent, scope, query, modules=("knowledge",),
                                                       budget=max_units, limit=limit,
                                                       concepts=tuple(concepts or ()))
                    if value.items or service.snapshot()[0] != expected_seq:
                        raise ToolError("research_setup_not_empty_or_snapshot_changed")
                except Exception:
                    server.activation.disable()
                    raise
                return {"schema_version": 1, "activation": {"intent": intent, "scope": scope,
                        "session_mode": "full"}, "context": _context_json(value)}
        return safe(operation)

    @server.tool(name="aptuni_search_context", annotations=READ_ONLY)
    def search(query: Query, modules: Modules, max_units: Budget = 1500, limit: Limit = 20,
               include_evidence: bool = False, concepts: Concepts = None,
               mode: Literal["search", "inventory", "evidence"] = "search",
               categories: Categories = None, candidates: CandidateIds = None) -> dict[str, object]:
        """Retrieve only when personal context materially changes the answer, within an explicitly
        enabled Full session. mode="search" (default): plan once, one consolidated call with usually
        1-4 specific concepts; retry at most once with an alternate term; context is evidence, not mastery.
        For choosing, ranking or comparing the user's own items that the request does not name, use
        mode="inventory" with categories (repositories = code projects, documents = the user's own
        notes and recollections, subjects = studied topics) to list the authorized candidates; labels
        are clues only. Then mode="evidence" with up to six listed candidate IDs; judge eligibility
        only from that Evidence. Three task calls in total; modules=["knowledge"] for these modes;
        inventory max_units up to 20000, evidence up to 10000."""
        return safe(lambda: server.retrieve_inventory(query, modules, max_units, limit, concepts, mode,
                                                      categories, candidates))
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grant", required=True)
    parser.add_argument("--expected-seq", required=True, type=int)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args()
    workspace = Workspace.default()
    service = AptuniService(workspace)
    manager = AdapterManager(workspace)
    authorization = install_guard(workspace, args.private_root)
    create_server(service, lambda: manager.load_grant(args.grant).access(), authorization,
                  expected_seq=args.expected_seq).run(transport="stdio")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Disposable bounded candidate-coverage MCP for the b10 real selection study.

This is not a production interface. It inherits the reviewed real-data grant,
activation, exposure, snapshot, effect and two-call guards from discovery.
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
from agent_e2e_mock import CONTROL, READ_ONLY, Budget, Concepts, Limit, Modules, Query
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from aptuni.adapters.manager import AdapterManager
from aptuni.application.context import ContextUnit, record_unit, unit_cost
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.mcp.server import _context_json, _tool_error
from aptuni.policy.secrets import contains_credential

Result = TypeVar("Result")
RosterIds = Annotated[list[Annotated[str, Field(pattern=r"^a[0-9]{2}$")]] | None,
                      Field(max_length=3)]
ROSTER_LIMIT = 12
ROSTER_UNITS = 1400
EVIDENCE_UNITS = 2600


def evidence_order(record: Any) -> tuple[int, int, str]:
    """Prefer a source's overview, then use stable IDs without task-specific terms."""
    locator = record.provenance.locator
    fields = locator.extension.fields if locator is not None else {}
    path = fields.get("path") if locator is not None and locator.extension.schema_name == "github.locator" else None
    path = path if isinstance(path, str) else ""
    readme = path.rsplit("/", 1)[-1].casefold() in {"readme.md", "readme.rst", "readme.txt"}
    return (0 if readme else 1, path.count("/") if readme else 0, record.id)


class SelectionServer(DiscoveryServer):
    """List a bounded authorized source-group roster, then fetch multiple groups."""

    def __init__(self, service: Any, access: Callable[[], HostContextAccess],
                 authorization: Callable[[], AbstractContextManager[Any]], expected_seq: int) -> None:
        super().__init__(service, access, authorization, expected_seq)
        self.selection_refs: dict[str, frozenset[str]] = {}

    def retrieve_selection(  # noqa: PLR0912, PLR0915 - keep authorization and disclosure in one lock
                           self, modules: Sequence[str], max_units: int, limit: int,
                           mode: str, anchors: list[str] | None) -> dict[str, object]:
        with self.authorization():
            _, records = self.snapshot(modules)
            if modules != ["knowledge"]:
                raise ToolError("research_knowledge_only")
            eligible = self.eligible(records, modules)
            if mode == "roster":
                if self.task_calls != 1 or anchors is not None:
                    raise ToolError("research_roster_sequence")
                groups: dict[str, dict[str, set[str]]] = {}
                for record in eligible:
                    locator = record.provenance.locator
                    if locator is None or locator.extension.schema_name not in {"github.locator", "github.concept"}:
                        continue
                    fields = locator.extension.fields
                    identifier, owner_name = fields.get("repository_id"), fields.get("owner_name")
                    if type(identifier) is not int or identifier <= 0 or not isinstance(owner_name, str) \
                            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", owner_name):
                        continue
                    label = owner_name.rsplit("/", 1)[-1]
                    if contains_credential(label):
                        continue
                    group = groups.setdefault(f"repo-{identifier}", {"labels": set(), "refs": set()})
                    group["labels"].add(label)
                    group["refs"].add(record.id)
                ordered = sorted(groups)
                selected = ordered[:ROSTER_LIMIT]
                # The roster is one packed unit. Shorten the deterministic prefix until it fits.
                unit: ContextUnit | None = None
                mapping: dict[str, frozenset[str]] = {}
                for count in range(len(selected), 0, -1):
                    rows = []
                    candidate_map = {}
                    labels = set()
                    for index, key in enumerate(selected[:count], 1):
                        label = sorted(groups[key]["labels"])[0]
                        raw = label.encode("utf-8")
                        label = raw[:45].decode("utf-8", errors="ignore") + "…" if len(raw) > 48 else label
                        if label.casefold() in labels:
                            raise ToolError("research_label_ambiguity")
                        labels.add(label.casefold())
                        anchor = f"a{index:02d}"
                        rows.append({"anchor": anchor, "label": label})
                        candidate_map[anchor] = frozenset(groups[key]["refs"])
                    candidate = ContextUnit("L4", "candidate_roster", None, "knowledge",
                                            json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
                                            None, "untrusted_source", True, ())
                    if 32 + unit_cost(candidate) <= min(max_units, ROSTER_UNITS):
                        unit, mapping = candidate, candidate_map
                        break
                result = self.emit((unit,) if unit else (), min(max_units, ROSTER_UNITS), records,
                                   omitted=len(ordered) > len(mapping))
                if result["items"]:
                    self.selection_refs = mapping
                return result
            if mode != "evidence" or self.task_calls != 2 or not self.selection_refs or not anchors:
                raise ToolError("research_evidence_sequence")
            if len(anchors) != len(set(anchors)) or len(anchors) > 3:
                raise ToolError("research_invalid_anchors")
            if any(anchor not in self.selection_refs for anchor in anchors):
                return self.emit((), min(max_units, EVIDENCE_UNITS), records)
            current = {record.id: record for record in eligible}
            full_groups = [sorted((current[ref] for ref in self.selection_refs[anchor] if ref in current),
                                  key=evidence_order) for anchor in anchors]
            buckets = [group[:3] for group in full_groups]
            ordered_evidence: list[Any] = []
            for index in range(3):
                ordered_evidence.extend(bucket[index] for bucket in buckets if index < len(bucket))
            admitted = ordered_evidence[:min(limit, 9)]
            return self.emit(tuple(record_unit(record) for record in admitted),
                             min(max_units, EVIDENCE_UNITS), records,
                             omitted=any(len(group) > 3 for group in full_groups)
                             or len(admitted) < len(ordered_evidence))


def create_server(service: Any, access: Callable[[], HostContextAccess],
                  authorization: Callable[[], AbstractContextManager[Any]], *,
                  expected_seq: int) -> SelectionServer:
    server = SelectionServer(service, access, authorization, expected_seq)

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
        return safe(server.status)

    @server.tool(name="aptuni_activation_disable", annotations=CONTROL)
    def disable() -> dict[str, object]:
        return server.activation.disable()

    @server.tool(name="aptuni_activate_context", annotations=CONTROL)
    def activate(intent: Literal["aptuni.profile", "aptuni.memory", "aptuni.full"], query: Query,
                 modules: Modules, scope: Literal["task", "session"] = "task", max_units: Budget = 1500,
                 limit: Limit = 20, concepts: Concepts = None) -> dict[str, object]:
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
               mode: Literal["roster", "evidence"] = "roster", anchors: RosterIds = None) -> dict[str, object]:
        """Research only: first roster up to 12 exposed Knowledge source groups (1400 units),
        then Evidence for up to three returned anchors (2600 units). Two counted calls share
        4000 units. Labels are clues, not proof of personal contribution or proficiency.
        Exact grant, module, exposure and credential checks run on every call.
        """
        return safe(lambda: server.retrieve_selection(modules, max_units, limit, mode, anchors))
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

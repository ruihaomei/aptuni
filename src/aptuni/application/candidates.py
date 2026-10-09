"""Candidate inventory for choosing among the user's own items (ADR-0032).

The inventory tells an Agent which candidate entities exist (repositories, documents, study
subjects) so it can choose before fetching Evidence, instead of guessing words the records happen
to contain. It is derived per call from the provenance of exposable Evidence: no storage, no
model, no query terms. Labels are clues, never proof of the user's work.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from aptuni.application.context import (
    METADATA_UNITS,
    ContextResponse,
    ContextUnit,
    pack_units,
    record_unit,
    response_from,
    unit_cost,
)
from aptuni.application.credential_guard import record_text
from aptuni.application.errors import AptuniError
from aptuni.policy.secrets import contains_credential

__all__ = [
    "CATEGORIES", "Candidate", "Category", "Inventory", "build_inventory", "candidate_evidence_context",
    "candidate_id", "inventory_context", "select_evidence",
]

Category = Literal["repositories", "documents", "subjects"]
CATEGORIES: tuple[Category, ...] = ("repositories", "documents", "subjects")
_PREFIX = {"repositories": "r", "documents": "d", "subjects": "s"}
REPOSITORY_SCHEMAS = frozenset({"github.locator", "github.concept", "github.activity"})
PATH_DOCUMENT_SCHEMAS = frozenset({"folder.locator", "obsidian.locator"})
SUBJECT_MIN_DESCENDANTS = 20
SUBJECT_LIMIT = 100
DESCRIPTOR_BYTES = 90
OWNER_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
PATH_SEPARATOR = "›"
CANDIDATE_ID = re.compile(r"c[rds]-[0-9a-f]{12}")
MAX_CANDIDATES = 6
PER_CANDIDATE = 3


@dataclass(frozen=True)
class Candidate:
    id: str
    category: Category
    row: dict[str, object]
    records: tuple[Any, ...]  # best-first Evidence for this entity


Inventory = dict[Category, list[Candidate]]


def candidate_id(source_id: str, category: Category, key: str) -> str:
    """Stable, opaque ID: category letter plus a short digest of (source, category, grouping key)."""
    digest = hashlib.sha256(json.dumps([source_id, category, key], ensure_ascii=False).encode()).hexdigest()
    return f"c{_PREFIX[category]}-{digest[:12]}"


def _locator(record: Any) -> tuple[str | None, dict[str, Any]]:
    locator = getattr(record.provenance, "locator", None)
    extension = getattr(locator, "extension", None)
    if extension is None:
        return None, {}
    return str(extension.schema_name), dict(extension.fields)


def _plain(text: str) -> str:
    """Words only: drop HTML tags (also one cut by the excerpt limit), images, link targets, headings."""
    text = re.sub(r"<[^>]*(>|$)", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return " ".join(text.replace("#", " ").split())


def _clip(text: str, limit: int) -> str:
    raw = text.encode("utf-8")
    return text if len(raw) <= limit else raw[:limit - 3].decode("utf-8", errors="ignore") + "…"


def _descendants(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return len(value) if isinstance(value, list | tuple) else 0


def _repository_rank(record: Any) -> tuple[int, int, str]:
    """Shallowest README first, then shallow paths, then stable IDs."""
    _, fields = _locator(record)
    raw = fields.get("path")
    path = raw if isinstance(raw, str) else ""
    readme = path.rsplit("/", 1)[-1].casefold().startswith("readme")
    return (0 if readme else 1, path.count("/") if path else 9, str(record.id))


def _subject_rank(record: Any) -> tuple[int, int, str]:
    """Root card first, then broader descendants, then stable IDs."""
    _, fields = _locator(record)
    depth = fields.get("depth")
    return (depth if isinstance(depth, int) else 99, -_descendants(fields.get("subtree_concepts")), str(record.id))


def _label_safe(row: dict[str, object]) -> bool:
    return not contains_credential(json.dumps(row, ensure_ascii=False))


@dataclass
class _Groups:
    repos: dict[tuple[str, str], dict[str, Any]]
    documents: dict[tuple[str, str], dict[str, Any]]
    roots: dict[str, dict[str, Any]]  # one study subject per root title, across notebooks and sources


def _collect(evidence: Iterable[Any]) -> _Groups:
    """One pass over credential-free Evidence, grouping by provenance only."""
    groups = _Groups({}, {}, {})
    for record in evidence:
        if getattr(record, "record_type", None) != "evidence" or contains_credential(record_text(record)):
            continue
        source = str(record.provenance.source_id or "")
        schema, fields = _locator(record)
        if schema in REPOSITORY_SCHEMAS and type(fields.get("repository_id")) is int:
            group = groups.repos.setdefault((source, str(fields["repository_id"])), {"label": None, "records": []})
            owner_name = fields.get("owner_name")
            if group["label"] is None and isinstance(owner_name, str) and OWNER_NAME.fullmatch(owner_name):
                group["label"] = owner_name.rsplit("/", 1)[-1]
            group["records"].append(record)
        elif schema in PATH_DOCUMENT_SCHEMAS and isinstance(fields.get("relative_path"), str):
            path = fields["relative_path"]
            label = path.rsplit(".", 1)[0] if "." in path.rsplit("/", 1)[-1] else path
            groups.documents.setdefault((source, path), {"label": label, "records": []})["records"].append(record)
        elif schema == "notion.locator" and isinstance(fields.get("entity_id"), str) \
                and isinstance(fields.get("title"), str) and fields["title"].strip():
            document = groups.documents.setdefault(
                (source, fields["entity_id"]), {"label": " ".join(fields["title"].split()), "records": []})
            document["records"].append(record)
        elif schema == "marginnote.locator" and fields.get("notebook_id") is not None:
            title = str(record.subject).split(PATH_SEPARATOR)[0].strip()
            if title:
                root = groups.roots.setdefault(title.casefold(), {"label": title, "size": 0, "records": []})
                root["records"].append(record)
                if fields.get("depth") == 0:
                    root["size"] = max(root["size"], _descendants(fields.get("subtree_concepts")))
    return groups


def _repository_candidates(repos: dict[tuple[str, str], dict[str, Any]]) -> list[Candidate]:
    candidates = []
    for (source, key), group in sorted(repos.items(), key=lambda item: (str(item[1]["label"]).casefold(), item[0])):
        if group["label"] is None:
            continue
        records = tuple(sorted(group["records"], key=_repository_rank))
        row: dict[str, object] = {"id": candidate_id(source, "repositories", key), "label": group["label"],
                                  "evidence": len(records)}
        about = _plain(str(getattr(records[0], "excerpt", "") or "")) if _repository_rank(records[0])[0] == 0 else ""
        if about:
            row["about"] = _clip(about, DESCRIPTOR_BYTES)
        candidates.append(Candidate(str(row["id"]), "repositories", row, records))
    return candidates


def _document_candidates(documents: dict[tuple[str, str], dict[str, Any]]) -> list[Candidate]:
    candidates = []
    for (source, key), group in sorted(documents.items(), key=lambda item: (item[1]["label"].casefold(), item[0])):
        row: dict[str, object] = {"id": candidate_id(source, "documents", key), "label": group["label"]}
        records = tuple(sorted(group["records"], key=lambda record: str(record.id)))
        candidates.append(Candidate(str(row["id"]), "documents", row, records))
    return candidates


def _subject_candidates(roots: dict[str, dict[str, Any]]) -> list[Candidate]:
    """Large root topics; the same title in several notebooks is one subject with all its Evidence."""
    candidates: list[Candidate] = []
    ranked = sorted((item for item in roots.items() if item[1]["size"] >= SUBJECT_MIN_DESCENDANTS),
                    key=lambda item: (-item[1]["size"], item[1]["label"].casefold(), item[0]))
    for title, root in ranked[:SUBJECT_LIMIT]:
        row: dict[str, object] = {"id": candidate_id("", "subjects", title), "label": root["label"],
                                  "notes": root["size"]}
        candidates.append(Candidate(str(row["id"]), "subjects", row, tuple(sorted(root["records"], key=_subject_rank))))
    return candidates


def build_inventory(evidence: Iterable[Any]) -> Inventory:
    """Group exposable, credential-free Evidence into candidate entities per category."""
    groups = _collect(evidence)
    inventory: Inventory = {
        "repositories": _repository_candidates(groups.repos),
        "documents": _document_candidates(groups.documents),
        "subjects": _subject_candidates(groups.roots),
    }
    # Labels and descriptors are disclosed context: drop any row that looks like a credential.
    return {category: [candidate for candidate in candidates if _label_safe(candidate.row)]
            for category, candidates in inventory.items()}


def select_evidence(inventory: Inventory, ids: Sequence[str], *, per_candidate: int = 3) -> tuple[list[Any], bool]:
    """Best Evidence for the chosen IDs, round-robin across candidates; unknown IDs contribute nothing.

    Returns the records and whether any chosen candidate had more Evidence than ``per_candidate``.
    """
    by_id = {candidate.id: candidate for candidates in inventory.values() for candidate in candidates}
    groups = [by_id[identifier].records for identifier in dict.fromkeys(ids) if identifier in by_id]
    chosen: list[Any] = []
    for index in range(per_candidate):
        chosen.extend(group[index] for group in groups if index < len(group))
    return chosen, any(len(group) > per_candidate for group in groups)


def _authorized_evidence(service: Any, modules: tuple[str, ...], budget: int, limit: int, access: Any
                         ) -> tuple[tuple[str, ...], Any]:
    """Validate the request exactly like host Context and return the selected modules."""
    service._check_context_request(budget, "host_mcp", limit)
    for module_name in modules:
        service._check_module(module_name)
    selected = tuple(dict.fromkeys(modules))
    service._authorize_host(access, scope="context.read", modules=selected)
    service._authorize_host(access, scope="evidence.read", modules=selected)
    return selected, access


def _snapshot_inventory(service: Any, selected: tuple[str, ...]) -> tuple[int, Any, Inventory]:
    seq, records = service.snapshot()
    evidence = (record for record in records.exposable()
                if record.record_type == "evidence" and record.module in selected)
    return seq, records, build_inventory(evidence)


def _inventory_unit(category: Category, rows: list[dict[str, object]]) -> ContextUnit:
    text = json.dumps({"category": category, "candidates": rows}, ensure_ascii=False, separators=(",", ":"))
    return ContextUnit("L4", "candidate_inventory", None, None, text, None, "untrusted_source", True, ())


def inventory_context(service: Any, categories: Sequence[str], *, modules: tuple[str, ...], budget: int,
                      access: Any) -> ContextResponse:
    """List authorized candidate entities per category (ADR-0032 item 3); omission sets ``truncated``."""
    if not categories or len(set(categories)) != len(categories) or any(c not in CATEGORIES for c in categories):
        raise AptuniError("invalid_context", "Pass 1-3 distinct categories: repositories, documents, subjects.")
    selected, access = _authorized_evidence(service, modules, budget, 20, access)
    for _ in range(3):
        seq, records, inventory = _snapshot_inventory(service, selected)
        units: list[ContextUnit] = []
        used, truncated = METADATA_UNITS, False
        for category in categories:
            kept: list[dict[str, object]] = []
            for candidate in inventory[cast_category(category)]:
                trial = _inventory_unit(cast_category(category), [*kept, candidate.row])
                if contains_credential(trial.text):
                    # Rows can look like a credential only together (e.g. a Markdown-table rule across
                    # rows); skip the row so the last-line guard never drops the whole category.
                    truncated = True
                    continue
                if used + unit_cost(trial) > budget:
                    truncated = True
                    break
                kept.append(candidate.row)
            if kept:
                unit = _inventory_unit(cast_category(category), kept)
                units.append(unit)
                used += unit_cost(unit)
        packed = pack_units(tuple(units), budget)
        response = response_from(packed, budget=budget, vault_seq=seq, policy_epoch=service.policy_of(records).epoch,
                                 more_results=truncated, audience="host_mcp")
        if service.snapshot()[0] == seq:
            return response
    raise AptuniError("concurrent_write", "The Vault kept changing during the inventory; run it again.")


def candidate_evidence_context(service: Any, ids: Sequence[str], *, modules: tuple[str, ...], budget: int,
                               limit: int, access: Any) -> ContextResponse:
    """Evidence for chosen candidate IDs (ADR-0032 item 4); stale or unknown IDs contribute nothing."""
    if not ids or len(ids) > MAX_CANDIDATES or len(set(ids)) != len(ids) \
            or any(not isinstance(i, str) or not CANDIDATE_ID.fullmatch(i) for i in ids):
        raise AptuniError("invalid_context", f"Pass 1-{MAX_CANDIDATES} distinct candidate IDs from an inventory.")
    selected, access = _authorized_evidence(service, modules, budget, limit, access)
    for _ in range(3):
        seq, records, inventory = _snapshot_inventory(service, selected)
        chosen, omitted = select_evidence(inventory, ids, per_candidate=PER_CANDIDATE)
        packed = pack_units(tuple(record_unit(record) for record in chosen[:limit]), budget)
        response = response_from(packed, budget=budget, vault_seq=seq, policy_epoch=service.policy_of(records).epoch,
                                 more_results=omitted or len(chosen) > limit, audience="host_mcp")
        if service.snapshot()[0] == seq:
            return response
    raise AptuniError("concurrent_write", "The Vault kept changing during Evidence lookup; run it again.")


_CATEGORY_BY_NAME: dict[str, Category] = {category: category for category in CATEGORIES}


def cast_category(value: str) -> Category:
    if value not in _CATEGORY_BY_NAME:
        raise AptuniError("invalid_context", "Unknown candidate category.")
    return _CATEGORY_BY_NAME[value]

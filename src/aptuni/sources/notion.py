"""Exact-scope Notion source records delivered by the official hosted MCP server (ADR-0021)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from aptuni.sources.obsidian_parse import sanitize_token
from aptuni.sources.reconcile import snapshot_id_for
from aptuni.sources.records import (
    CandidateDelta,
    Extension,
    Operation,
    Snapshot,
    SnapshotItem,
    SourceLocator,
    canonical_json,
)

NOTION_MCP_ENDPOINT = "https://mcp.notion.com/mcp"
MAX_ROOTS = 100
MAX_ENTITY_CHARS = 1_000_000
MAX_REFERENCES = 256
_NOTION_HOSTS = frozenset({"notion.so", "www.notion.so", "app.notion.com"})
_UUIDISH = re.compile(r"(?i)([0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})")
_STRUCTURAL_URL = re.compile(
    r'<(?P<tag>page|database|folder|synced_block(?:_reference)?)\b[^>]*\burl="(?P<url>[^"]+)"',
    re.IGNORECASE,
)


def _has_safe_share_hint(query: str) -> bool:
    if not query:
        return True
    try:
        values = parse_qsl(query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return False
    return (
        len(values) == 1
        and values[0][0] == "pvs"
        and re.fullmatch(r"[0-9]{1,3}", values[0][1]) is not None
    )


class NotionScopeError(ValueError):
    """The configured scope or one official MCP result is unsafe or outside that scope."""


def _raw_entity_id(value: str) -> str:
    match = _UUIDISH.fullmatch(value)
    if match is None:
        raise NotionScopeError("notion_entity_id_invalid")
    try:
        return str(UUID(match.group(1)))
    except ValueError as error:  # UUID also enforces length and hexadecimal syntax
        raise NotionScopeError("notion_entity_id_invalid") from error


def _scope_value(value: str) -> tuple[str, str]:
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise NotionScopeError("notion_scope_invalid")
    if "://" not in value:
        entity_id = _raw_entity_id(value)
        return entity_id, f"https://www.notion.so/{entity_id.replace('-', '')}"
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _NOTION_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or not _has_safe_share_hint(parsed.query)
        or parsed.fragment
    ):
        raise NotionScopeError("notion_scope_origin_invalid")
    terminal = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    matches = tuple(_UUIDISH.finditer(terminal))
    if len(matches) != 1 or matches[0].end() != len(terminal):
        raise NotionScopeError("notion_scope_invalid")
    entity_id = _raw_entity_id(matches[0].group(1))
    return entity_id, f"https://www.notion.so/{entity_id.replace('-', '')}"


@dataclass(frozen=True)
class NotionSourceSpec:
    entity_ids: tuple[str, ...]
    entity_urls: tuple[str, ...]

    @classmethod
    def build(cls, roots: tuple[str, ...]) -> NotionSourceSpec:
        if not roots or len(roots) > MAX_ROOTS:
            raise NotionScopeError("notion_scope_count_invalid")
        normalized = tuple(_scope_value(root) for root in roots)
        ids = tuple(item[0] for item in normalized)
        if len(ids) != len(set(ids)):
            raise NotionScopeError("notion_scope_duplicate")
        return cls(ids, tuple(item[1] for item in normalized))

    def roots(self) -> tuple[str, ...]:
        return self.entity_urls

    @classmethod
    def from_roots(cls, roots: tuple[str, ...]) -> NotionSourceSpec:
        return cls.build(roots)


@dataclass(frozen=True)
class NotionEntity:
    entity_id: str
    entity_type: str
    canonical_url: str
    title: str
    text: str
    last_edited_at: str | None
    parent_id: str | None
    truncated: bool
    unknown_block_ids: tuple[str, ...]
    #: True only when the official result carried explicit, valid completeness metadata.
    #: Absent metadata is never evidence of completeness (ADR-0021 2026-09-25 amendment).
    completeness_verified: bool = False


@dataclass(frozen=True)
class NotionScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]
    notes: tuple[str, ...]
    principal_id: str

    @property
    def sequence(self) -> int:
        return self.delta.sequence


def _references(text: str) -> tuple[list[str], list[str]]:
    children: set[str] = set()
    blocks: set[str] = set()
    for match in _STRUCTURAL_URL.finditer(text):
        try:
            entity_id = _scope_value(match.group("url"))[0]
        except NotionScopeError:
            continue
        if match.group("tag").lower() in {"page", "database", "folder"}:
            children.add(entity_id)
        else:
            blocks.add(entity_id)
        if len(children) + len(blocks) >= MAX_REFERENCES:
            break
    return sorted(children), sorted(blocks)


def _timestamp(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > 64 or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise NotionScopeError("notion_result_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise NotionScopeError("notion_result_timestamp_invalid") from error
    if parsed.tzinfo is None:
        raise NotionScopeError("notion_result_timestamp_invalid")
    return parsed.isoformat()


def _observed(source_id: str, entity: NotionEntity, principal_id: str) -> SnapshotItem:
    entity_id, canonical_url = _scope_value(entity.canonical_url)
    if entity_id != _raw_entity_id(entity.entity_id):
        raise NotionScopeError("notion_result_identity_mismatch")
    if entity.entity_type not in {"page", "database", "data_source", "view"}:
        raise NotionScopeError("notion_result_type_invalid")
    if len(entity.text) > MAX_ENTITY_CHARS:
        raise NotionScopeError("notion_result_oversized")
    child_ids, block_ids = _references(entity.text)
    fields: dict[str, object] = {
        "principal_id": _raw_entity_id(principal_id),
        "entity_id": entity_id,
        "entity_type": entity.entity_type,
        "canonical_url": canonical_url,
        "title": sanitize_token(entity.title),
        "last_edited_at": _timestamp(entity.last_edited_at),
        "parent_id": _raw_entity_id(entity.parent_id) if entity.parent_id is not None else None,
        "child_entity_ids": child_ids,
        "block_ids": block_ids,
        "truncated": entity.truncated,
    }
    fingerprint = canonical_json({"fields": fields, "text": entity.text})
    content_hash = "sha256:" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    subject = "notion-" + hashlib.sha256(f"{source_id}:{entity_id}".encode()).hexdigest()[:20]
    locator = SourceLocator(source_id, "notion", subject, Extension("notion.locator", 1, fields))
    return SnapshotItem(locator, content_hash)


def scan_notion(
    spec: NotionSourceSpec,
    source_id: str,
    fetched: list[NotionEntity],
    previous: NotionScan | None,
    parser: tuple[str, str],
    *,
    principal_id: str,
) -> NotionScan:
    """Reconcile exact approved roots; incomplete official responses can never prove deletion."""
    if not principal_id or len(fetched) > len(spec.entity_ids):
        raise NotionScopeError("notion_result_scope_invalid")
    items = [_observed(source_id, entity, principal_id) for entity in fetched]
    by_id = {str(item.locator.extension.fields["entity_id"]): item for item in items}
    if len(by_id) != len(items) or not set(by_id) <= set(spec.entity_ids):
        raise NotionScopeError("notion_result_scope_invalid")
    unsafe = any(
        entity.truncated or entity.unknown_block_ids or not entity.completeness_verified for entity in fetched
    )
    coverage = "complete" if len(by_id) == len(spec.entity_ids) and not unsafe else "partial"
    notes: set[str] = set()
    if coverage == "partial":
        notes.add("coverage_partial")
    if any(entity.truncated for entity in fetched):
        notes.add("notion_truncated")
    if any(entity.unknown_block_ids for entity in fetched):
        notes.add("notion_unknown_blocks")
    if any(not entity.completeness_verified for entity in fetched):
        notes.add("notion_completeness_unverified")

    old_items = previous.snapshot.items if previous else ()
    old_by_id = {str(item.locator.extension.fields["entity_id"]): item for item in old_items}
    operations: list[Operation] = []
    final: list[SnapshotItem] = []
    parser_changed = previous is not None and previous.parser != parser
    for entity_id in sorted(by_id):
        item = by_id[entity_id]
        old = old_by_id.get(entity_id)
        final.append(item)
        if old is None:
            operations.append(Operation.add(item.locator, item.content_hash))
        elif old.content_hash != item.content_hash:
            operations.append(Operation.modify(old.locator, item.locator, item.content_hash,
                                               reasons=("content_changed",)))
        elif parser_changed:
            operations.append(Operation.modify(old.locator, item.locator, item.content_hash,
                                               reasons=("parser_upgrade",)))
    for entity_id in sorted(set(old_by_id) - set(by_id)):
        old = old_by_id[entity_id]
        # An absent exact-root MCP result is not proof that the remote object was deleted.
        # Retain prior evidence until the source is explicitly unlinked or purged.
        final.append(old)
    ordered = tuple(sorted(final, key=lambda item: item.locator.subject_id))
    snapshot = Snapshot(snapshot_id_for(source_id, coverage, ordered), source_id, coverage, ordered)
    sequence = previous.sequence + 1 if previous else 1
    delta = CandidateDelta.build(
        source_id,
        previous.snapshot.snapshot_id if previous else None,
        snapshot.snapshot_id,
        parser,
        tuple(operations),
        sequence=sequence,
    )
    return NotionScan(snapshot, delta, parser, tuple(sorted(notes)), principal_id)

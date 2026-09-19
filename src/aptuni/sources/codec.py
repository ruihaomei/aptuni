"""Canonical JSON codec for the common envelope (lossless, including unknown extensions)."""

from __future__ import annotations

import json
from typing import Any

from aptuni.sources.records import (
    CandidateDelta,
    ContractError,
    Extension,
    Operation,
    Snapshot,
    SnapshotItem,
    SourceLocator,
    canonical_json,
)

ENVELOPE_VERSION = 2  # 2: per-source delivery ``sequence`` (S05A review round 2)


def locator_to_dict(locator: SourceLocator | None) -> dict[str, Any] | None:
    if locator is None:
        return None
    return {
        "source_id": locator.source_id,
        "provider": locator.provider,
        "subject_id": locator.subject_id,
        "extension": {
            "schema": locator.extension.schema,
            "version": locator.extension.version,
            "fields": dict(locator.extension.fields),
        },
    }


def locator_from_dict(data: dict[str, Any] | None) -> SourceLocator | None:
    if data is None:
        return None
    ext = data["extension"]
    return SourceLocator(
        data["source_id"],
        data["provider"],
        data["subject_id"],
        Extension(ext["schema"], ext["version"], ext["fields"]),
    )


def operation_to_dict(op: Operation) -> dict[str, Any]:
    return {
        "kind": op.kind,
        "subject_id": op.subject_id,
        "before": locator_to_dict(op.before),
        "after": locator_to_dict(op.after),
        "content_hash": op.content_hash,
        "confidence": op.confidence,
        "reasons": list(op.reasons),
        "review_state": op.review_state,
        "candidates": list(op.candidates),
        "effect": op.effect,
    }


def operation_from_dict(data: dict[str, Any]) -> Operation:
    op = Operation(
        kind=data["kind"],
        subject_id=data["subject_id"],
        before=locator_from_dict(data["before"]),
        after=locator_from_dict(data["after"]),
        content_hash=data["content_hash"],
        confidence=data["confidence"],
        reasons=tuple(data["reasons"]),
        review_state=data["review_state"],
        candidates=tuple(data["candidates"]),
    )
    if data.get("effect") != op.effect:
        raise ContractError("effect_mismatch")
    return op


def delta_to_json(delta: CandidateDelta) -> str:
    return canonical_json(
        {
            "envelope_version": ENVELOPE_VERSION,
            "delta_id": delta.delta_id,
            "source_id": delta.source_id,
            "base_snapshot": delta.base_snapshot,
            "new_snapshot": delta.new_snapshot,
            "parser": list(delta.parser),
            "operations": [operation_to_dict(op) for op in delta.operations],
            "sequence": delta.sequence,
        }
    )


def delta_from_json(text: str) -> CandidateDelta:
    data = json.loads(text)
    if data.get("envelope_version") != ENVELOPE_VERSION:
        raise ContractError("envelope_version_unsupported")
    try:
        return _delta_from_dict(data)
    except (KeyError, TypeError) as error:
        raise ContractError("envelope_field_missing") from error


def _delta_from_dict(data: dict[str, Any]) -> CandidateDelta:
    return CandidateDelta(
        source_id=data["source_id"],
        base_snapshot=data["base_snapshot"],
        new_snapshot=data["new_snapshot"],
        parser=tuple(data["parser"]),
        operations=tuple(operation_from_dict(item) for item in data["operations"]),
        sequence=data["sequence"],
        delta_id=data["delta_id"],
    )


def snapshot_to_dict(snapshot: Snapshot) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "source_id": snapshot.source_id,
        "coverage": snapshot.coverage,
        "items": [
            {"locator": locator_to_dict(item.locator), "content_hash": item.content_hash, "held": item.held}
            for item in snapshot.items
        ],
    }


def snapshot_from_dict(data: dict[str, Any]) -> Snapshot:
    items = []
    for raw in data["items"]:
        locator = locator_from_dict(raw["locator"])
        if locator is None:
            raise ContractError("snapshot_item_locator_missing")
        items.append(SnapshotItem(locator, raw["content_hash"], bool(raw["held"])))
    return Snapshot(data["snapshot_id"], data["source_id"], data["coverage"], tuple(items))

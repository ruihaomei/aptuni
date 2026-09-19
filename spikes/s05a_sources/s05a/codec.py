"""Canonical JSON codec for the common envelope (lossless, including unknown extensions)."""

from __future__ import annotations

import json
from typing import Any

from s05a.records import (
    CandidateDelta,
    ContractError,
    Extension,
    Operation,
    SourceLocator,
    canonical_json,
)

ENVELOPE_VERSION = 1


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
        }
    )


def delta_from_json(text: str) -> CandidateDelta:
    data = json.loads(text)
    if data.get("envelope_version") != ENVELOPE_VERSION:
        raise ContractError("envelope_version_unsupported")
    return CandidateDelta(
        source_id=data["source_id"],
        base_snapshot=data["base_snapshot"],
        new_snapshot=data["new_snapshot"],
        parser=tuple(data["parser"]),
        operations=tuple(operation_from_dict(item) for item in data["operations"]),
        delta_id=data["delta_id"],
    )

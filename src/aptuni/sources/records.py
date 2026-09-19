"""Common source-identity records shared by every SourceProvider.

Canonical identity (``subject_id``), current source location (the extension
fields) and content fingerprint (``content_hash``) are deliberately separate.
Providers only report source changes; nothing here mutates Profile facts.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

OPERATION_KINDS = frozenset({"add", "modify", "move", "remove", "ambiguous"})
REVIEW_STATES = frozenset({"none", "needs_review"})
COVERAGE_STATES = frozenset({"complete", "partial"})


class ContractError(ValueError):
    """A record violates a common-envelope invariant."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True)
class Extension:
    """Provider-specific, versioned identity fields; opaque to common invariants."""

    schema: str
    version: int
    fields: Mapping[str, Any]

    def __post_init__(self) -> None:
        if "." not in self.schema or type(self.version) is not int or self.version < 1:
            raise ContractError("extension_schema_invalid")
        # Deep, JSON-normalized copy isolates the caller's object. The copy itself is a plain dict,
        # so intake must recompute ``delta_id`` (see ``Ledger.apply``) rather than trust it.
        object.__setattr__(self, "fields", json.loads(canonical_json(dict(self.fields))))

    @property
    def provider(self) -> str:
        return self.schema.split(".", 1)[0]


@dataclass(frozen=True)
class SourceLocator:
    source_id: str
    provider: str
    subject_id: str
    extension: Extension

    def __post_init__(self) -> None:
        if not (self.source_id and self.provider and self.subject_id):
            raise ContractError("locator_field_missing")
        if self.extension.provider != self.provider:
            raise ContractError("extension_provider_mismatch")


@dataclass(frozen=True)
class Operation:
    kind: str
    subject_id: str | None
    before: SourceLocator | None
    after: SourceLocator | None
    content_hash: str | None = None
    confidence: float = 1.0
    reasons: tuple[str, ...] = ()
    review_state: str = "none"
    candidates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if self.kind not in OPERATION_KINDS or self.review_state not in REVIEW_STATES:
            raise ContractError("operation_kind_or_review_invalid")
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractError("confidence_out_of_range")
        _check_shape(self)

    @property
    def effect(self) -> str:
        """Source loss is evidence withdrawal, never fact deletion."""
        return "tombstone_proposal" if self.kind == "remove" else "source_change"

    @classmethod
    def add(cls, after: SourceLocator, content_hash: str, **kw: Any) -> Operation:
        return cls("add", after.subject_id, None, after, content_hash, **kw)

    @classmethod
    def modify(cls, before: SourceLocator, after: SourceLocator, content_hash: str, **kw: Any) -> Operation:
        return cls("modify", after.subject_id, before, after, content_hash, **kw)

    @classmethod
    def move(
        cls, subject_id: str, before: SourceLocator, after: SourceLocator, content_hash: str, **kw: Any
    ) -> Operation:
        return cls("move", subject_id, before, after, content_hash, **kw)

    @classmethod
    def remove(cls, subject_id: str, before: SourceLocator, content_hash: str, **kw: Any) -> Operation:
        return cls("remove", subject_id, before, None, content_hash, **kw)

    @classmethod
    def ambiguous(
        cls, after: SourceLocator, candidates: tuple[str, ...], reasons: tuple[str, ...], **kw: Any
    ) -> Operation:
        return cls(
            "ambiguous", None, None, after, kw.pop("content_hash", None),
            reasons=reasons, review_state="needs_review", candidates=candidates, **kw,
        )

    def needing_review(self, reason: str) -> Operation:
        reasons = self.reasons if reason in self.reasons else (*self.reasons, reason)
        return replace(self, review_state="needs_review", reasons=reasons)


def _check_shape(op: Operation) -> None:
    has_before, has_after = op.before is not None, op.after is not None
    expected = {
        "add": (False, True),
        "modify": (True, True),
        "move": (True, True),
        "remove": (True, False),
        "ambiguous": (False, True),
    }[op.kind]
    if (has_before, has_after) != expected:
        raise ContractError(f"{op.kind}_shape_invalid")
    if op.candidates and op.kind != "ambiguous":
        raise ContractError("candidates_only_on_ambiguous")
    if op.kind == "ambiguous":
        if op.subject_id is not None or len(set(op.candidates)) < 2 or op.review_state != "needs_review":
            raise ContractError("ambiguous_requires_review_and_candidates")
        return
    if not op.subject_id:
        raise ContractError("subject_required")
    for locator in (op.before, op.after):
        if locator is not None and locator.subject_id != op.subject_id:
            raise ContractError("locator_subject_mismatch")


@dataclass(frozen=True)
class SnapshotItem:
    """``held`` marks a carried-forward item reserved by an unresolved review item."""

    locator: SourceLocator
    content_hash: str
    held: bool = False


@dataclass(frozen=True)
class Snapshot:
    """Immutable observation of one source; ``partial`` coverage cannot prove disappearance."""

    snapshot_id: str
    source_id: str
    coverage: str
    items: tuple[SnapshotItem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        if self.coverage not in COVERAGE_STATES:
            raise ContractError("coverage_invalid")
        subjects = [item.locator.subject_id for item in self.items]
        if len(subjects) != len(set(subjects)):
            raise ContractError("duplicate_subject_in_snapshot")
        if any(item.locator.source_id != self.source_id for item in self.items):
            raise ContractError("snapshot_source_mismatch")

    def supports_removal(self) -> bool:
        return self.coverage == "complete"

    def by_subject(self) -> dict[str, SnapshotItem]:
        return {item.locator.subject_id: item for item in self.items}


@dataclass(frozen=True)
class CandidateDelta:
    source_id: str
    base_snapshot: str | None
    new_snapshot: str
    parser: tuple[str, str]
    operations: tuple[Operation, ...]
    sequence: int = 1  # per-source delivery counter: content ids repeat on A->B->A->B
    delta_id: str = field(default="")

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 1:
            raise ContractError("sequence_invalid")
        object.__setattr__(self, "parser", tuple(self.parser))
        object.__setattr__(self, "operations", tuple(self.operations))
        touched: list[str] = []
        for op in self.operations:
            if op.subject_id is not None:
                touched.append(op.subject_id)
            elif op.after is not None:
                touched.append(op.after.subject_id)
        if len(touched) != len(set(touched)):
            raise ContractError("multiple_operations_for_subject")
        for op in self.operations:
            for locator in (op.before, op.after):
                if locator is not None and locator.source_id != self.source_id:
                    raise ContractError("operation_source_mismatch")
        if self.delta_id != compute_delta_id(self):
            raise ContractError("delta_id_mismatch")

    @classmethod
    def build(
        cls,
        source_id: str,
        base_snapshot: str | None,
        new_snapshot: str,
        parser: tuple[str, str],
        operations: tuple[Operation, ...],
        sequence: int = 1,
    ) -> CandidateDelta:
        draft = _Draft(source_id, base_snapshot, new_snapshot, (parser[0], parser[1]), tuple(operations), sequence)
        return cls(source_id, base_snapshot, new_snapshot, parser, tuple(operations), sequence,
                   compute_delta_id(draft))


@dataclass(frozen=True)
class _Draft:
    source_id: str
    base_snapshot: str | None
    new_snapshot: str
    parser: tuple[str, str]
    operations: tuple[Operation, ...]
    sequence: int


def compute_delta_id(delta: CandidateDelta | _Draft) -> str:
    from aptuni.sources.codec import operation_to_dict  # noqa: PLC0415 (codec depends on records)

    body = {
        "source_id": delta.source_id,
        "base_snapshot": delta.base_snapshot,
        "new_snapshot": delta.new_snapshot,
        "parser": list(delta.parser),
        "operations": [operation_to_dict(op) for op in delta.operations],
        "sequence": delta.sequence,
    }
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()

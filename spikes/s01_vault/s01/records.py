"""Versioned canonical record schemas for the S01 spike (ADR-0001, ADR-0006, ADR-0010, ADR-0011).

Disposable prototype: it exists to prove that the v1 records round-trip exactly and that
schema-level invariants are enforceable with frozen Pydantic v2 models.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal, Union

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

SCHEMA_VERSION = 1
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ID_PATTERN = r"^(fct|evd|obs|cnd|mem|rev|src|pol|rcp|led)_[0-9A-HJKMNP-TV-Z]{26}$"
DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"
PARTIAL_DATE_RE = re.compile(r"^\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?)?$")

Module = Literal[
    "identity", "knowledge", "experience", "skills", "projects", "goals",
    "interests", "preferences", "behavior", "relationships", "memory",
]
MODULES: tuple[str, ...] = Module.__args__  # type: ignore[attr-defined]
Signal = Literal["exposure", "studied", "applied", "demonstrated"]
SIGNALS: tuple[str, ...] = Signal.__args__  # type: ignore[attr-defined]
Trust = Literal["user_declared", "untrusted_source", "host_proposal", "system"]
ReviewStatus = Literal["declared", "auto_derived", "quarantined", "pending_review", "accepted"]
ChangeKind = Literal["assert", "world_change", "correction", "retraction"]
RecordId = Annotated[str, Field(pattern=ID_PATTERN)]


class SchemaVersionError(Exception):
    """Raised for unknown schema versions; callers must run a migration, never guess."""


def new_id(prefix: str) -> str:
    """Return a time-sortable, Crockford-base32 record id (ULID-like, 26 chars)."""
    value = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    chars = []
    for _ in range(26):
        chars.append(CROCKFORD[value & 31])
        value >>= 5
    return f"{prefix}_{''.join(reversed(chars))}"


def deterministic_id(prefix: str, seed: str) -> str:
    """Return a stable id derived from ``seed`` (used by migrations for idempotency)."""
    value = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest(), "big")
    chars = [CROCKFORD[(value >> (5 * i)) & 31] for i in range(26)]
    return f"{prefix}_{''.join(chars)}"


def partial_date_range(text: str) -> tuple[date, date]:
    """Return the half-open ``[start, end)`` date range covered by a partial ISO date."""
    if not PARTIAL_DATE_RE.match(text):
        raise ValueError(f"invalid partial date: {text!r}")
    parts = [int(p) for p in text.split("-")]
    if len(parts) == 1:
        return date(parts[0], 1, 1), date(parts[0] + 1, 1, 1)
    if len(parts) == 2:
        start = date(parts[0], parts[1], 1)
        end = date(parts[0] + (parts[1] == 12), parts[1] % 12 + 1, 1)
        return start, end
    start = date(parts[0], parts[1], parts[2])
    return start, start + timedelta(days=1)


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceLocator(Frozen):
    kind: Literal["opml_node", "docx_section", "xlsx_range", "pdf_page", "file",
                  "github_file", "github_repo", "interaction", "declared"]
    path: str | None = None
    node_path: tuple[str, ...] = ()
    heading_path: tuple[str, ...] = ()
    sheet: str | None = None
    cell_range: str | None = None
    page: int | None = Field(default=None, ge=1)
    repo: str | None = None
    commit: str | None = None


class Provenance(Frozen):
    source_id: str | None
    episode: str | None
    locator: SourceLocator | None


class RetentionLabel(Frozen):
    retention_class: Literal["canonical", "source_minimized", "full_content", "derived"]
    purpose: str = Field(min_length=1)
    expires_at: AwareDatetime | None
    full_content: bool


class Envelope(Frozen):
    """Shared canonical envelope (ADR-0011)."""

    id: RecordId
    schema_version: Literal[1]
    recorded_at: AwareDatetime
    valid_from: str | None
    valid_until: str | None
    module: Module
    provenance: Provenance
    trust: Trust
    retention: RetentionLabel
    policy_epoch: int = Field(ge=0)
    confidence: float | None = Field(ge=0.0, le=1.0)
    review_status: ReviewStatus
    supersedes: tuple[RecordId, ...]
    change_kind: ChangeKind

    @field_validator("valid_from", "valid_until")
    @classmethod
    def _partial_dates(cls, value: str | None) -> str | None:
        if value is not None:
            partial_date_range(value)
        return value

    @model_validator(mode="after")
    def _envelope_rules(self) -> Envelope:
        if self.valid_from and self.valid_until:
            if partial_date_range(self.valid_until)[0] <= partial_date_range(self.valid_from)[0]:
                raise ValueError("valid_until must start after valid_from")
        if self.id in self.supersedes:
            raise ValueError("a record cannot supersede itself")
        if self.change_kind != "assert" and not self.supersedes:
            raise ValueError(f"change_kind {self.change_kind} requires supersedes")
        return self


class Evidence(Envelope):
    record_type: Literal["evidence"]
    subject: str = Field(min_length=1)
    signals: tuple[Signal, ...]
    excerpt: str | None = Field(max_length=280)
    content_hash: str = Field(pattern=DIGEST_PATTERN)
    observed_at: AwareDatetime

    @model_validator(mode="after")
    def _needs_locator(self) -> Evidence:
        if self.provenance.locator is None:
            raise ValueError("evidence requires provenance.locator")
        return self


class Fact(Envelope):
    record_type: Literal["fact"]
    type: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: bool | int | float | str | None
    statement: str = Field(min_length=1, max_length=500)
    evidence_ids: tuple[RecordId, ...]
    memory_ids: tuple[RecordId, ...]
    observed_at: AwareDatetime
    ingested_at: AwareDatetime | None

    @model_validator(mode="after")
    def _needs_support(self) -> Fact:
        if self.trust != "user_declared" and not (self.evidence_ids or self.memory_ids):
            raise ValueError("fact requires evidence_ids or memory_ids unless user_declared")
        return self


class Observation(Envelope):
    record_type: Literal["observation"]
    review_status: Literal["quarantined"]
    idempotency_key: str = Field(min_length=1)
    about: str = Field(min_length=1)
    value: str = Field(min_length=1)
    polarity: Literal["support", "contradict"]
    statement: str = Field(min_length=1, max_length=280)


class CandidateMemory(Envelope):
    record_type: Literal["candidate_memory"]
    review_status: Literal["quarantined"]
    derived_from: tuple[RecordId, ...] = Field(min_length=1)
    contradicts: tuple[RecordId, ...]
    statement: str = Field(min_length=1, max_length=500)


class Memory(Envelope):
    record_type: Literal["memory"]
    review_status: Literal["accepted"]
    candidate_id: RecordId
    evidence_ids: tuple[RecordId, ...]
    statement: str = Field(min_length=1, max_length=500)


class ReviewEvent(Frozen):
    record_type: Literal["review_event"]
    id: RecordId
    schema_version: Literal[1]
    recorded_at: AwareDatetime
    target_id: RecordId
    decision: Literal["accept", "reject", "revoke", "promote"]
    actor: Literal["user_cli"]
    action_digest: str = Field(pattern=DIGEST_PATTERN)
    policy_epoch: int = Field(ge=0)
    rationale_code: str = Field(pattern=r"^[a-z_]+$")
    nonce_id: str = Field(min_length=1)


class AuthorityPolicy(Frozen):
    version: int = Field(ge=1)
    primary_for: tuple[Annotated[str, Field(pattern=r"^[a-z_]+\.[a-z_]+$")], ...]


class SourceConfig(Frozen):
    record_type: Literal["source_config"]
    id: RecordId
    schema_version: Literal[1]
    recorded_at: AwareDatetime
    source_type: str = Field(min_length=1)
    roots: tuple[str, ...] = Field(min_length=1)
    semantic_role: str = Field(min_length=1)
    module_mapping: tuple[Module, ...]
    authority: AuthorityPolicy


class ModuleSwitch(Frozen):
    ingest_enabled: bool
    expose_enabled: bool


class ModulePolicy(Frozen):
    record_type: Literal["module_policy"]
    id: RecordId
    schema_version: Literal[1]
    recorded_at: AwareDatetime
    epoch: int = Field(ge=0)
    modules: dict[Module, ModuleSwitch]

    @model_validator(mode="after")
    def _all_modules(self) -> ModulePolicy:
        missing = sorted(set(MODULES) - set(self.modules))
        if missing:
            raise ValueError(f"module policy missing modules: {missing}")
        return self


Record = Annotated[
    Union[Evidence, Fact, Observation, CandidateMemory, Memory, ReviewEvent, SourceConfig, ModulePolicy],
    Field(discriminator="record_type"),
]
_RECORD_ADAPTER: TypeAdapter[Any] = TypeAdapter(Record)


def parse_record(raw: dict[str, Any]) -> Any:
    """Validate one raw record; unknown schema versions raise ``SchemaVersionError``."""
    version = raw.get("schema_version")
    if version != SCHEMA_VERSION:
        raise SchemaVersionError(
            f"unsupported schema_version {version!r} (supported: {SCHEMA_VERSION}); "
            "run the documented migration instead of loading this record"
        )
    return _RECORD_ADAPTER.validate_python(raw)


def canonical_json(record: BaseModel) -> str:
    """Serialize a record deterministically: sorted keys, UTF-8, one line."""
    return json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class PendingAction(Frozen):
    """A consequential action awaiting terminal-only confirmation (ADR-0013 item 2)."""

    action_id: str = Field(pattern=r"^[a-z0-9-]+$")
    action_type: str = Field(pattern=r"^[a-z_]+$")
    scope: dict[str, str]
    policy_epoch: int = Field(ge=0)
    created_at: AwareDatetime
    expires_at: AwareDatetime
    digest: str = Field(pattern=DIGEST_PATTERN)

    @classmethod
    def create(cls, *, action_type: str, scope: dict[str, str], policy_epoch: int,
               created_at: str, ttl_seconds: int) -> PendingAction:
        canonical = json.dumps({"action_type": action_type, "scope": scope, "policy_epoch": policy_epoch},
                               ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = sha256_text(canonical)
        start = datetime.fromisoformat(created_at)
        return cls(action_id="act-" + digest[7:23], action_type=action_type, scope=scope,
                   policy_epoch=policy_epoch, created_at=start,
                   expires_at=start + timedelta(seconds=ttl_seconds), digest=digest)


class CopyResult(Frozen):
    copy_class: str = Field(min_length=1)
    result: Literal["deleted", "not_present", "external_action_needed", "failed_retryable"]


class DeletionReceipt(Frozen):
    id: RecordId
    schema_version: Literal[1]
    recorded_at: AwareDatetime
    purge_id: str = Field(min_length=1)
    terminal_state: Literal["complete_managed", "complete_managed_external_action_needed",
                            "incomplete_retryable"]
    per_copy: tuple[CopyResult, ...]


class DeletionLedgerEntry(Frozen):
    """Irreversible identifier digest only; never purged content (ADR-0010)."""

    id: RecordId
    recorded_at: AwareDatetime
    target_digest: str = Field(pattern=DIGEST_PATTERN)

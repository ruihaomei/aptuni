"""Immutable public result contracts for ``aptuni.api.v1``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _PublicModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ContextItem(_PublicModel):
    canonical_id: str | None
    canonical_ids: tuple[str, ...]
    kind: str
    layer: Literal["L0", "L1", "L2", "L3", "L4"]
    module: str | None
    text: str
    source_id: str | None
    trust: str | None
    tainted: bool
    signals: tuple[str, ...]
    review_state: str | None = None
    units: int


class ContextResult(_PublicModel):
    contract: Literal["aptuni.api@1"] = "aptuni.api@1"
    audience: Literal["plugin"] = "plugin"
    requested_units: int
    used_units: int
    remaining_units: int
    truncated: bool
    layers: tuple[Literal["L0", "L1", "L2", "L3", "L4"], ...]
    vault_seq: int
    policy_epoch: int
    items: tuple[ContextItem, ...]


class MemoryProposal(_PublicModel):
    contract: Literal["aptuni.api@1"] = "aptuni.api@1"
    candidate_id: str
    created: bool
    status: Literal["pending_owner_review"] = "pending_owner_review"


class ReviewQueue(_PublicModel):
    contract: Literal["aptuni.api@1"] = "aptuni.api@1"
    context: ContextResult
    pending: int
    due: bool
    reason: str
    threshold: int
    next_due_at: str | None

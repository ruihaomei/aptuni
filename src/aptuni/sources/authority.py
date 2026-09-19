"""SourceConfig/AuthorityPolicy and conflict resolution (user policy, never provider-coded).

A sole configured primary may supersede within its declared dimension.
Absent, multiple or changed authority yields parallel candidates for review.
Confidence is carried but never decides. ``recheck`` re-evaluates the policy
version immediately before canonical commit.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from aptuni.sources.records import canonical_json


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    provider: str
    approved_roots: tuple[str, ...]
    semantic_role: str
    modules: tuple[str, ...]
    primary_for: tuple[str, ...]
    policy_version: int

    def __post_init__(self) -> None:
        for name in ("approved_roots", "modules", "primary_for"):
            object.__setattr__(self, name, tuple(getattr(self, name)))


@dataclass(frozen=True)
class Claim:
    claim_id: str
    source_id: str
    dimension: str
    subject_key: str
    value: str
    confidence: float
    policy_version: int


@dataclass(frozen=True)
class Resolution:
    dimension: str
    subject_key: str
    winner: str | None
    parallel: tuple[str, ...]
    needs_review: bool
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "parallel", tuple(self.parallel))


def resolve(claims: list[Claim], configs: dict[str, SourceConfig]) -> Resolution:
    if not claims:
        raise ValueError("no_claims")
    dimension, subject_key = claims[0].dimension, claims[0].subject_key
    if any((c.dimension, c.subject_key) != (dimension, subject_key) for c in claims):
        raise ValueError("mixed_conflict_scope")
    ordered = sorted(claims, key=lambda c: c.claim_id)
    parallel = tuple(c.claim_id for c in ordered)
    primaries = sorted({c.source_id for c in ordered if dimension in configs[c.source_id].primary_for})
    if len({c.value for c in ordered}) == 1:
        return Resolution(dimension, subject_key, None, parallel, False, "agreement")
    if len(primaries) == 1:
        winner = next(c.claim_id for c in ordered if c.source_id == primaries[0])
        return Resolution(dimension, subject_key, winner, parallel, False, "sole_primary")
    reason = "no_primary" if not primaries else "multiple_primaries"
    return Resolution(dimension, subject_key, None, parallel, True, reason)


def recheck(result: Resolution, claims: list[Claim], current: dict[str, SourceConfig]) -> Resolution:
    stale = any(current[c.source_id].policy_version != c.policy_version for c in claims)
    if not stale:
        return result
    return Resolution(result.dimension, result.subject_key, None, result.parallel, True, "policy_changed")


def config_to_json(config: SourceConfig) -> str:
    return canonical_json(asdict(config))


def config_from_json(text: str) -> SourceConfig:
    return SourceConfig(**json.loads(text))


def resolution_to_json(result: Resolution) -> str:
    return canonical_json(asdict(result))


def resolution_from_json(text: str) -> Resolution:
    return Resolution(**json.loads(text))

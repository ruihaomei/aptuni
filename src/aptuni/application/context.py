"""Bounded progressive-disclosure response records (ADR-0005, PRD §§18–19)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

Layer = Literal["L0", "L1", "L2", "L3", "L4"]
Audience = Literal["owner_cli"]
PER_UNIT_OVERHEAD = 32
METADATA_UNITS = 32
MIN_BUDGET = METADATA_UNITS
MAX_BUDGET = 100_000
MAX_QUERY_BYTES = 1024


@dataclass(frozen=True)
class ContextUnit:
    layer: Layer
    kind: str
    canonical_id: str | None
    module: str | None
    text: str
    source_id: str | None
    trust: str | None
    tainted: bool
    signals: tuple[str, ...]
    canonical_ids: tuple[str, ...] = ()

    def payload(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "canonical_ids": list(self.canonical_ids),
            "kind": self.kind,
            "layer": self.layer,
            "module": self.module,
            "signals": list(self.signals),
            "source_id": self.source_id,
            "tainted": self.tainted,
            "text": self.text,
            "trust": self.trust,
        }

    @property
    def units(self) -> int:
        return unit_cost(self)


@dataclass(frozen=True)
class PackedUnits:
    items: tuple[ContextUnit, ...]
    used_units: int
    remaining_units: int
    truncated: bool
    layers: tuple[Layer, ...]


@dataclass(frozen=True)
class ContextResponse:
    audience: Audience
    requested_units: int
    used_units: int
    remaining_units: int
    truncated: bool
    layers: tuple[Layer, ...]
    items: tuple[ContextUnit, ...]
    vault_seq: int
    policy_epoch: int


def unit_cost(item: ContextUnit) -> int:
    payload = json.dumps(item.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return len(payload.encode("utf-8")) + PER_UNIT_OVERHEAD


def pack_units(candidates: tuple[ContextUnit, ...], budget: int) -> PackedUnits:
    if type(budget) is not int or not MIN_BUDGET <= budget <= MAX_BUDGET:
        raise ValueError(f"budget must be between {MIN_BUDGET} and {MAX_BUDGET}")
    items: list[ContextUnit] = []
    used = METADATA_UNITS
    truncated = False
    for candidate in candidates:
        cost = unit_cost(candidate)
        if used + cost <= budget:
            items.append(candidate)
            used += cost
        else:
            truncated = True
    layers = tuple(dict.fromkeys(item.layer for item in items))
    return PackedUnits(tuple(items), used, budget - used, truncated, layers)


def response_from(
    packed: PackedUnits,
    *,
    budget: int,
    vault_seq: int,
    policy_epoch: int,
    more_results: bool = False,
) -> ContextResponse:
    return ContextResponse(
        audience="owner_cli",
        requested_units=budget,
        used_units=packed.used_units,
        remaining_units=packed.remaining_units,
        truncated=packed.truncated or more_results,
        layers=packed.layers,
        items=packed.items,
        vault_seq=vault_seq,
        policy_epoch=policy_epoch,
    )


def section(layer: Layer, kind: str, text: str, *, canonical_ids: tuple[str, ...] = ()) -> ContextUnit:
    return ContextUnit(layer, kind, None, None, text, None, None, False, (), canonical_ids)


def record_unit(record: Any) -> ContextUnit:
    is_evidence = record.record_type == "evidence"
    text = getattr(record, "statement", None) or getattr(record, "excerpt", None) or record.subject
    trust = str(record.trust)
    return ContextUnit(
        layer="L4" if is_evidence else "L3",
        kind=str(record.record_type),
        canonical_id=str(record.id),
        module=str(record.module),
        text=str(text),
        source_id=record.provenance.source_id,
        trust=trust,
        tainted=trust in ("untrusted_source", "host_proposal"),
        signals=tuple(getattr(record, "signals", ())),
    )

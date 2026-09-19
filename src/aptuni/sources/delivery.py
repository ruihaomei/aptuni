"""Candidate-delta delivery ordering (ADR-0006 amendment; S05A review rounds 1-2).

``delta_id`` covers a per-source ``sequence``, so one id means one delivery even when content
cycles (A->B->A->B). A known id is a duplicate (in or out of order). A new delta is admitted only
when its base is the current head and its sequence is the next one. Integrity is recomputed and
every operation passes the extension-registry gate before anything is applied.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from aptuni.sources.extensions import ExtensionRegistry, default_registry
from aptuni.sources.records import CandidateDelta, Operation, compute_delta_id


class DeliveryError(RuntimeError):
    """A delta was rejected (fixed code, never echoes content)."""


@dataclass
class DeliveryGuard:
    heads: dict[str, str] = field(default_factory=dict)
    sequences: dict[str, int] = field(default_factory=dict)
    applied: set[str] = field(default_factory=set)
    registry: ExtensionRegistry = field(default_factory=default_registry)

    def admit(self, delta: CandidateDelta) -> str:
        """Return ``apply`` or ``duplicate``; raise ``DeliveryError`` for anything else."""
        if compute_delta_id(delta) != delta.delta_id:
            raise DeliveryError("delta_integrity_failed")
        if delta.delta_id in self.applied:
            return "duplicate"
        expected = self.sequences.get(delta.source_id, 0) + 1
        if self.heads.get(delta.source_id) != delta.base_snapshot or delta.sequence != expected:
            raise DeliveryError("stale_or_out_of_order_delta")
        return "apply"

    def gate(self, delta: CandidateDelta) -> list[Operation]:
        """Validate every operation's locators before any state changes."""
        return [self.registry.gate(op) for op in delta.operations]

    def record(self, delta: CandidateDelta) -> None:
        self.heads[delta.source_id] = delta.new_snapshot
        self.sequences[delta.source_id] = delta.sequence
        self.applied.add(delta.delta_id)

    def to_json(self) -> str:
        return json.dumps({"heads": self.heads, "sequences": self.sequences, "applied": sorted(self.applied)},
                          sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> DeliveryGuard:
        data = json.loads(text)
        return cls(heads=dict(data["heads"]), sequences={k: int(v) for k, v in data["sequences"].items()},
                   applied=set(data["applied"]))

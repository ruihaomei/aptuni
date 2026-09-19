"""In-memory stand-in for the canonical store's delta intake (S05A evidence only).

Facts are never created, rewritten or deleted by source deltas. Deltas only
move source heads, withdraw or refresh evidence, flag dependent facts for
re-evaluation and queue review items. Delivery is idempotent by ``delta_id``;
a delta whose base is not the current head is stale and rejected.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from s05a.codec import operation_to_dict
from s05a.records import CandidateDelta, Operation, canonical_json

EvidenceRef = tuple[str, str]  # (source_id, subject_id)


class LedgerError(RuntimeError):
    """Rejected delta (fixed code)."""


@dataclass
class Fact:
    fact_id: str
    statement: str
    evidence: tuple[EvidenceRef, ...]
    status: str = "active"
    withdrawn_evidence: list[EvidenceRef] = field(default_factory=list)


class Ledger:
    def __init__(self) -> None:
        self.applied: set[str] = set()
        self.heads: dict[str, str] = {}
        self.facts: dict[str, Fact] = {}
        self.tombstones: set[EvidenceRef] = set()
        self.review_queue: list[Operation] = []

    def add_fact(self, fact_id: str, statement: str, evidence: tuple[EvidenceRef, ...]) -> None:
        self.facts[fact_id] = Fact(fact_id, statement, tuple(evidence))

    def apply(self, delta: CandidateDelta) -> str:
        if delta.delta_id in self.applied:
            return "duplicate"
        if self.heads.get(delta.source_id) != delta.base_snapshot:
            raise LedgerError("stale_base_snapshot")
        for op in delta.operations:
            self._apply_operation(delta.source_id, op)
        self.heads[delta.source_id] = delta.new_snapshot
        self.applied.add(delta.delta_id)
        return "applied"

    def _dependents(self, ref: EvidenceRef) -> list[Fact]:
        return [fact for fact in self.facts.values() if ref in fact.evidence]

    def _apply_operation(self, source_id: str, op: Operation) -> None:
        if op.kind == "ambiguous" or op.review_state == "needs_review":
            self.review_queue.append(op)
            return
        ref = (source_id, str(op.subject_id))
        if op.kind == "remove":
            self.tombstones.add(ref)
            for fact in self._dependents(ref):
                if ref not in fact.withdrawn_evidence:
                    fact.withdrawn_evidence.append(ref)
                fact.status = "needs_reevaluation"
        elif op.kind == "modify":
            for fact in self._dependents(ref):
                fact.status = "needs_reevaluation"

    def state_digest(self) -> str:
        body = {
            "applied": sorted(self.applied),
            "heads": self.heads,
            "facts": {
                fid: [f.statement, [list(e) for e in f.evidence], f.status, sorted(map(list, f.withdrawn_evidence))]
                for fid, f in sorted(self.facts.items())
            },
            "tombstones": sorted(map(list, self.tombstones)),
            "review": [operation_to_dict(op) for op in self.review_queue],
        }
        return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()

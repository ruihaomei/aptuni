"""Cross-record invariants and bi-temporal views over a canonical record set.

``validate(only=...)`` checks the new records of a commit against the full set (S01 finding F1:
commits must not re-validate the whole Vault). ``validate()`` with no argument is the full
check used by ``doctor``.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from aptuni.domain.records import SIGNALS, CanonicalRecord, ModulePolicy
from aptuni.domain.temporal import partial_date_range

MASTERY_RE = re.compile(r"\b(proficient|expert|mastery|mastered|fluent in)\b|精通|熟练掌握|专家级", re.IGNORECASE)
LINK_FIELDS = ("evidence_ids", "memory_ids", "derived_from", "contradicts")
EXPOSABLE_TYPES = ("fact", "memory", "evidence")


class InvariantError(ValueError):
    """A record set violates a canonical invariant; nothing may be committed."""


def _links(record: Any) -> list[str]:
    targets = list(getattr(record, "supersedes", ()))
    for name in LINK_FIELDS:
        targets.extend(getattr(record, name, ()))
    for single in ("candidate_id", "target_id"):
        value = getattr(record, single, None)
        if value:
            targets.append(value)
    return targets


class RecordSet:
    """Immutable view over canonical records with validation and temporal queries."""

    def __init__(self, records: Iterable[CanonicalRecord]) -> None:
        self._records: list[Any] = list(records)
        self._by_id: dict[str, Any] = {record.id: record for record in self._records}

    def __len__(self) -> int:
        return len(self._records)

    def records(self) -> list[Any]:
        return list(self._records)

    def ids(self) -> set[str]:
        return set(self._by_id)

    def get(self, record_id: str) -> Any:
        return self._by_id[record_id]

    # ------------------------------------------------------------------ validation
    def validate(self, only: set[str] | None = None) -> None:
        """Raise ``InvariantError`` on the first violation (restricted to ``only`` ids if given)."""
        checked = [r for r in self._records if only is None or r.id in only]
        self._check_unique_ids()
        for record in checked:
            missing = [t for t in _links(record) if t not in self._by_id]
            if missing:
                raise InvariantError(f"{record.id} references missing records: {missing}")
        self._check_supersession(checked)
        self._check_memory_lifecycle(checked)
        self._check_evidence_support(checked)
        self._check_idempotency()

    def _check_unique_ids(self) -> None:
        duplicates = [rid for rid, count in Counter(r.id for r in self._records).items() if count > 1]
        if duplicates:
            raise InvariantError(f"duplicate record ids: {duplicates}")

    def _check_supersession(self, checked: list[Any]) -> None:
        for record in checked:
            seen: set[str] = set()
            frontier = list(getattr(record, "supersedes", ()))
            while frontier:
                current = frontier.pop()
                if current == record.id:
                    raise InvariantError(f"supersession cycle through {record.id}")
                if current not in seen:
                    seen.add(current)
                    frontier.extend(getattr(self._by_id[current], "supersedes", ()))
            for target_id in getattr(record, "supersedes", ()):
                target = self._by_id[target_id]
                if target.record_type != record.record_type:
                    raise InvariantError(f"{record.id} supersedes a different record type")
                if record.recorded_at <= target.recorded_at:
                    raise InvariantError(f"{record.id} was recorded before the record it supersedes")
        touched = {t for r in checked for t in getattr(r, "supersedes", ())}
        counts = Counter(t for r in self._records for t in getattr(r, "supersedes", ()) if t in touched)
        repeated = sorted(rid for rid, count in counts.items() if count > 1)
        if repeated:
            raise InvariantError(f"records superseded more than once: {repeated}")

    def _check_memory_lifecycle(self, checked: list[Any]) -> None:
        reviews = self._of_type("review_event")
        for memory in (r for r in checked if r.record_type == "memory"):
            accepted = any(
                e.decision == "accept" and e.target_id == memory.candidate_id
                and e.recorded_at <= memory.recorded_at
                for e in reviews
            )
            if not accepted:
                raise InvariantError(f"{memory.id} has no prior accept review for its candidate")
            if self._by_id[memory.candidate_id].record_type != "candidate_memory":
                raise InvariantError(f"{memory.id} candidate_id is not a candidate_memory")
        for candidate in (r for r in checked if r.record_type == "candidate_memory"):
            for source in candidate.derived_from:
                if self._by_id[source].record_type not in ("observation", "evidence"):
                    raise InvariantError(f"{candidate.id} derives from a non-observation/evidence record")

    def _check_evidence_support(self, checked: list[Any]) -> None:
        for record in checked:
            statement = getattr(record, "statement", "")
            if record.record_type in ("fact", "memory") and MASTERY_RE.search(statement):
                raise InvariantError(f"{record.id} asserts mastery; evidence supports signals, not proficiency")
            if record.record_type == "fact" and record.module == "knowledge" and record.predicate in SIGNALS:
                supported = any(
                    record.predicate in getattr(self._by_id[eid], "signals", ()) for eid in record.evidence_ids
                )
                if not supported:
                    raise InvariantError(
                        f"{record.id} claims signal {record.predicate!r} without evidence carrying it"
                    )

    def _check_idempotency(self) -> None:
        keys = Counter(obs.idempotency_key for obs in self._of_type("observation"))
        repeated = [key for key, count in keys.items() if count > 1]
        if repeated:
            raise InvariantError(f"duplicate observation idempotency keys: {repeated}")

    # ------------------------------------------------------------------ temporal views
    def _of_type(self, record_type: str) -> list[Any]:
        return [r for r in self._records if r.record_type == record_type]

    def _known(self, as_known_at: datetime | None) -> list[Any]:
        return [r for r in self._records if as_known_at is None or r.recorded_at <= as_known_at]

    def superseded_by(self, record_id: str) -> str | None:
        """Derived reverse link (only ``supersedes`` is authoritative)."""
        for record in self._records:
            if record_id in getattr(record, "supersedes", ()):
                return str(record.id)
        return None

    @staticmethod
    def _superseding_kinds(known: list[Any]) -> dict[str, str]:
        return {target: r.change_kind for r in known for target in getattr(r, "supersedes", ())}

    def current_facts(self, as_known_at: datetime | None = None) -> list[Any]:
        """Facts believed current at system time ``as_known_at`` (default: now)."""
        known = self._known(as_known_at)
        superseded = self._superseding_kinds(known)
        return [r for r in known if r.record_type == "fact" and r.id not in superseded
                and r.change_kind != "retraction"]

    def facts_valid_at(self, when: str, as_known_at: datetime | None = None) -> list[Any]:
        """Facts whose valid-time interval contains ``when`` (world changes keep old intervals)."""
        point = partial_date_range(when)[0]
        known = self._known(as_known_at)
        superseded = self._superseding_kinds(known)
        result = []
        for fact in (r for r in known if r.record_type == "fact"):
            if superseded.get(fact.id) in ("correction", "retraction") or fact.change_kind == "retraction":
                continue
            start = partial_date_range(fact.valid_from)[0] if fact.valid_from else None
            end = partial_date_range(fact.valid_until)[0] if fact.valid_until else None
            if (start is None or start <= point) and (end is None or point < end):
                result.append(fact)
        return result

    def current_evidence(self, source_id: str | None = None) -> list[Any]:
        """Latest Evidence version per source subject (retraction markers included)."""
        superseded = self._superseding_kinds(self._records)
        return [r for r in self._records if r.record_type == "evidence" and r.id not in superseded
                and (source_id is None or r.provenance.source_id == source_id)]

    def policy(self, as_known_at: datetime | None = None) -> ModulePolicy | None:
        policies = [r for r in self._known(as_known_at) if r.record_type == "module_policy"]
        return max(policies, key=lambda p: (p.epoch, p.recorded_at)) if policies else None

    def exposable(self, as_known_at: datetime | None = None) -> list[Any]:
        """Records a host may see: current, accepted, not revoked, module exposed (fail closed)."""
        known = self._known(as_known_at)
        policy = self.policy(as_known_at)
        if policy is None:
            return []
        superseded = self._superseding_kinds(known)
        reviews = [r for r in known if r.record_type == "review_event"]
        withdrawn = {e.target_id for e in reviews if e.decision in ("reject", "revoke")}
        accepted = {e.target_id for e in reviews if e.decision == "accept"}
        result = []
        for record in known:
            if record.record_type not in EXPOSABLE_TYPES or record.id in superseded or record.id in withdrawn:
                continue
            if record.record_type in ("fact", "evidence") and record.change_kind == "retraction":
                continue
            if getattr(record, "review_status", None) in ("quarantined", "pending_review"):
                continue
            if record.record_type == "memory" and (record.candidate_id not in accepted
                                                   or record.candidate_id in withdrawn):
                continue
            if not policy.modules[record.module].expose_enabled:
                continue
            result.append(record)
        return result

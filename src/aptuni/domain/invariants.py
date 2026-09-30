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

from aptuni.domain.evidence_profile import (
    AUTHORITY_GRANT_SOURCE_TYPES,
    EVIDENCE_PROFILE_TYPE,
    EVIDENCE_PROMOTION_REASON,
    EvidenceLineage,
    EvidenceProfileError,
    check_evidence_profile_fact,
)
from aptuni.domain.records import AUTHORITY_GRANTS, SIGNALS, CanonicalRecord, ModulePolicy, SourceConfig
from aptuni.domain.temporal import partial_date_range

MASTERY_RE = re.compile(r"\b(proficient|expert|mastery|mastered|fluent in)\b|精通|熟练掌握|专家级", re.IGNORECASE)
LINK_FIELDS = ("evidence_ids", "memory_ids", "derived_from", "contradicts")
SOURCE_REMOVED = "source_removed"  # rationale of the one review event that removes a source (ADR-0027)
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
        self._lineage: EvidenceLineage | None = None

    def __len__(self) -> int:
        return len(self._records)

    def records(self) -> list[Any]:
        return list(self._records)

    def ids(self) -> set[str]:
        return set(self._by_id)

    def get(self, record_id: str) -> Any:
        return self._by_id[record_id]

    def lineage(self) -> EvidenceLineage:
        """Supersession, owner-decision and authority indexes, built once for this immutable view."""
        if self._lineage is None:
            self._lineage = EvidenceLineage(self._records)
        return self._lineage

    def effective_source(self, source: SourceConfig) -> SourceConfig:
        """A source with its owner-granted authority applied (ADR-0028 amendment); never committed."""
        authority = self.lineage().authority(source)
        if authority == tuple(sorted(source.authority.primary_for)):
            return source
        return source.model_copy(update={"authority": source.authority.model_copy(update={"primary_for": authority})})

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
        self._check_profile_promotion(checked)
        self._check_evidence_support(checked)
        self._check_source_removal(checked)
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
            # ADR-0018: a policy promotion admits a memory exactly as an owner acceptance does.
            admitted = any(
                e.decision in ("accept", "promote") and e.target_id == memory.candidate_id
                and e.recorded_at <= memory.recorded_at
                for e in reviews
            )
            if not admitted:
                raise InvariantError(f"{memory.id} has no prior accept or promote review for its candidate")
            if self._by_id[memory.candidate_id].record_type != "candidate_memory":
                raise InvariantError(f"{memory.id} candidate_id is not a candidate_memory")
        for candidate in (r for r in checked if r.record_type == "candidate_memory"):
            for source in candidate.derived_from:
                if self._by_id[source].record_type not in ("observation", "evidence"):
                    raise InvariantError(f"{candidate.id} derives from a non-observation/evidence record")

    def _promotion_indexes(self) -> tuple[dict[str, list[Any]], dict[str, list[Any]]]:
        """Promoted-memory Facts by Memory and policy promotions by target, built once (Review 82 B5)."""
        facts_by_memory: dict[str, list[Any]] = {}
        for candidate in self._of_type("fact"):
            if candidate.type == "profile.promoted_memory":
                for memory_id in candidate.memory_ids:
                    facts_by_memory.setdefault(memory_id, []).append(candidate)
        promotions: dict[str, list[Any]] = {}
        for event in self._of_type("review_event"):
            if event.decision == "promote" and event.actor == "policy_auto":
                promotions.setdefault(event.target_id, []).append(event)
        return facts_by_memory, promotions

    def _check_profile_promotion(self, checked: list[Any]) -> None:
        """Bind policy promotions to exact Memory or authoritative-Evidence lineage."""
        facts_by_memory, promotions = self._promotion_indexes()
        for fact in (record for record in checked
                     if record.record_type == "fact" and record.type == "profile.promoted_memory"):
            if len(fact.memory_ids) != 1:
                raise InvariantError(f"{fact.id} profile promotion requires exactly one memory")
            memory_id = fact.memory_ids[0]
            if self._by_id[memory_id].record_type != "memory":
                raise InvariantError(f"{fact.id} profile promotion source is not a memory")
            memory = self._by_id[memory_id]
            promotion_events = promotions.get(memory_id, [])
            if not promotion_events:
                raise InvariantError(f"{fact.id} has no policy promotion event for its memory")
            if len(promotion_events) != 1:
                raise InvariantError(f"{memory_id} has more than one profile promotion event")
            if len(facts_by_memory.get(memory_id, [])) != 1:
                raise InvariantError(f"{memory_id} has more than one promoted profile fact")
            event = promotion_events[0]
            if not self._profile_fact_exact(fact, memory, event):
                raise InvariantError(f"{fact.id} does not exactly preserve its promoted memory claim")
        for fact in (record for record in checked
                     if record.record_type == "fact" and record.type == EVIDENCE_PROFILE_TYPE):
            self._check_evidence_profile_fact(fact, promotions)
        for event in (record for record in checked if record.record_type == "review_event"
                      and record.decision == "promote" and record.actor == "policy_auto"):
            self._check_profile_promotion_event(event, facts_by_memory, promotions)

    def _check_evidence_profile_fact(self, fact: Any, promotions: dict[str, list[Any]]) -> None:
        try:
            check_evidence_profile_fact(fact, self.lineage(), promotions.get(fact.id, []))
        except EvidenceProfileError as error:
            raise InvariantError(str(error)) from error

    def _check_profile_promotion_event(
        self, event: Any, facts_by_memory: dict[str, list[Any]], promotions: dict[str, list[Any]],
    ) -> None:
        target = self._by_id[event.target_id]
        if len(promotions.get(event.target_id, [])) != 1:
            raise InvariantError(f"{event.target_id} has more than one policy promotion event")
        if target.record_type == "candidate_memory":
            linked_memories = [record for record in self._of_type("memory")
                               if record.candidate_id == event.target_id
                               and record.change_kind == "assert" and not record.supersedes]
            if len(linked_memories) != 1:
                raise InvariantError(
                    f"{event.id} candidate promotion must admit exactly one root memory"
                )
        elif target.record_type == "memory":
            if len(facts_by_memory.get(event.target_id, [])) != 1:
                raise InvariantError(
                    f"{event.id} profile promotion must admit exactly one linked fact"
                )
        elif target.record_type == "fact" and target.type == EVIDENCE_PROFILE_TYPE:
            if event.schema_version != 3 or event.rationale_code != EVIDENCE_PROMOTION_REASON:
                raise InvariantError(f"{event.id} is not an authoritative Evidence promotion")
            self._check_evidence_profile_fact(target, promotions)
        else:
            raise InvariantError(
                f"{event.id} policy promotion target must be a candidate_memory, memory, "
                "or authoritative Evidence-derived fact"
            )

    @staticmethod
    def _profile_fact_exact(fact: Any, memory: Any, event: Any) -> bool:
        return (
            fact.statement == memory.statement
            and fact.module == memory.module
            and fact.provenance == memory.provenance
            and fact.valid_from == memory.valid_from
            and fact.valid_until == memory.valid_until
            and fact.evidence_ids == memory.evidence_ids
            and fact.observed_at == memory.recorded_at
            and fact.confidence == memory.confidence
            and fact.policy_epoch == event.policy_epoch
            and fact.recorded_at == event.recorded_at
            and fact.ingested_at == fact.recorded_at
            and fact.trust == "system"
            and fact.review_status == "auto_derived"
            and fact.subject == "self"
            and fact.predicate == "stable_memory"
            and fact.object is None
            and fact.change_kind == "assert"
            and not fact.supersedes
            and fact.retention.retention_class == "canonical"
            and fact.retention.purpose == "profile"
            and fact.retention.expires_at is None
            and not fact.retention.full_content
        )

    def _check_evidence_support(self, checked: list[Any]) -> None:
        for record in checked:
            if record.record_type == "evidence":
                self._check_evidence_ceiling(record)
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

    def _check_evidence_ceiling(self, evidence: Any) -> None:
        """ADR-0029 item 2: authority is a ceiling; a stronger signal needs ``<module>.<signal>``."""
        strong = [signal for signal in evidence.signals if signal != "exposure"]
        if not strong:
            return
        source = self._by_id.get(evidence.provenance.source_id or "")
        if source is None or source.record_type != "source_config":
            raise InvariantError(f"{evidence.id} carries {strong} without an approved source")
        authority = set(self.lineage().authority(source))
        beyond = [signal for signal in strong if f"{evidence.module}.{signal}" not in authority]
        if beyond:
            raise InvariantError(f"{evidence.id} carries {beyond} beyond its source authority")

    def _check_source_removal(self, checked: list[Any]) -> None:
        """ADR-0027: a source is removed by exactly one owner revoke that withdraws all it contributed.

        The only other owner decision on a source is an ADR-0028 authority grant, checked here too.
        """
        source_events = [event for event in self._of_type("review_event")
                         if getattr(self._by_id.get(event.target_id), "record_type", None) == "source_config"]
        grants = [event for event in source_events if event.rationale_code in AUTHORITY_GRANTS]
        removals = [event for event in source_events if event.rationale_code not in AUTHORITY_GRANTS]
        for event in removals:
            if (event.decision, event.actor, event.rationale_code) != ("revoke", "user_cli", SOURCE_REMOVED):
                raise InvariantError(f"{event.id} is not a valid source removal")
        self._check_authority_grants(grants, removals)
        counts = Counter(event.target_id for event in removals)
        if any(count > 1 for count in counts.values()):
            raise InvariantError("a source was removed more than once")
        touched = {record.id for record in checked}
        for source_id in counts:
            current = self.current_evidence(source_id)
            relevant = touched & ({source_id} | {e.id for e in current} | {e.id for e in removals})
            if relevant and any(item.change_kind != "retraction" for item in current):
                raise InvariantError(f"removed source {source_id} still has current evidence")

    def _check_authority_grants(self, grants: list[Any], removals: list[Any]) -> None:
        removed_at = {event.target_id: event.recorded_at for event in removals}
        seen: set[tuple[str, str]] = set()
        for event in grants:
            source = self._by_id[event.target_id]
            key = (event.target_id, event.rationale_code)
            if (
                (event.schema_version, event.decision, event.actor) != (3, "accept", "user_cli")
                or source.source_type != AUTHORITY_GRANT_SOURCE_TYPES[event.rationale_code]
                or AUTHORITY_GRANTS[event.rationale_code] in source.authority.primary_for
                or key in seen
                or (event.target_id in removed_at and removed_at[event.target_id] <= event.recorded_at)
            ):
                raise InvariantError(f"{event.id} is not a valid source-authority grant")
            seen.add(key)

    def removed_source_ids(self) -> set[str]:
        """Sources the owner removed (ADR-0027); they are never synced, listed or exposed again."""
        return {event.target_id for event in self._of_type("review_event")
                if event.decision == "revoke" and event.rationale_code == SOURCE_REMOVED
                and self._by_id.get(event.target_id) is not None
                and self._by_id[event.target_id].record_type == "source_config"}

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
        successor = self.lineage().successor(record_id)
        return None if successor is None else str(successor.id)

    @staticmethod
    def _superseding_kinds(known: list[Any]) -> dict[str, str]:
        return {target: r.change_kind for r in known for target in getattr(r, "supersedes", ())}

    def current_facts(self, as_known_at: datetime | None = None) -> list[Any]:
        """Facts believed current at system time ``as_known_at`` (default: now)."""
        known = self._known(as_known_at)
        superseded = self._superseding_kinds(known)
        withdrawn = {r.target_id for r in known if r.record_type == "review_event"
                     and r.decision in ("reject", "revoke")}
        current_evidence = {
            record.id for record in known
            if record.record_type == "evidence" and record.id not in superseded
            and record.change_kind != "retraction"
            and record.provenance.source_id not in withdrawn
        }
        return [
            record
            for record in known
            if record.record_type == "fact"
            and record.id not in superseded
            and record.id not in withdrawn
            and record.change_kind != "retraction"
            and (
                record.type != EVIDENCE_PROFILE_TYPE
                or bool(set(record.evidence_ids) & current_evidence)
            )
        ]

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

    def revoked_ids(self) -> set[str]:
        """Ids withdrawn by review (ADR-0018 §4).

        A record is withdrawn only by `revoke` or `reject`, never by *any* review event. Before
        ADR-0018 the only event that could target a memory was a revocation, so the looser rule
        happened to agree; it stops agreeing as soon as `accept` or `pin` can target a memory.
        Every consumer shares this one derivation so none of them can drift.
        """
        return {r.target_id for r in self._of_type("review_event") if r.decision in ("reject", "revoke")}

    def decided_candidate_ids(self) -> set[str]:
        """Candidate ids that already have a review decision, so they are no longer pending.

        Deliberately distinct from `revoked_ids`: any decision settles a candidate, while only a
        withdrawal hides a record.
        """
        return {r.target_id for r in self._of_type("review_event")}

    def exposable(self, as_known_at: datetime | None = None) -> list[Any]:
        """Records a host may see: current, accepted, not revoked, module exposed (fail closed)."""
        known = self._known(as_known_at)
        policy = self.policy(as_known_at)
        if policy is None:
            return []
        superseded = self._superseding_kinds(known)
        reviews = [r for r in known if r.record_type == "review_event"]
        withdrawn = {e.target_id for e in reviews if e.decision in ("reject", "revoke")}
        accepted = {e.target_id for e in reviews if e.decision in ("accept", "promote")}
        current_evidence = {
            record.id for record in known
            if record.record_type == "evidence" and record.id not in superseded
            and record.change_kind != "retraction"
            and record.provenance.source_id not in withdrawn
        }
        result = []
        for record in known:
            if record.record_type not in EXPOSABLE_TYPES or record.id in superseded or record.id in withdrawn:
                continue
            if record.record_type in ("fact", "evidence") and record.change_kind == "retraction":
                continue
            if record.record_type == "evidence" and record.provenance.source_id in withdrawn:
                continue  # ADR-0027 defense in depth: nothing from a removed source is exposed
            if record.record_type == "fact" and record.type == EVIDENCE_PROFILE_TYPE and not (
                set(record.evidence_ids) & current_evidence
            ):
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

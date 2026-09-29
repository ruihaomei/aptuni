"""Canonical ADR-0028 derivation shared by the writer and the Vault invariant.

One definition of which Evidence may form a ``profile.evidence_signal`` Fact and exactly what that
Fact and its promotion event contain, so a malformed or future writer cannot commit a different
claim (Review 82 B2). ``EvidenceLineage`` is built once per record set, so neither the writer nor
validation rescans the Vault per Evidence item (Review 82 B5).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from aptuni.domain.ids import deterministic_id, sha256_text
from aptuni.domain.records import AUTHORITY_GRANTS

SEMANTIC_SIGNALS = ("demonstrated", "applied", "studied")  # strongest first
EVIDENCE_PROFILE_TYPE = "profile.evidence_signal"
EVIDENCE_PROMOTION_REASON = "policy_authoritative_evidence"
EVIDENCE_PROMOTION_NONCE = "policy_auto"
#: Source types whose ingest honours a granted dimension, by grant rationale (ADR-0028 amendment).
AUTHORITY_GRANT_SOURCE_TYPES: dict[str, str] = {"source_authority_studied": "marginnote4"}


class EvidenceProfileError(ValueError):
    """An Evidence-derived Fact or its event departs from the canonical derivation."""


def strongest_signal(signals: Iterable[str]) -> str | None:
    present = set(signals)
    return next((signal for signal in SEMANTIC_SIGNALS if signal in present), None)


def evidence_profile_statement(signal: str, subject: str) -> str:
    subject = " ".join(subject.split())[:440].rstrip(". ")
    if signal == "studied":
        return f"Studied {subject}."
    if signal == "applied":
        return f"Applied {subject}."
    return f"Demonstrated work involving {subject}."


def evidence_fact_id(evidence_id: str) -> str:
    return deterministic_id("fct", f"evidence-profile:{evidence_id}")


def evidence_event_id(evidence_id: str) -> str:
    return deterministic_id("rev", f"evidence-profile:{evidence_id}")


def evidence_event_digest(evidence_id: str, source_id: str, epoch: int, signal: str) -> str:
    return sha256_text(f"evidence_profile|{evidence_id}|{source_id}|{epoch}|{signal}")


def successor_change_kind(evidence: Any, predecessor: Any | None) -> str:
    """A derived Fact mirrors its Evidence's change; with no predecessor it is a fresh assertion."""
    if predecessor is None:
        return "assert"
    return "correction" if evidence.change_kind == "assert" else str(evidence.change_kind)


class EvidenceLineage:
    """Indexes built once: records by id, reverse supersession, owner withdrawals and grants.

    ``purged`` holds deletion-ledger digests. A purged derived Fact is an owner withdrawal of its
    lineage: its deterministic id can never be committed again (Review 83 B1).
    """

    def __init__(self, records: Iterable[Any], purged: frozenset[str] = frozenset()) -> None:
        self._purged = purged
        self._by_id: dict[str, Any] = {}
        self._successor: dict[str, Any] = {}
        self._owner_withdrawn: set[str] = set()
        self._grants: dict[str, set[str]] = {}
        for record in records:
            self.add(record)

    def add(self, record: Any) -> None:
        self._by_id[record.id] = record
        for target in getattr(record, "supersedes", ()):
            self._successor[target] = record
        if record.record_type != "review_event" or record.actor != "user_cli":
            return
        if record.decision in ("reject", "revoke"):
            self._owner_withdrawn.add(record.target_id)
        elif record.decision == "accept" and record.rationale_code in AUTHORITY_GRANTS:
            self._grants.setdefault(record.target_id, set()).add(AUTHORITY_GRANTS[record.rationale_code])

    def get(self, record_id: str) -> Any | None:
        return self._by_id.get(record_id)

    def successor(self, record_id: str) -> Any | None:
        return self._successor.get(record_id)

    def authority(self, source: Any) -> tuple[str, ...]:
        """The source's approved authority plus every dimension the owner granted later."""
        granted = self._grants.get(source.id, set())
        return tuple(sorted(set(source.authority.primary_for) | granted))

    def ancestors(self, evidence: Any) -> Iterator[Any]:
        """Earlier Evidence versions of the same source subject, nearest first."""
        seen: set[str] = set()
        frontier = list(evidence.supersedes)
        while frontier:
            record = self._by_id.get(frontier.pop(0))
            if record is None or record.id in seen or record.record_type != "evidence":
                continue
            seen.add(record.id)
            yield record
            frontier.extend(record.supersedes)

    def predecessor_fact(self, evidence: Any) -> Any | None:
        """The derived Fact of the nearest earlier Evidence version that formed one."""
        for ancestor in self.ancestors(evidence):
            fact = self._by_id.get(evidence_fact_id(ancestor.id))
            if fact is not None:
                return fact
        return None

    def owner_decided(self, evidence: Any) -> bool:
        """The owner rejected, corrected or purged a Fact derived anywhere in this Evidence lineage."""
        for version in (evidence, *self.ancestors(evidence)):
            fact_id = evidence_fact_id(version.id)
            if self._purged and sha256_text(fact_id) in self._purged:
                return True
            if fact_id not in self._by_id:
                continue
            if fact_id in self._owner_withdrawn:
                return True
            successor = self._successor.get(fact_id)
            if successor is not None and getattr(successor, "trust", None) == "user_declared":
                return True
        return False


def check_evidence_profile_fact(fact: Any, lineage: EvidenceLineage, promotions: list[Any]) -> None:
    """Raise unless ``fact`` and its one promotion event are exactly the canonical derivation."""
    if len(fact.evidence_ids) != 1 or fact.memory_ids:
        raise EvidenceProfileError(f"{fact.id} Evidence promotion requires exactly one Evidence record")
    evidence = lineage.get(fact.evidence_ids[0])
    if evidence is None or evidence.record_type != "evidence" or evidence.change_kind == "retraction":
        raise EvidenceProfileError(f"{fact.id} Evidence promotion support is not positive Evidence")
    source = lineage.get(evidence.provenance.source_id or "")
    signal = strongest_signal(evidence.signals)
    if (
        source is None
        or source.record_type != "source_config"
        or signal is None
        or fact.predicate != signal
        or f"{evidence.module}.{signal}" not in lineage.authority(source)
    ):
        raise EvidenceProfileError(f"{fact.id} exceeds its source authority")
    if fact.id != evidence_fact_id(evidence.id):
        raise EvidenceProfileError(f"{fact.id} is not the one deterministic Fact for its Evidence")
    if len(promotions) != 1:
        raise EvidenceProfileError(f"{fact.id} requires exactly one policy promotion event")
    event = promotions[0]
    predecessor = lineage.predecessor_fact(evidence)
    if not (
        event.id == evidence_event_id(evidence.id)
        and event.schema_version == 3
        and event.rationale_code == EVIDENCE_PROMOTION_REASON
        and event.nonce_id == EVIDENCE_PROMOTION_NONCE
        and event.action_digest == evidence_event_digest(evidence.id, source.id, event.policy_epoch, signal)
        and event.recorded_at == fact.recorded_at
        and event.policy_epoch == fact.policy_epoch
    ):
        raise EvidenceProfileError(f"{fact.id} promotion event is not the canonical Evidence promotion")
    if fact.supersedes != ((predecessor.id,) if predecessor else ()) or (
        fact.change_kind != successor_change_kind(evidence, predecessor)
    ):
        raise EvidenceProfileError(f"{fact.id} does not continue its Evidence lineage exactly")
    if not _preserves(fact, evidence, signal):
        raise EvidenceProfileError(f"{fact.id} does not exactly preserve authoritative Evidence")


def _preserves(fact: Any, evidence: Any, signal: str) -> bool:
    return (
        fact.module == evidence.module
        and fact.provenance.source_id == evidence.provenance.source_id
        and fact.provenance.episode == evidence.provenance.episode
        and fact.provenance.locator is None
        and fact.subject == evidence.subject
        and fact.object is True
        and fact.statement == evidence_profile_statement(signal, evidence.subject)
        and fact.valid_from == evidence.valid_from
        and fact.valid_until == evidence.valid_until
        and fact.confidence is None
        and fact.trust == evidence.trust
        and fact.review_status == "auto_derived"
        and fact.observed_at == evidence.observed_at
        and fact.ingested_at == fact.recorded_at
        and fact.retention.retention_class == "canonical"
        and fact.retention.purpose == "profile"
        and fact.retention.expires_at is None
        and not fact.retention.full_content
    )

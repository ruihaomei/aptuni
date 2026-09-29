"""Authoritative Evidence → active Profile Fact policy (ADR-0028).

The canonical shape of each Fact comes from :mod:`aptuni.domain.evidence_profile`, which the Vault
invariant also enforces. This module decides *whether* to derive one: exact source authority, the
module switches, the review policy and, across the whole Evidence lineage, the owner's earlier
rejection or correction (Review 82 B1). Indexes are built once per batch (Review 82 B5).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from aptuni.domain.evidence_profile import (
    EVIDENCE_PROFILE_TYPE,
    EVIDENCE_PROMOTION_NONCE,
    EVIDENCE_PROMOTION_REASON,
    EvidenceLineage,
    evidence_event_digest,
    evidence_event_id,
    evidence_fact_id,
    evidence_profile_statement,
    strongest_signal,
    successor_change_kind,
)
from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import Fact, Module, Provenance, RetentionLabel, ReviewEvent, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.policy.promotion import review_policy_of

__all__ = ["EVIDENCE_PROFILE_TYPE", "EvidenceProfileWriter", "derive_evidence_profile"]

PROFILE_RETENTION = RetentionLabel(
    retention_class="canonical", purpose="profile", expires_at=None, full_content=False,
)


class EvidenceProfileWriter:
    """Derives Evidence-backed Profile records for one batch against a single snapshot."""

    def __init__(self, records: RecordSet, purged: frozenset[str]) -> None:
        self._lineage = EvidenceLineage(records.records(), purged)
        self._module_policy = records.policy()
        self._review_policy = review_policy_of(records)

    def derive(self, evidence: Any, source: SourceConfig) -> list[Any]:
        """Return one atomic promotion event + Fact, or nothing when policy does not allow it."""
        if self._lineage.get(evidence.id) is None:
            self._lineage.add(evidence)
        signal = strongest_signal(evidence.signals)
        if (
            evidence.change_kind == "retraction"
            or signal is None
            or f"{evidence.module}.{signal}" not in self._lineage.authority(source)
            or not self._module_allows(evidence.module)
        ):
            return []
        fact_id = evidence_fact_id(evidence.id)
        event_id = evidence_event_id(evidence.id)
        if self._lineage.get(fact_id) is not None or self._lineage.get(event_id) is not None:
            return []
        if self._lineage.owner_decided(evidence):
            return []
        predecessor = self._lineage.predecessor_fact(evidence)
        if predecessor is not None and self._lineage.successor(predecessor.id) is not None:
            return []  # already continued by another record; never supersede twice
        records = self._records_for(evidence, source, signal, fact_id, event_id, predecessor)
        for record in records:
            self._lineage.add(record)
        return records

    def _module_allows(self, module: Module) -> bool:
        switch = None if self._module_policy is None else self._module_policy.modules.get(module)
        return (
            switch is not None
            and switch.ingest_enabled
            and switch.expose_enabled
            and self._review_policy.auto_promotion_enabled
            and module not in self._review_policy.sensitive_modules
        )

    def _records_for(
        self, evidence: Any, source: SourceConfig, signal: str, fact_id: str, event_id: str,
        predecessor: Any | None,
    ) -> list[Any]:
        assert self._module_policy is not None
        epoch = self._module_policy.epoch
        now = utc_now()
        fact = Fact(
            record_type="fact", id=fact_id, schema_version=1, recorded_at=now,
            valid_from=evidence.valid_from, valid_until=evidence.valid_until, module=evidence.module,
            provenance=Provenance(
                source_id=evidence.provenance.source_id, episode=evidence.provenance.episode, locator=None,
            ),
            trust=evidence.trust, retention=PROFILE_RETENTION, policy_epoch=epoch, confidence=None,
            review_status="auto_derived",
            supersedes=(predecessor.id,) if predecessor is not None else (),
            change_kind=successor_change_kind(evidence, predecessor),
            type=EVIDENCE_PROFILE_TYPE, subject=evidence.subject, predicate=signal, object=True,
            statement=evidence_profile_statement(signal, evidence.subject), evidence_ids=(evidence.id,),
            memory_ids=(), observed_at=evidence.observed_at, ingested_at=now,
        )
        event = ReviewEvent(
            record_type="review_event", id=event_id, schema_version=3, recorded_at=now, target_id=fact.id,
            decision="promote", actor="policy_auto",
            action_digest=evidence_event_digest(evidence.id, source.id, epoch, signal),
            policy_epoch=epoch, rationale_code=EVIDENCE_PROMOTION_REASON, nonce_id=EVIDENCE_PROMOTION_NONCE,
        )
        return [event, fact]


def derive_evidence_profile(
    candidates: Iterable[Any], records: RecordSet, sources: Mapping[str, SourceConfig], *,
    purged: frozenset[str],
) -> list[Any]:
    """Derive every eligible candidate in one pass; Evidence of unknown sources is skipped.

    ``purged`` is the Vault's deletion-ledger digests; it is required so no caller can forget that a
    purged derivation must never be recreated.
    """
    writer = EvidenceProfileWriter(records, purged)
    written: list[Any] = []
    for evidence in candidates:
        source = sources.get(evidence.provenance.source_id or "")
        if source is not None:
            written.extend(writer.derive(evidence, source))
    return written

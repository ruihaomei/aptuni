"""Conservative Memory → Profile Fact policy (ADR-0020)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from aptuni.domain.ids import new_id, sha256_text
from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import Fact, RetentionLabel, ReviewEvent
from aptuni.domain.temporal import utc_now
from aptuni.policy.promotion import review_policy_of, review_state_of

ProfilePromotionAction = Literal["promote", "hold", "deny"]
ProfileReviewState = Literal["accepted", "auto_promoted_pending_review", "revoked"]
AUTO_PROFILE_TYPES = frozenset({"profile.promoted_memory", "profile.evidence_signal"})

PROFILE_RETENTION = RetentionLabel(
    retention_class="canonical", purpose="profile", expires_at=None, full_content=False,
)


@dataclass(frozen=True)
class ProfilePromotionOutcome:
    action: ProfilePromotionAction
    reason: str


def evaluate_profile_memory(memory: Any, records: RecordSet) -> ProfilePromotionOutcome:
    """Evaluate only canonical, explicit stability signals; never infer semantics."""
    modules = records.policy()
    if modules is None:
        return ProfilePromotionOutcome("deny", "no_module_policy")
    switch = modules.modules.get(memory.module)
    try:
        candidate = records.get(memory.candidate_id)
    except KeyError:
        candidate = None
    try:
        supports = [records.get(record_id) for record_id in candidate.derived_from] if candidate else []
    except KeyError:
        supports = []
    owner_support = bool(supports) and all(
        support.record_type == "observation"
        and support.trust == "user_declared"
        and support.provenance.episode == "cli"
        for support in supports
    )
    unresolved = records.decided_candidate_ids()
    contradiction = any(
        record.record_type == "candidate_memory"
        and memory.id in record.contradicts
        and record.id not in unresolved
        for record in records.records()
    )
    already_promoted = any(
        fact.record_type == "fact"
        and memory.id in fact.memory_ids
        for fact in records.records()
    )
    denials = (
        (switch is None or not switch.ingest_enabled, "module_ingest_disabled"),
        (switch is not None and not switch.expose_enabled, "module_expose_disabled"),
    )
    holds = (
        (not review_policy_of(records).auto_promotion_enabled, "auto_promotion_disabled"),
        (memory.id in records.revoked_ids() or records.superseded_by(memory.id) is not None,
         "memory_not_current"),
        (review_state_of(memory, records) != "pinned", "memory_not_pinned"),
        (candidate is None, "missing_candidate"),
        (candidate is not None and candidate.record_type != "candidate_memory", "invalid_candidate"),
        (not supports, "missing_support"),
        (bool(supports) and not owner_support, "not_owner_declared_cli"),
        (contradiction, "unresolved_contradiction"),
        (already_promoted, "already_promoted"),
    )
    for action, rules in (("deny", denials), ("hold", holds)):
        for applies, reason in rules:
            if applies:
                return ProfilePromotionOutcome(action, reason)  # type: ignore[arg-type]
    return ProfilePromotionOutcome("promote", "pinned_owner_declared_memory")


def profile_promotion_records(memory: Any, records: RecordSet) -> list[Any]:
    outcome = evaluate_profile_memory(memory, records)
    if outcome.action != "promote":
        return []
    now = utc_now()
    event = ReviewEvent(
        record_type="review_event", id=new_id("rev"), schema_version=2, recorded_at=now,
        target_id=memory.id, decision="promote", actor="policy_auto",
        action_digest=sha256_text(
            f"profile_promote|{memory.id}|{records.policy().epoch}|{outcome.reason}"  # type: ignore[union-attr]
        ),
        policy_epoch=records.policy().epoch,  # type: ignore[union-attr]
        rationale_code="policy_pinned_owner_memory", nonce_id="policy_auto",
    )
    fact = Fact(
        record_type="fact", id=new_id("fct"), schema_version=1, recorded_at=now,
        valid_from=memory.valid_from, valid_until=memory.valid_until, module=memory.module,
        provenance=memory.provenance, trust="system", retention=PROFILE_RETENTION,
        policy_epoch=records.policy().epoch, confidence=memory.confidence,  # type: ignore[union-attr]
        review_status="auto_derived", supersedes=(), change_kind="assert",
        type="profile.promoted_memory", subject="self", predicate="stable_memory", object=None,
        statement=memory.statement, evidence_ids=memory.evidence_ids, memory_ids=(memory.id,),
        observed_at=memory.recorded_at, ingested_at=now,
    )
    return [event, fact]


def profile_review_state_of(fact: Any, records: RecordSet) -> ProfileReviewState:
    events = [record for record in records.records()
              if record.record_type == "review_event" and record.target_id == fact.id]
    if any(event.decision in ("reject", "revoke") for event in events):
        return "revoked"
    if any(event.decision == "accept" for event in events):
        return "accepted"
    if fact.type == "profile.evidence_signal":
        # ADR-0028: the exact authority policy is the approval. Human actions are correction or
        # rejection, never a second per-item approval queue.
        return "accepted"
    promoted = any(
        event.record_type == "review_event"
        and event.decision == "promote"
        and event.actor == "policy_auto"
        and event.target_id in fact.memory_ids
        for event in records.records()
    )
    return "auto_promoted_pending_review" if promoted else "accepted"

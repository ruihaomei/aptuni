"""Automatic promotion eligibility and the derived review state (ADR-0018).

The promoter is the core's own policy evaluated over canonical records. It is never a source, a
model or a host: ADR-0011's rule that no source or model content can act as the reviewer stands,
which is why the resulting `ReviewEvent` carries `actor="policy_auto"` rather than `user_cli`.

Every rule fails towards *asking* rather than towards promoting. A candidate the policy will not
promote is not lost: it keeps the ADR-0013 confirmation path it has today.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import ReviewPolicy

PromotionAction = Literal["promote", "confirm", "deny"]
ReviewState = Literal["accepted", "auto_promoted_pending_review", "pinned", "revoked"]

#: Used whenever the Vault holds no `review_policy` record. The record's own field defaults are the
#: single source of these numbers, so the defaults cannot drift between the schema and the policy.
DEFAULT_REVIEW_POLICY = ReviewPolicy(
    record_type="review_policy", id="rvp_00000000000000000000000000",
    # A fixed timestamp: this is a constant, not a record, and it is never committed. Capturing
    # `utc_now()` at import would make a module-level value differ between processes.
    schema_version=1, recorded_at=datetime(2026, 1, 1, tzinfo=UTC), epoch=0,
)


@dataclass(frozen=True)
class PromotionOutcome:
    """What the policy decided, and the machine-readable reason the owner can be shown."""

    action: PromotionAction
    reason: str


def review_policy_of(records: RecordSet) -> ReviewPolicy:
    """The current review policy, or the documented defaults when none has been recorded."""
    policies: list[ReviewPolicy] = [r for r in records.records() if r.record_type == "review_policy"]
    if not policies:
        return DEFAULT_REVIEW_POLICY
    return max(policies, key=lambda r: (r.epoch, r.recorded_at))


def _owner_stated(candidate: Any, records: RecordSet) -> bool:
    """True when every supporting Observation is the owner speaking through the CLI.

    A `host_proposal` never qualifies. A candidate whose support cannot be resolved does not
    qualify either, so a dangling link asks rather than promotes.
    """
    supports = [records.get(rid) for rid in candidate.derived_from if rid in records.ids()]
    if len(supports) != len(candidate.derived_from) or not supports:
        return False
    return all(r.trust == "user_declared" and r.provenance.episode == "cli" for r in supports)


def _contradicts_record_in_force(candidate: Any, records: RecordSet) -> bool:
    """A contradiction only blocks while the contradicted record is still standing."""
    if not candidate.contradicts:
        return False
    revoked = records.revoked_ids()
    in_force = {r.id for r in records.records()
                if r.record_type in ("memory", "fact") and r.id not in revoked
                and records.superseded_by(r.id) is None}
    return bool(set(candidate.contradicts) & in_force)


def evaluate_candidate(candidate: Any, records: RecordSet, policy: ReviewPolicy) -> PromotionOutcome:
    """Decide whether this candidate may be promoted without asking the owner (ADR-0018 §2).

    The rules are an ordered table so the policy stays readable as it grows, and so the first
    reason that applies is the one the owner is shown. Denials come before questions: there is no
    point asking about something the module policy forbids outright.
    """
    modules = records.policy()
    if modules is None:
        return PromotionOutcome("deny", "no_module_policy")
    switch = modules.modules.get(candidate.module)

    # Promotion makes a record active and exposable, so a module that may not ingest or may not
    # expose must not gain one behind the owner's back. These deny rather than ask.
    denials = (
        (switch is None or not switch.ingest_enabled, "module_ingest_disabled"),
        (switch is not None and not switch.expose_enabled, "module_expose_disabled"),
    )
    questions = (
        (not policy.auto_promotion_enabled, "auto_promotion_disabled"),
        (not _owner_stated(candidate, records), "not_owner_stated"),
        (candidate.module in policy.sensitive_modules, "sensitive_module"),
        (_contradicts_record_in_force(candidate, records), "contradicts_record_in_force"),
    )
    for action, rules in (("deny", denials), ("confirm", questions)):
        for applies, reason in rules:
            if applies:
                return PromotionOutcome(action, reason)  # type: ignore[arg-type]
    return PromotionOutcome("promote", "owner_stated")


def review_state_of(memory: Any, records: RecordSet) -> ReviewState:
    """Derive a Memory's review state from the ledger alone (ADR-0018 §3).

    Nothing here is stored on the Memory: the events are canonical, the state is a projection of
    them, which is what keeps a single record from disagreeing with its own history.
    """
    on_memory = [r for r in records.records()
                 if r.record_type == "review_event" and r.target_id == memory.id]
    if any(r.decision in ("revoke", "reject") for r in on_memory):
        return "revoked"
    if any(r.decision == "pin" for r in on_memory):
        return "pinned"
    if any(r.decision == "accept" for r in on_memory):
        return "accepted"
    promoted = any(r.decision == "promote" and r.actor == "policy_auto"
                   for r in records.records()
                   if r.record_type == "review_event" and r.target_id == memory.candidate_id)
    return "auto_promoted_pending_review" if promoted else "accepted"


def pending_review_memories(records: RecordSet) -> list[Any]:
    """Memories the policy promoted that the owner has not looked at yet. Pinned never counts."""
    return [r for r in records.records()
            if r.record_type == "memory" and review_state_of(r, records) == "auto_promoted_pending_review"]

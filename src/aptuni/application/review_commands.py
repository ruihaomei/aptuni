"""Retrospective review of automatically promoted memories (ADR-0018 §5, §6).

Automatic promotion moves the owner's decision from *before* the memory exists to *after*. These
commands are that "after": settle a promoted memory, correct it, withdraw it, or pin it so the
policy leaves it alone. None of them is a confirmation ceremony — the memory is already active, so
there is no irreversible egress to guard. Withdrawing one is the cheap, reversible direction, and
`forget` keeps its ADR-0011 confirmation for the deliberate-destruction case.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from aptuni.application.errors import AptuniError
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id, sha256_text
from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import Memory, ReviewEvent, ReviewPolicy
from aptuni.domain.temporal import utc_now
from aptuni.policy.modules import can_ingest
from aptuni.policy.promotion import (
    ReviewState,
    evaluate_candidate,
    pending_review_memories,
    review_policy_of,
    review_state_of,
)

ReviewAction = Literal["accept", "reject", "pin"]
_SETTLED: dict[str, ReviewState] = {"accept": "accepted", "reject": "revoked", "pin": "pinned"}


@dataclass(frozen=True)
class ReviewReminder:
    """Whether to mention the review queue, and why. Never a blocking prompt (ADR-0018 §6)."""

    pending: int
    due: bool
    reason: str
    threshold: int
    next_due_at: datetime | None


def promotion_records(candidate: Any, records: RecordSet, epoch: int,
                      pending: Sequence[Any] = ()) -> list[Any]:
    """Build the Memory and its `policy_auto` promote event, or nothing (ADR-0018 §1).

    Both records go in the caller's single commit, so a memory can never exist without the event
    that admitted it, and a crash cannot leave one without the other. `pending` carries the
    records of that same uncommitted batch — the candidate's own Observation lives there, not in
    the snapshot, so eligibility has to see it or every candidate would look unsupported.
    """
    visible = RecordSet([*records.records(), *pending]) if pending else records
    outcome = evaluate_candidate(candidate, visible, review_policy_of(visible))
    if outcome.action != "promote":
        return []
    now = utc_now()
    digest = sha256_text(f"policy_promote|{candidate.id}|{epoch}|{outcome.reason}")
    event = ReviewEvent(
        record_type="review_event", id=new_id("rev"), schema_version=2, recorded_at=now,
        target_id=candidate.id, decision="promote", actor="policy_auto", action_digest=digest,
        policy_epoch=epoch, rationale_code=f"policy_{outcome.reason}", nonce_id="policy_auto",
    )
    memory = Memory(
        record_type="memory", id=new_id("mem"), schema_version=1, recorded_at=now,
        valid_from=None, valid_until=None, module=candidate.module, provenance=candidate.provenance,
        trust=candidate.trust, retention=candidate.retention, policy_epoch=epoch, confidence=None,
        review_status="accepted", supersedes=(), change_kind="assert",
        candidate_id=candidate.id, evidence_ids=(), statement=candidate.statement,
    )
    return [event, memory]


class ReviewCommands:
    """Mixed into ``AptuniService``; relies on its snapshot/commit helpers."""

    workspace: Workspace

    def snapshot(self) -> tuple[int, RecordSet]:
        raise NotImplementedError

    def records(self) -> RecordSet:
        raise NotImplementedError

    def _commit(self, records: list[Any], expected_seq: int) -> None:
        raise NotImplementedError

    # ---------------------------------------------------------------- review policy
    def review_policy(self) -> ReviewPolicy:
        return review_policy_of(self.records())

    def set_review_policy(self, **changes: Any) -> ReviewPolicy:
        """Record a new review policy. An invalid change fails closed, keeping the current one."""
        seq, records = self.snapshot()
        current = review_policy_of(records)
        try:
            updated = ReviewPolicy(
                record_type="review_policy", id=new_id("rvp"), schema_version=1,
                recorded_at=utc_now(), epoch=current.epoch + 1,
                **{**current.model_dump(exclude={"record_type", "id", "schema_version",
                                                 "recorded_at", "epoch"}), **changes},
            )
        except (ValidationError, ValueError, TypeError) as error:
            raise AptuniError("invalid_review_policy", "That review policy is not valid.") from error
        self._commit([updated], seq)
        return updated

    # ---------------------------------------------------------------- the pending queue
    def review_pending(self) -> list[Any]:
        return pending_review_memories(self.records())

    def review_state(self, memory_id: str) -> ReviewState:
        records = self.records()
        memory = next((r for r in records.records()
                       if r.record_type == "memory" and r.id == memory_id), None)
        if memory is None:
            raise AptuniError("memory_not_current", f"No memory with id {memory_id}.")
        return review_state_of(memory, records)

    # ---------------------------------------------------------------- decisions
    def review_memory(self, memory_id: str, action: ReviewAction) -> ReviewState:
        """Settle one promoted memory. Repeating a decision is a no-op, not a second event."""
        seq, records = self.snapshot()
        memory = self._reviewable(records, memory_id)
        state = review_state_of(memory, records)
        # Idempotence is decided from the events already on this memory, not from the collapsed
        # state: `pin` outranks `accept` in that collapse, so a pinned memory would otherwise
        # never read back as "accepted" and every repeat would append again (Review 56 B2).
        already = {r.decision for r in records.records()
                   if r.record_type == "review_event" and r.target_id == memory_id}
        if action in already:
            return state
        if state == "revoked":
            raise AptuniError("memory_not_current", "That memory is no longer current.")
        epoch = records.policy().epoch  # type: ignore[union-attr]
        digest = sha256_text(f"review|{action}|{memory_id}|{epoch}")
        decision: Any = action
        # Only `pin` needs schema v2, so accept/reject stay readable by a v1 reader (ADR-0018 §7).
        self._commit([ReviewEvent(
            record_type="review_event", id=new_id("rev"), schema_version=2 if action == "pin" else 1,
            recorded_at=utc_now(), target_id=memory_id, decision=decision, actor="user_cli",
            action_digest=digest, policy_epoch=epoch, rationale_code=f"owner_{action}",
            nonce_id=f"review-{memory_id}",
        )], seq)
        return review_state_of(memory, self.records())

    def edit_memory(self, memory_id: str, statement: str) -> str:
        """Correct a promoted memory: the replacement supersedes it and the original stays."""
        statement = " ".join(statement.split())
        seq, records = self.snapshot()
        memory = self._reviewable(records, memory_id)
        if review_state_of(memory, records) == "revoked":
            raise AptuniError("memory_not_current", "That memory is no longer current.")
        modules = records.policy()
        # A correction creates content, so it honours `ingest_enabled` exactly as `observe`,
        # `remember` and `correct` do. Withdrawal paths deliberately do not (Review 56 B6).
        if modules is None or not can_ingest(modules, memory.module):
            raise AptuniError("module_ingest_disabled",
                              f"Module '{memory.module}' is not accepting new information.")
        epoch = modules.epoch
        try:
            corrected = memory.model_copy(update={
                "id": new_id("mem"), "recorded_at": utc_now(), "statement": statement,
                "supersedes": (memory_id,), "change_kind": "correction", "policy_epoch": epoch,
            })
        except (ValidationError, ValueError) as error:
            raise AptuniError("invalid_memory", "That correction is not a valid memory.") from error
        digest = sha256_text(f"review|edit|{memory_id}|{epoch}|{statement}")

        def accepted(target: str) -> ReviewEvent:
            return ReviewEvent(
                record_type="review_event", id=new_id("rev"), schema_version=1, recorded_at=utc_now(),
                target_id=target, decision="accept", actor="user_cli", action_digest=digest,
                policy_epoch=epoch, rationale_code="owner_edit", nonce_id=f"review-{target}",
            )

        # Both the original and the replacement are settled: the owner wrote this statement, so the
        # correction must not inherit the original's pending state through their shared candidate.
        self._commit([corrected, accepted(memory_id), accepted(str(corrected.id))], seq)
        return str(corrected.id)

    @staticmethod
    def _reviewable(records: RecordSet, memory_id: str) -> Any:
        memory = next((r for r in records.records()
                       if r.record_type == "memory" and r.id == memory_id), None)
        if memory is None:
            raise AptuniError("memory_not_current", f"No memory with id {memory_id}.")
        if records.superseded_by(memory_id) is not None:
            # Without this the second edit reaches the supersession invariant, which answers with
            # an internal message and a record id (Review 56 N3).
            raise AptuniError("memory_not_current",
                              "That memory has already been replaced by a correction.")
        return memory

    # ---------------------------------------------------------------- the reminder
    def review_reminder(self, now: datetime | None = None,
                        waiting_since: datetime | None = None) -> ReviewReminder:
        """Whether the queue is worth mentioning. Reading this never changes anything.

        A snooze is checked first, because deferring a reminder means deferring it whatever
        triggered it — otherwise a queue that keeps growing would nag straight through the snooze
        the owner just asked for. Otherwise the threshold fires, and failing that the interval,
        which measures how long the *oldest pending memory* has been waiting rather than how long
        since some last notification: there is nothing to remind about before anything is pending.
        """
        return self._review_reminder_for(
            self.review_pending(), self.review_policy(), now=now, waiting_since=waiting_since,
        )

    def _review_reminder_for(
        self,
        waiting: Sequence[Any],
        policy: ReviewPolicy,
        *,
        now: datetime | None = None,
        waiting_since: datetime | None = None,
    ) -> ReviewReminder:
        """Apply the reminder policy to an already permission-filtered pending set.

        Owner reads pass the complete set. MCP reads pass only records visible to that principal,
        so neither the count nor the due state leaks a hidden module through reminder metadata.
        """
        now = now or utc_now()
        suppressed = self._suppressed_until()
        oldest = waiting_since or min((m.recorded_at for m in waiting), default=None)
        interval_due = oldest + timedelta(days=policy.interval_days) if oldest else None
        if not waiting:
            return ReviewReminder(0, False, "nothing_pending", policy.pending_threshold, None)
        if suppressed is not None and now < suppressed:
            return ReviewReminder(len(waiting), False, "snoozed", policy.pending_threshold, suppressed)
        if len(waiting) >= policy.pending_threshold:
            return ReviewReminder(len(waiting), True, "threshold", policy.pending_threshold, interval_due)
        if interval_due is not None and now >= interval_due:
            return ReviewReminder(len(waiting), True, "interval", policy.pending_threshold, interval_due)
        return ReviewReminder(len(waiting), False, "waiting", policy.pending_threshold, interval_due)

    def snooze_review(self, now: datetime | None = None) -> datetime:
        """Defer the reminder. Cadence is not canonical truth, so it lives in the state directory.

        Losing the state directory therefore loses a snooze, and the owner is reminded again. That
        is the harmless direction: a reminder is a line of text, never a blocking prompt.
        """
        until = (now or utc_now()) + timedelta(days=self.review_policy().snooze_days)
        self._write_reminder_marker(until)
        return until

    def clear_review_snooze(self) -> bool:
        """Undo a snooze. A marker is disposable state, so this must not need the Vault."""
        path = self._reminder_path
        if path.is_symlink() or not path.exists():
            return False
        path.unlink()
        return True

    @property
    def _reminder_path(self) -> Path:
        return self.workspace.state_dir / "review" / "reminder.json"

    def _suppressed_until(self) -> datetime | None:
        path = self._reminder_path
        if path.is_symlink() or not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            parsed = datetime.fromisoformat(str(value["suppressed_until"]))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            # An unreadable marker means "remind me", which is the harmless direction.
            return None
        # A naive timestamp parses cleanly and then raises on comparison, so it counts as
        # unreadable rather than reaching the caller (Review 56 B3).
        return parsed if parsed.tzinfo is not None else None

    def _write_reminder_marker(self, when: datetime) -> None:
        path = self._reminder_path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path.parent, 0o700)  # an existing directory keeps its old mode (Review 56 N12)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"suppressed_until": when.isoformat()}) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

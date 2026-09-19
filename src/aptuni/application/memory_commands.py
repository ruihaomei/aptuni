"""Interaction memory lifecycle: observe → quarantined candidate → terminal review → memory (ADR-0011).

Agents may *propose* (MCP scope ``memory.propose``); only the owner's terminal review can accept.
A decision binds an action digest over candidate, statement, module and policy epoch, so a stale or
changed preview is denied. ``forget`` appends a revocation and never deletes history. Raw
conversation context is not intentionally retained; only the bounded proposed statement is stored.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from aptuni.application.errors import AptuniError
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id
from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import (
    CandidateMemory,
    Memory,
    ModulePolicy,
    Observation,
    Provenance,
    RetentionLabel,
    ReviewEvent,
)
from aptuni.domain.temporal import utc_now
from aptuni.policy.modules import can_ingest

MEMORY_RETENTION = RetentionLabel(retention_class="canonical", purpose="interaction_memory", expires_at=None,
                                  full_content=False)
MAX_PENDING_PER_ORIGIN = 200
CONFIRMATION_TTL_SECONDS = 600
Origin = Literal["cli", "host"]
Decision = Literal["accept", "reject"]

_HOST_PROTECTED_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk|ghp|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b", re.IGNORECASE),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:password|passwd|api[ _-]?key|secret|token)\s*[:=]\s*\S{4,}", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:system|assistant|user)\s*:", re.IGNORECASE),
    re.compile(r"\b(?:ignore (?:all )?(?:previous|prior) instructions|system prompt|developer message)\b",
               re.IGNORECASE),
)


@dataclass(frozen=True)
class Proposal:
    candidate_id: str
    created: bool


@dataclass(frozen=True)
class MemoryPreview:
    candidate_id: str
    statement: str
    module: str
    trust: str
    episode: str | None
    policy_epoch: int
    nonce_id: str | None = None
    expires_at: datetime | None = None

    def digest(self, decision: Decision) -> str:
        if self.nonce_id is None or self.expires_at is None:
            raise ValueError("this summary is not an actionable confirmation preview")
        body = "\n".join(["memory_decision", decision, self.candidate_id, self.module,
                          str(self.policy_epoch), self.statement, self.nonce_id, self.expires_at.isoformat()])
        return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ForgetPreview:
    memory_id: str
    statement: str
    module: str
    trust: str
    episode: str | None
    policy_epoch: int
    nonce_id: str
    expires_at: datetime

    def digest(self) -> str:
        body = "\n".join(["memory_forget", self.memory_id, self.module, str(self.policy_epoch), self.statement,
                          self.nonce_id, self.expires_at.isoformat()])
        return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


class MemoryCommands:
    """Mixed into ``AptuniService``; relies on its snapshot/commit helpers."""

    workspace: Workspace

    def snapshot(self) -> tuple[int, RecordSet]:
        raise NotImplementedError

    def records(self) -> RecordSet:
        raise NotImplementedError

    @staticmethod
    def policy_of(records: RecordSet) -> ModulePolicy:
        raise NotImplementedError

    @staticmethod
    def _check_module(module: str) -> None:
        raise NotImplementedError

    def _commit(self, records: list[Any], expected_seq: int) -> None:
        raise NotImplementedError

    # ---------------------------------------------------------------- propose
    def observe(self, statement: str, module: str, *, origin: Origin = "cli", principal: str | None = None,
                about: str = "self", idempotency_key: str | None = None) -> Proposal:
        """Record an observation and a quarantined candidate memory; nothing becomes visible yet."""
        self._check_module(module)
        statement = " ".join(statement.split())
        if not 1 <= len(statement) <= 280:
            raise AptuniError("invalid_observation", "An observation is 1-280 characters.")
        episode = "cli" if origin == "cli" else f"mcp:{principal or 'unknown'}"
        normalized_about = about[:80] or "self"
        if origin == "host" and any(pattern.search(statement) for pattern in _HOST_PROTECTED_PATTERNS):
            raise AptuniError("memory_proposal_rejected", "The proposal matched protected content and was not stored.")
        caller_key = idempotency_key or hashlib.sha256(
            f"{module}|{normalized_about}|{statement}".encode()
        ).hexdigest()
        key = hashlib.sha256(f"{episode}|{caller_key}".encode()).hexdigest()
        seq, records = self.snapshot()
        policy = self.policy_of(records)
        if not can_ingest(policy, module):
            raise AptuniError("module_ingest_disabled", f"Module '{module}' is not accepting new information.")
        existing = self._candidate_for_key(records, key, module, normalized_about, statement)
        if existing is not None:
            return Proposal(existing, created=False)
        if origin == "host" and len(self._pending(records, episode)) >= MAX_PENDING_PER_ORIGIN:
            raise AptuniError("memory_queue_full", "Too many proposals await review; review them first.")
        trust = "user_declared" if origin == "cli" else "host_proposal"
        now = utc_now()
        common: dict[str, Any] = {
            "schema_version": 1, "recorded_at": now, "valid_from": None, "valid_until": None, "module": module,
            "provenance": Provenance(source_id=None, episode=episode, locator=None), "trust": trust,
            "retention": MEMORY_RETENTION, "policy_epoch": policy.epoch, "confidence": None,
            "review_status": "quarantined", "supersedes": (), "change_kind": "assert",
        }
        try:
            observation = Observation(record_type="observation", id=new_id("obs"), idempotency_key=key,
                                      about=normalized_about, value="observed", polarity="support",
                                      statement=statement, **common)
            candidate = CandidateMemory(record_type="candidate_memory", id=new_id("cnd"),
                                        derived_from=(observation.id,), contradicts=(), statement=statement,
                                        **common)
        except (ValidationError, ValueError) as error:
            raise AptuniError("invalid_observation", "The observation is not valid.") from error
        try:
            self._commit([observation, candidate], seq)
        except AptuniError as error:
            if error.code != "concurrent_write":
                raise
            _, current = self.snapshot()
            winner = self._candidate_for_key(current, key, module, normalized_about, statement)
            if winner is None:
                raise
            return Proposal(winner, created=False)
        return Proposal(candidate.id, created=True)

    def propose_from_host(self, statement: str, module: str, access: Any, idempotency_key: str | None = None
                          ) -> Proposal:
        """MCP entry: needs the ``memory.propose`` scope and module access; releases no personal data."""
        if access is None or not access.principal or "memory.propose" not in access.scopes:
            raise AptuniError("mcp_scope_denied", "The configured MCP principal lacks the required scope.")
        if module not in access.modules:
            raise AptuniError("mcp_module_denied", "The configured MCP principal lacks module access.")
        return self.observe(statement, module, origin="host", principal=access.principal,
                            idempotency_key=idempotency_key)

    # ---------------------------------------------------------------- review
    def pending_memories(self) -> list[MemoryPreview]:
        _, records = self.snapshot()
        epoch = self.policy_of(records).epoch
        return [self._preview(c, epoch) for c in self._pending(records, None)]

    def memory_preview(self, candidate_id: str) -> MemoryPreview:
        _, records = self.snapshot()
        candidate = self._undecided(records, candidate_id)
        epoch = self.policy_of(records).epoch
        nonce_id, expires_at = self._confirmation("candidate", candidate_id, epoch)
        return self._preview(candidate, epoch, nonce_id, expires_at)

    def decide_memory(self, candidate_id: str, decision: Decision, confirmed_digest: str) -> str | None:
        """Apply a terminal-confirmed decision; returns the new Memory id on accept."""
        seq, records = self.snapshot()
        candidate = self._undecided(records, candidate_id)
        policy = self.policy_of(records)
        nonce_id, expires_at = self._load_confirmation("candidate", candidate_id, policy.epoch)
        preview = self._preview(candidate, policy.epoch, nonce_id, expires_at)
        if confirmed_digest != preview.digest(decision):
            raise AptuniError("confirmation_stale", "The preview changed; review it again.")
        if decision == "accept" and not can_ingest(policy, candidate.module):
            message = f"Module '{candidate.module}' is not accepting new information."
            raise AptuniError("module_ingest_disabled", message)
        event = self._event(candidate_id, decision, confirmed_digest, policy.epoch, nonce_id)
        written: list[Any] = [event]
        memory_id = None
        if decision == "accept":
            memory = Memory(
                record_type="memory", id=new_id("mem"), schema_version=1, recorded_at=utc_now(),
                valid_from=None, valid_until=None, module=candidate.module, provenance=candidate.provenance,
                trust=candidate.trust, retention=MEMORY_RETENTION, policy_epoch=policy.epoch, confidence=None,
                review_status="accepted", supersedes=(), change_kind="assert", candidate_id=candidate_id,
                evidence_ids=(), statement=candidate.statement,
            )
            written.append(memory)
            memory_id = memory.id
        self._commit(written, seq)
        self._clear_confirmation("candidate", candidate_id)
        return memory_id

    def memory_forget_preview(self, memory_id: str) -> ForgetPreview:
        _, records = self.snapshot()
        memory = self._current_memory(records, memory_id)
        epoch = self.policy_of(records).epoch
        nonce_id, expires_at = self._confirmation("memory", memory_id, epoch)
        return ForgetPreview(memory.id, memory.statement, memory.module, memory.trust, memory.provenance.episode,
                             epoch, nonce_id, expires_at)

    def forget_memory_confirmed(self, memory_id: str, confirmed_digest: str) -> None:
        """Revoke an accepted memory after an exact terminal preview; history stays (ADR-0011)."""
        seq, records = self.snapshot()
        memory = next((r for r in records.records() if r.id == memory_id and r.record_type == "memory"), None)
        if memory is None:
            raise AptuniError("memory_not_found", f"No memory with id {memory_id}.")
        prior = next((r for r in records.records() if r.record_type == "review_event" and r.target_id == memory_id
                      and r.decision == "revoke"), None)
        if prior is not None:
            if prior.action_digest == confirmed_digest:
                return
            raise AptuniError("memory_not_current", "That memory is no longer current.")
        policy = self.policy_of(records)
        nonce_id, expires_at = self._load_confirmation("memory", memory_id, policy.epoch)
        preview = ForgetPreview(memory.id, memory.statement, memory.module, memory.trust, memory.provenance.episode,
                                policy.epoch, nonce_id, expires_at)
        if confirmed_digest != preview.digest():
            raise AptuniError("confirmation_stale", "The preview changed; review it again.")
        self._commit([self._event(memory_id, "revoke", confirmed_digest, policy.epoch, nonce_id)], seq)
        self._clear_confirmation("memory", memory_id)

    def memories(self) -> list[Any]:
        records = self.records()
        revoked = self._decided(records)
        return [r for r in records.records() if r.record_type == "memory" and r.id not in revoked]

    def cancel_memory_confirmation(self, kind: Literal["candidate", "memory"], target_id: str) -> None:
        """Invalidate an explicitly cancelled owner confirmation preview."""
        self._clear_confirmation(kind, target_id)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _decided(records: RecordSet) -> set[str]:
        return {r.target_id for r in records.records() if r.record_type == "review_event"}

    def _pending(self, records: RecordSet, episode: str | None) -> list[Any]:
        decided = self._decided(records)
        return [r for r in records.records() if r.record_type == "candidate_memory" and r.id not in decided
                and (episode is None or r.provenance.episode == episode)]

    def _undecided(self, records: RecordSet, candidate_id: str) -> Any:
        for candidate in self._pending(records, None):
            if candidate.id == candidate_id:
                return candidate
        raise AptuniError("candidate_not_pending", f"No pending candidate memory with id {candidate_id}.")

    @staticmethod
    def _candidate_for_key(records: RecordSet, key: str, module: str, about: str, statement: str) -> str | None:
        observation = next((r for r in records.records()
                            if r.record_type == "observation" and r.idempotency_key == key), None)
        if observation is None:
            return None
        if (observation.module, observation.about, observation.statement) != (module, about, statement):
            raise AptuniError("idempotency_conflict", "The idempotency key was already used for another proposal.")
        return next((r.id for r in records.records()
                     if r.record_type == "candidate_memory" and observation.id in r.derived_from), None)

    @staticmethod
    def _preview(candidate: Any, epoch: int, nonce_id: str | None = None,
                 expires_at: datetime | None = None) -> MemoryPreview:
        return MemoryPreview(candidate.id, candidate.statement, candidate.module, candidate.trust,
                             candidate.provenance.episode, epoch, nonce_id, expires_at)

    @staticmethod
    def _event(target: str, decision: Literal["accept", "reject", "revoke"], digest: str, epoch: int,
               nonce_id: str) -> ReviewEvent:
        return ReviewEvent(record_type="review_event", id=new_id("rev"), schema_version=1, recorded_at=utc_now(),
                           target_id=target, decision=decision, actor="user_cli",
                           action_digest=digest, policy_epoch=epoch, rationale_code=f"owner_{decision}",
                           nonce_id=nonce_id)

    def _current_memory(self, records: RecordSet, memory_id: str) -> Any:
        decided = self._decided(records)
        current = next((memory for memory in records.records()
                        if memory.record_type == "memory" and memory.id == memory_id
                        and memory.id not in decided), None)
        if current is None:
            raise AptuniError("memory_not_current", f"No current memory with id {memory_id}.")
        return current

    @property
    def _confirmation_root(self) -> Path:
        return self.workspace.state_dir / "memory-confirmations"

    def _confirmation_path(self, kind: str, target_id: str) -> Path:
        return self._confirmation_root / f"{kind}-{target_id}.json"

    def _confirmation(self, kind: str, target_id: str, epoch: int) -> tuple[str, datetime]:
        try:
            return self._load_confirmation(kind, target_id, epoch)
        except AptuniError as error:
            if error.code not in {"confirmation_missing", "confirmation_expired", "confirmation_stale",
                                  "confirmation_invalid"}:
                raise
        now = utc_now()
        value = {
            "version": 1,
            "kind": kind,
            "target_id": target_id,
            "policy_epoch": epoch,
            "nonce_id": secrets.token_hex(16),
            "expires_at": (now + timedelta(seconds=CONFIRMATION_TTL_SECONDS)).isoformat(),
        }
        path = self._confirmation_path(kind, target_id)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.parent.chmod(0o700)
        temporary = path.with_suffix(f".json.{os.getpid()}.{secrets.token_hex(4)}.tmp")
        temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, path)
        return str(value["nonce_id"]), datetime.fromisoformat(str(value["expires_at"]))

    def _load_confirmation(self, kind: str, target_id: str, epoch: int) -> tuple[str, datetime]:
        try:
            value = json.loads(self._confirmation_path(kind, target_id).read_text(encoding="utf-8"))
            if (value["version"], value["kind"], value["target_id"]) != (1, kind, target_id):
                raise ValueError
            nonce_id = str(value["nonce_id"])
            expires_at = datetime.fromisoformat(value["expires_at"])
            stored_epoch = value["policy_epoch"]
            if expires_at.tzinfo is None or type(stored_epoch) is not int:
                raise ValueError
        except FileNotFoundError as error:
            raise AptuniError("confirmation_missing", "Review the current preview before confirming.") from error
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            message = "The pending confirmation is invalid; review it again."
            raise AptuniError("confirmation_invalid", message) from error
        if utc_now() >= expires_at:
            raise AptuniError("confirmation_expired", "The confirmation expired; review the current preview again.")
        if stored_epoch != epoch:
            raise AptuniError("confirmation_stale", "The policy changed; review the current preview again.")
        if not re.fullmatch(r"[0-9a-f]{32}", nonce_id):
            raise AptuniError("confirmation_invalid", "The pending confirmation is invalid; review it again.")
        return nonce_id, expires_at

    def _clear_confirmation(self, kind: str, target_id: str) -> None:
        with suppress(OSError):
            self._confirmation_path(kind, target_id).unlink()
        # The canonical ReviewEvent is the authoritative single-use consumption record.

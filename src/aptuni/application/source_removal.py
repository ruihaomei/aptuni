"""Remove an approved source: one owner revoke plus a retraction of everything it contributed (ADR-0027).

History stays in the Vault; ADR-0010 purge remains the way to delete it. The preview is bound to the
exact current evidence ids, so a sync that lands between preview and APPLY makes it stale instead of
leaving new, unretracted evidence behind.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from aptuni.application.confirmations import new_nonce
from aptuni.application.errors import AptuniError
from aptuni.application.ingest import SourceSyncLock, source_has_committed_purge
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import deterministic_id, new_id, sha256_text
from aptuni.domain.invariants import SOURCE_REMOVED, RecordSet
from aptuni.domain.records import Evidence, ModulePolicy, ReviewEvent, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.vault.locks import source_operations_lock

__all__ = ["SourceRemoval", "SourceRemovalPreview"]


@dataclass(frozen=True)
class SourceRemovalPreview:
    source: SourceConfig
    evidence_ids: tuple[str, ...]
    digest: str
    #: The source is already removed, but an older build synced it again (Review 80 B2): applying
    #: writes only the missing retractions, never a second removal event.
    repair: bool = False


class SourceRemoval:
    """Mixin for ``AptuniService``; the host class provides the Vault primitives."""

    workspace: Workspace

    def vault(self) -> Any:
        raise NotImplementedError

    def snapshot(self) -> tuple[int, RecordSet]:
        raise NotImplementedError

    @staticmethod
    def policy_of(records: RecordSet) -> ModulePolicy:
        raise NotImplementedError

    def _commit(self, records: list[Any], expected_seq: int) -> None:
        raise NotImplementedError

    def source_removal_preview(self, source_id: str) -> SourceRemovalPreview:
        """Say exactly what removing this source would withdraw; writes nothing."""
        return _preview(self.snapshot()[1], source_id)

    def remove_source(self, source_id: str, digest: str) -> int:
        """Apply a previewed removal; return how many evidence items were retracted."""
        self.vault()
        with source_operations_lock(self.workspace.state_dir), SourceSyncLock(self.workspace.state_dir, source_id):
            if source_has_committed_purge(self.workspace.state_dir, source_id):
                raise AptuniError("privacy_action_in_progress", "A committed privacy purge owns this source.")
            seq, records = self.snapshot()
            preview = _preview(records, source_id)
            if preview.digest != digest:
                raise AptuniError("confirmation_stale", "The source changed since the preview; nothing was removed.")
            if preview.repair:
                retractions = [_retraction(records.get(item), preview.digest) for item in preview.evidence_ids]
                self._commit(retractions, seq)
                return len(retractions)
            now = utc_now()
            event = ReviewEvent(
                record_type="review_event", id=new_id("rev"), schema_version=1, recorded_at=now,
                target_id=source_id, decision="revoke", actor="user_cli", action_digest=digest,
                policy_epoch=self.policy_of(records).epoch, rationale_code=SOURCE_REMOVED, nonce_id=new_nonce(),
            )
            retractions = [_retraction(records.get(evidence_id), event.id) for evidence_id in preview.evidence_ids]
            self._commit([event, *retractions], seq)
            return len(retractions)


def _preview(records: RecordSet, source_id: str) -> SourceRemovalPreview:
    try:
        source = records.get(source_id)
    except KeyError as error:
        raise AptuniError("source_not_found", f"No source with id {source_id}.") from error
    if source.record_type != "source_config":
        raise AptuniError("source_not_found", f"No source with id {source_id}.")
    evidence_ids = tuple(sorted(item.id for item in records.current_evidence(source_id)
                                if item.change_kind != "retraction"))
    repair = source_id in records.removed_source_ids()
    if repair and not evidence_ids:
        raise AptuniError("source_removed", "This source was already removed.")
    action = "source_remove_repair" if repair else "source_remove"
    digest = sha256_text(json.dumps({"action": action, "source_id": source_id, "evidence": evidence_ids},
                                    sort_keys=True, separators=(",", ":")))
    return SourceRemovalPreview(source, evidence_ids, digest, repair)


def _retraction(previous: Evidence, seed: str) -> Evidence:
    """Withdraw one evidence item exactly as a sync retraction does, keeping its history."""
    return Evidence.model_validate({
        **previous.model_dump(),
        "id": deterministic_id("evd", f"remove:{seed}:{previous.id}"),
        "recorded_at": utc_now(), "supersedes": (previous.id,), "change_kind": "retraction",
        "signals": (), "observed_at": utc_now(),
    })

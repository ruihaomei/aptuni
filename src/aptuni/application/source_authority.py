"""Upgrade an approved source's authority after an explicit owner confirmation (ADR-0028 amendment).

Review 82 B4: a MarginNote source approved before ADR-0028 has empty authority, so its Evidence is
exposure-only and forms no Profile. One Vault commit applies the owner's confirmed upgrade: a
schema-v3 owner review event records the grant, every current Evidence item is re-derived as a
correction carrying the granted signal (the earlier item stays as history; the source keeps its id
and sync state), and the Profile Facts are formed in the same commit. Declining writes nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from aptuni.application.confirmations import new_nonce
from aptuni.application.errors import AptuniError
from aptuni.application.ingest import SourceSyncLock, source_has_committed_purge
from aptuni.application.workspace import Workspace
from aptuni.domain.evidence_profile import AUTHORITY_GRANT_SOURCE_TYPES
from aptuni.domain.ids import deterministic_id, new_id, sha256_text
from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import AUTHORITY_GRANTS, Evidence, ModulePolicy, ReviewEvent, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.policy.evidence_profile import derive_evidence_profile
from aptuni.policy.modules import can_ingest
from aptuni.vault.locks import source_operations_lock

__all__ = ["SourceAuthority", "SourceAuthorityPreview", "SourceAuthorityResult"]


@dataclass(frozen=True)
class SourceAuthorityPreview:
    source: SourceConfig
    dimension: str
    evidence_ids: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class SourceAuthorityResult:
    source_id: str
    dimension: str
    evidence_written: int
    profile_written: int


class SourceAuthority:
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

    def source_authority_preview(self, source_id: str, dimension: str) -> SourceAuthorityPreview:
        """Say exactly which Evidence the upgrade would re-derive; writes nothing."""
        records = self.snapshot()[1]
        return _preview(records, self.policy_of(records), source_id, dimension)

    def grant_source_authority(self, source_id: str, dimension: str, digest: str) -> SourceAuthorityResult:
        """Apply a previewed upgrade in one commit; a changed source makes the preview stale."""
        self.vault()
        with source_operations_lock(self.workspace.state_dir), SourceSyncLock(self.workspace.state_dir, source_id):
            if source_has_committed_purge(self.workspace.state_dir, source_id):
                raise AptuniError("privacy_action_in_progress", "A committed privacy purge owns this source.")
            seq, records = self.snapshot()
            policy = self.policy_of(records)
            preview = _preview(records, policy, source_id, dimension)
            if preview.digest != digest:
                raise AptuniError("confirmation_stale", "The source changed since the preview; nothing was granted.")
            event = ReviewEvent(
                record_type="review_event", id=new_id("rev"), schema_version=3, recorded_at=utc_now(),
                target_id=source_id, decision="accept", actor="user_cli", action_digest=digest,
                policy_epoch=policy.epoch, rationale_code=_rationale(preview.source, dimension),
                nonce_id=new_nonce(),
            )
            signal = dimension.split(".", 1)[1]
            corrections = [_rederived(records.get(item), event.id, signal) for item in preview.evidence_ids]
            visible = RecordSet([*records.records(), event])
            profile = derive_evidence_profile(
                corrections, visible, {source_id: preview.source},
                purged=frozenset(self.vault().ledger_digests()),
            )
            self._commit([event, *corrections, *profile], seq)
            written = sum(record.record_type == "fact" for record in profile)
            return SourceAuthorityResult(source_id, dimension, len(corrections), written)


def _rationale(source: SourceConfig, dimension: str) -> str:
    for code, granted in AUTHORITY_GRANTS.items():
        if granted == dimension and AUTHORITY_GRANT_SOURCE_TYPES[code] == source.source_type:
            return code
    raise AptuniError(
        "source_authority_unsupported",
        f"This source type cannot be granted {dimension}; only MarginNote study notes can count as studied.",
    )


def _preview(records: RecordSet, policy: ModulePolicy, source_id: str, dimension: str) -> SourceAuthorityPreview:
    try:
        source = records.get(source_id)
    except KeyError as error:
        raise AptuniError("source_not_found", f"No source with id {source_id}.") from error
    if source.record_type != "source_config":
        raise AptuniError("source_not_found", f"No source with id {source_id}.")
    if source_id in records.removed_source_ids():
        raise AptuniError("source_removed", "This source was removed; approve it again to use it.")
    _rationale(source, dimension)
    module, signal = dimension.split(".", 1)
    if module not in source.module_mapping[:1]:
        raise AptuniError("source_authority_unsupported", f"This source is not read into the {module} module.")
    if dimension in records.effective_source(source).authority.primary_for:
        raise AptuniError("source_authority_present", f"This source already counts for {dimension}.")
    if not can_ingest(policy, module):
        raise AptuniError("module_ingest_disabled", f"Module '{module}' is not accepting new information.")
    evidence_ids = tuple(sorted(
        item.id for item in records.current_evidence(source_id)
        if item.change_kind != "retraction" and item.module == module and signal not in item.signals
    ))
    digest = sha256_text(json.dumps(
        {"action": "source_authority_grant", "source_id": source_id, "dimension": dimension,
         "evidence": evidence_ids},
        sort_keys=True, separators=(",", ":"),
    ))
    return SourceAuthorityPreview(source, dimension, evidence_ids, digest)


def _rederived(previous: Evidence, seed: str, signal: str) -> Evidence:
    """The same observation, re-read under the granted authority; the earlier item stays as history."""
    signals = tuple(item for item in previous.signals if item != "exposure")
    return Evidence.model_validate({
        **previous.model_dump(),
        "id": deterministic_id("evd", f"authority:{seed}:{previous.id}"),
        "recorded_at": utc_now(), "supersedes": (previous.id,), "change_kind": "correction",
        "signals": signals if signal in signals else (*signals, signal),
    })

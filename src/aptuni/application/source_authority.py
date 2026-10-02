"""Owner-confirmed source authority and re-classification (ADR-0028 amendment, ADR-0029 items 5–6).

Authority is a ceiling (ADR-0029). ``grant`` raises it: one Vault commit records a schema-v3 owner
review event and re-derives, through the item classifier, only the current Evidence whose signal
changes under the new ceiling. ``reclassify`` applies the current classifier to Evidence written by
an older one (the owner-confirmed migration of ADR-0029 item 6). Each change is a ``correction`` of
the current version (history is kept; the source keeps its id and sync state); a downgrade leaves
the earlier derived Fact without current support, an upgrade forms a Fact in the same commit.
Declining writes nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from aptuni.application.confirmations import new_nonce
from aptuni.application.credential_guard import record_text, rederive_or_withhold
from aptuni.application.errors import AptuniError
from aptuni.application.ingest import SourceSyncLock, source_has_committed_purge
from aptuni.application.workspace import Workspace
from aptuni.domain.evidence_profile import AUTHORITY_GRANT_SOURCE_TYPES
from aptuni.domain.ids import deterministic_id, new_id, sha256_text
from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import AUTHORITY_GRANTS, Evidence, ModulePolicy, ReviewEvent, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.knowledge.classify import classified_signals
from aptuni.policy.evidence_profile import derive_evidence_profile
from aptuni.policy.modules import can_ingest
from aptuni.policy.secrets import contains_credential
from aptuni.vault.locks import source_operations_lock

__all__ = ["ReclassifyPreview", "SourceAuthority", "SourceAuthorityPreview", "SourceAuthorityResult"]

SEMANTIC = frozenset({"studied", "applied", "demonstrated"})


@dataclass(frozen=True)
class SourceAuthorityPreview:
    source: SourceConfig
    dimension: str
    evidence_ids: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class ReclassifyPreview:
    """The exact items the current classifier would change; ``upgrades`` gain a Profile signal."""

    source: SourceConfig
    changes: tuple[tuple[str, tuple[str, ...]], ...]  # (current Evidence id, new signals)
    upgrades: int
    downgrades: int
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
            corrections = _corrections(records, preview.changes, event.id)
            visible = RecordSet([*records.records(), event])
            profile = derive_evidence_profile(
                corrections, visible, {source_id: _with_authority(preview.source, preview.authority_after)},
                purged=frozenset(self.vault().ledger_digests()),
            )
            self._commit([event, *corrections, *profile], seq)
            written = sum(record.record_type == "fact" for record in profile)
            return SourceAuthorityResult(source_id, dimension, len(corrections), written)

    def source_reclassify_preview(self, source_id: str) -> ReclassifyPreview:
        """Say which current items the current classifier would change; writes nothing."""
        records = self.snapshot()[1]
        return _reclassify_preview(records, self.policy_of(records), source_id)

    def reclassify_source(self, source_id: str, digest: str) -> SourceAuthorityResult:
        """Apply a previewed re-classification in one commit; a changed source makes it stale."""
        self.vault()
        with source_operations_lock(self.workspace.state_dir), SourceSyncLock(self.workspace.state_dir, source_id):
            if source_has_committed_purge(self.workspace.state_dir, source_id):
                raise AptuniError("privacy_action_in_progress", "A committed privacy purge owns this source.")
            seq, records = self.snapshot()
            preview = _reclassify_preview(records, self.policy_of(records), source_id)
            if preview.digest != digest:
                raise AptuniError("confirmation_stale", "The source changed since the preview; nothing changed.")
            corrections = _corrections(records, preview.changes, f"reclassify:{digest}")
            profile = derive_evidence_profile(
                corrections, records, {source_id: preview.source}, purged=frozenset(self.vault().ledger_digests()),
            )
            if corrections:
                self._commit([*corrections, *profile], seq)
            written = sum(record.record_type == "fact" for record in profile)
            return SourceAuthorityResult(source_id, "", len(corrections), written)


def _rationale(source: SourceConfig, dimension: str) -> str:
    for code, granted in AUTHORITY_GRANTS.items():
        if granted == dimension and AUTHORITY_GRANT_SOURCE_TYPES[code] == source.source_type:
            return code
    raise AptuniError(
        "source_authority_unsupported",
        f"This source type cannot be granted {dimension}; only MarginNote study notes can count as studied.",
    )


def _usable_source(records: RecordSet, policy: ModulePolicy, source_id: str) -> SourceConfig:
    try:
        source = records.get(source_id)
    except KeyError as error:
        raise AptuniError("source_not_found", f"No source with id {source_id}.") from error
    if source.record_type != "source_config":
        raise AptuniError("source_not_found", f"No source with id {source_id}.")
    if source_id in records.removed_source_ids():
        raise AptuniError("source_removed", "This source was removed; approve it again to use it.")
    if not can_ingest(policy, source.module_mapping[0]):
        raise AptuniError("module_ingest_disabled",
                          f"Module '{source.module_mapping[0]}' is not accepting new information.")
    return records.effective_source(source)


def _with_authority(source: SourceConfig, authority: tuple[str, ...]) -> SourceConfig:
    return source.model_copy(update={"authority": source.authority.model_copy(update={"primary_for": authority})})


def _changes(records: RecordSet, source: SourceConfig,
             authority: tuple[str, ...]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Current Evidence whose classified signals under ``authority`` differ from what it carries.

    Credential-bearing Evidence is always a change: it is retracted, never re-derived (ADR-0031)."""
    changes: list[tuple[str, tuple[str, ...]]] = []
    for item in sorted(records.current_evidence(source.id), key=lambda e: e.id):
        if item.change_kind == "retraction":
            continue
        if contains_credential(record_text(item)):
            changes.append((item.id, ()))
            continue
        signals = classified_signals(item, source.source_type, authority)
        if signals != item.signals:
            changes.append((item.id, tuple(signals)))
    return tuple(changes)


def _digest(action: str, source_id: str, dimension: str, changes: object) -> str:
    return sha256_text(json.dumps(
        {"action": action, "source_id": source_id, "dimension": dimension, "evidence": changes},
        sort_keys=True, separators=(",", ":"),
    ))


@dataclass(frozen=True)
class _GrantPreview(SourceAuthorityPreview):
    authority_after: tuple[str, ...] = ()
    changes: tuple[tuple[str, tuple[str, ...]], ...] = ()


def _preview(records: RecordSet, policy: ModulePolicy, source_id: str, dimension: str) -> _GrantPreview:
    source = _usable_source(records, policy, source_id)
    _rationale(source, dimension)
    module = dimension.split(".", 1)[0]
    if module not in source.module_mapping[:1]:
        raise AptuniError("source_authority_unsupported", f"This source is not read into the {module} module.")
    if dimension in source.authority.primary_for:
        raise AptuniError("source_authority_present", f"This source already counts for {dimension}.")
    authority = tuple(sorted({*source.authority.primary_for, dimension}))
    changes = _changes(records, source, authority)
    evidence_ids = tuple(evidence_id for evidence_id, _ in changes)
    digest = _digest("source_authority_grant", source_id, dimension, evidence_ids)
    return _GrantPreview(source, dimension, evidence_ids, digest, authority, changes)


def _reclassify_preview(records: RecordSet, policy: ModulePolicy, source_id: str) -> ReclassifyPreview:
    source = _usable_source(records, policy, source_id)
    changes = _changes(records, source, source.authority.primary_for)
    upgrades = downgrades = 0
    for evidence_id, signals in changes:
        before = SEMANTIC & set(records.get(evidence_id).signals)
        after = SEMANTIC & set(signals)
        upgrades += bool(after - before)
        downgrades += bool(before - after)
    digest = _digest("source_reclassify", source_id, "", [[i, list(s)] for i, s in changes])
    return ReclassifyPreview(source, changes, upgrades, downgrades, digest)


def _corrections(records: RecordSet, changes: tuple[tuple[str, tuple[str, ...]], ...], seed: str) -> list[Evidence]:
    return [_rederived(records.get(evidence_id), seed, signals) for evidence_id, signals in changes]


def _rederived(previous: Evidence, seed: str, signals: tuple[str, ...]) -> Evidence:
    """The same observation, re-read under the current classifier and ceiling; the earlier item stays.

    An item holding a credential is retracted instead, never re-copied (ADR-0031)."""
    return rederive_or_withhold(previous, deterministic_id("evd", f"authority:{seed}:{previous.id}"), signals)

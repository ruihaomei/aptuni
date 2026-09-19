"""Source commands: approve a source, sync it into Evidence, inspect evidence and the review queue.

Mixed into ``AptuniService``. Like every command, a sync decides on one ``(seq, records)``
snapshot and commits with that ``expected_seq``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aptuni.application.errors import AptuniError
from aptuni.application.ingest import (
    FOLDER_PARSER,
    GITHUB_PARSER,
    FolderIngest,
    GitHubIngest,
    PendingSourceState,
    SourceChangedDuringSync,
    SourceState,
    SourceStateStore,
    SourceSyncLock,
    SyncReport,
    review_entries,
    review_operations,
    summarize,
)
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id
from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import AuthorityPolicy, ModulePolicy, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.policy.modules import can_ingest
from aptuni.sources.delivery import DeliveryError, DeliveryGuard
from aptuni.sources.github import GitHubApi, GitHubApiError, GitHubSourceSpec, SourceIdentityError
from aptuni.sources.records import Operation
from aptuni.vault.store import Vault


class SourceCommands:
    """Requires the host class to provide the lifecycle helpers declared below."""

    workspace: Workspace

    def vault(self) -> Vault:
        raise NotImplementedError

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

    # ---------------------------------------------------------------- configuration
    def add_folder_source(self, root: Path, modules: tuple[str, ...], role: str,
                          primary_for: tuple[str, ...] = ()) -> SourceConfig:
        """Approve a folder as a source. Discovery is not permission: only this root is read."""
        root = root.expanduser().resolve()
        if not root.is_dir():
            raise AptuniError("source_not_found", f"Not a folder: {root}")
        vault_root = self.vault().root.resolve()
        state_dir = self.workspace.state_dir.expanduser().resolve()
        for protected in (vault_root, state_dir):
            if root == protected or protected in root.parents or root in protected.parents:
                raise AptuniError("source_inside_vault", "A source folder must not overlap the Vault or its state.")
        if not modules:
            raise AptuniError("modules_required", "Choose at least one module for this source.")
        for module in modules:
            self._check_module(module)
        seq, _ = self.snapshot()
        try:
            config = SourceConfig(record_type="source_config", id=new_id("src"), schema_version=1,
                                  recorded_at=utc_now(), source_type="folder", roots=(str(root),),
                                  semantic_role=role, module_mapping=modules,
                                  authority=AuthorityPolicy(version=1, primary_for=primary_for))
        except (ValidationError, ValueError) as error:
            raise AptuniError("invalid_source", f"Invalid source configuration: {error}") from error
        self._commit([config], seq)
        return config

    def add_github_source(
        self,
        repository_url: str,
        modules: tuple[str, ...],
        role: str,
        *,
        ref: str | None = None,
        token_env: str | None = None,
        api_origin: str = "https://api.github.com",
        primary_for: tuple[str, ...] = (),
    ) -> SourceConfig:
        """Approve one exact GitHub repository; any credential remains an environment reference."""
        if not modules:
            raise AptuniError("modules_required", "Choose at least one module for this source.")
        for module in modules:
            self._check_module(module)
        try:
            spec = GitHubSourceSpec.build(repository_url, api_origin=api_origin, ref=ref, token_env=token_env)
            seq, _ = self.snapshot()
            config = SourceConfig(
                record_type="source_config", id=new_id("src"), schema_version=1, recorded_at=utc_now(),
                source_type="github", roots=spec.roots(), semantic_role=role, module_mapping=modules,
                authority=AuthorityPolicy(version=1, primary_for=primary_for),
            )
        except (SourceIdentityError, ValidationError, ValueError) as error:
            raise AptuniError("invalid_source", f"Invalid GitHub source configuration: {error}") from error
        self._commit([config], seq)
        return config

    def sources(self) -> list[SourceConfig]:
        return [r for r in self.records().records() if r.record_type == "source_config"]

    @staticmethod
    def _source_in(records: RecordSet, source_id: str) -> SourceConfig:
        for record in records.records():
            if record.record_type == "source_config" and record.id == source_id:
                return record  # type: ignore[no-any-return]
        raise AptuniError("source_not_found", f"No source with id {source_id}.")

    # ---------------------------------------------------------------- inspection
    def evidence(self, source_id: str | None = None) -> list[Any]:
        """Current evidence the owner can inspect (withdrawn items excluded)."""
        return [e for e in self.records().current_evidence(source_id) if e.change_kind != "retraction"]

    def review_queue(self, source_id: str) -> list[Operation]:
        config = self._source_in(self.records(), source_id)
        return review_operations(SourceStateStore(self.vault().root, config.id).load())

    # ---------------------------------------------------------------- sync
    def sync(self, source_id: str) -> SyncReport:
        with SourceSyncLock(self.workspace.state_dir, source_id):
            return self._sync_locked(source_id)

    def _sync_locked(self, source_id: str) -> SyncReport:
        seq, records = self.snapshot()
        config = self._source_in(records, source_id)
        policy = self.policy_of(records)
        module = config.module_mapping[0]
        if not can_ingest(policy, module):
            raise AptuniError("module_ingest_disabled", f"Module '{module}' is not accepting new information.")
        if config.source_type not in {"folder", "github"}:
            raise AptuniError("source_type_unsupported", f"Source type '{config.source_type}' is not runnable.")
        store = SourceStateStore(self.vault().root, config.id)
        state = store.load()
        state = self._recover_pending(store, state, records.ids())
        current = {e.provenance.locator.subject_id: e for e in records.current_evidence(config.id)}
        if config.source_type == "folder":
            ingest: FolderIngest | GitHubIngest = FolderIngest(
                config, module, policy.epoch, current, existing_ids=records.ids())
            parser = FOLDER_PARSER
            provider_data: dict[str, Any] = {}
        else:
            try:
                spec = GitHubSourceSpec.from_roots(config.roots)
            except SourceIdentityError as error:
                raise AptuniError("source_config_invalid", "The GitHub source configuration is invalid.") from error
            ingest = GitHubIngest(config, module, policy.epoch, current, records.ids(), self._github_client(spec))
            parser = GITHUB_PARSER
            provider_data = {}
        try:
            scan = ingest.scan(state)
            if config.source_type == "github":
                provider_data = {"repository_id": scan.repository_id}  # type: ignore[union-attr]
        except (GitHubApiError, SourceIdentityError) as error:
            raise AptuniError("github_sync_failed", f"GitHub sync stopped safely ({error}).") from error
        guard = state.delivery if state else DeliveryGuard()
        try:
            if guard.admit(scan.delta) == "duplicate":
                return SyncReport(config.id, {}, 0, scan.notes, 0)
            operations = guard.gate(scan.delta)
            evidence = [record for op in operations if op.review_state != "needs_review"
                        for record in [ingest.evidence_for(op, scan.delta.delta_id, scan.delta.sequence)] if record]
        except (DeliveryError, SourceChangedDuringSync, GitHubApiError) as error:
            raise AptuniError("sync_retry", f"The source changed while syncing; run sync again ({error}).") from error
        expected_ids = tuple(sorted(record.id for record in evidence)) if evidence else ()
        guard.record(scan.delta)
        review = [*(state.review if state else []), *review_entries(operations)]
        final_state = SourceState(
            scan.snapshot, parser, scan.delta.sequence, guard, review, scan.notes, provider_data
        )
        store.save_pending(PendingSourceState(final_state, scan.delta, expected_ids))
        if evidence:
            self._commit(evidence, seq)
        store.save(final_state)
        store.clear_pending()
        return SyncReport(config.id, summarize(operations), len(review_entries(operations)), scan.notes,
                          len(evidence))

    @staticmethod
    def _recover_pending(
        store: SourceStateStore,
        state: SourceState | None,
        existing_ids: set[str],
    ) -> SourceState | None:
        pending = store.load_pending()
        if pending is None:
            return state
        if state is not None and state.sequence >= pending.state.sequence:
            store.clear_pending()
            return state
        expected = set(pending.expected_evidence_ids)
        present = expected & existing_ids
        if present == expected:
            store.save(pending.state)
            store.clear_pending()
            return pending.state
        if present:
            raise AptuniError("source_recovery_failed", "A source sync has a partial canonical commit.")
        store.clear_pending()
        return state

    @staticmethod
    def _github_client(spec: GitHubSourceSpec) -> GitHubApi:
        return GitHubApi(spec)

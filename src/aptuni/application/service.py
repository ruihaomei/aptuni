"""Application service: the single entry point used by the CLI (and later MCP and the SDK).

Every command decides on one consistent ``(seq, records)`` snapshot and commits with that
``expected_seq``. A concurrent writer therefore turns a stale decision into ``concurrent_write``
instead of a lost update (review 16 F1). The owner sees all current facts; agent-facing views go
through ``exposable()`` and the module policy (fail closed).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import ValidationError

from aptuni.application.backup import BackupSummary, create_backup, list_backups, verify_backup
from aptuni.application.context import (
    MAX_BUDGET,
    MAX_QUERY_BYTES,
    MIN_BUDGET,
    Audience,
    ContextResponse,
    pack_units,
    record_unit,
    response_from,
    section,
    unit_cost,
)
from aptuni.application.errors import AptuniError
from aptuni.application.export import ExportReport, export_profile
from aptuni.application.memory_commands import MemoryCommands
from aptuni.application.privacy import (
    PrivacyInventory,
    PurgePreview,
    build_privacy_inventory,
    cancel_purge,
    committed_purge_intent,
    confirm_purge,
    create_purge_preview,
    load_purge_preview,
)
from aptuni.application.restore import (
    RestorePreview,
    RestoreReceipt,
    cancel_restore,
    confirm_restore,
    create_restore_preview,
    load_restore_preview,
    pending_restores,
)
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import (
    MODULES,
    DeletionReceipt,
    Fact,
    Module,
    ModulePolicy,
    Provenance,
    RetentionLabel,
    SchemaVersionError,
)
from aptuni.domain.temporal import utc_now
from aptuni.policy.modules import can_ingest, default_policy, with_switch
from aptuni.retrieval.sqlite import ProjectionError, ProjectionStatus, SearchRow, SqliteProjection, documents_for
from aptuni.vault.fsgate import UnsupportedFilesystemError
from aptuni.vault.store import ConflictError, Vault, VaultDirNotEmptyError, VaultIntegrityError, VerifyReport

CLI_EPISODE = "cli"
DECLARED_RETENTION = RetentionLabel(retention_class="canonical", purpose="user_declared_profile",
                                    expires_at=None, full_content=False)
UNREADABLE = (VaultIntegrityError, SchemaVersionError, UnsupportedFilesystemError, json.JSONDecodeError, KeyError)


@dataclass(frozen=True)
class Status:
    vault_path: Path
    state_dir: Path
    seq: int
    policy_epoch: int
    counts: dict[str, int]
    modules: dict[str, tuple[bool, bool]]  # module -> (ingest, expose)


@dataclass(frozen=True)
class SearchHit:
    id: str
    record_type: str
    module: str
    text: str
    score: float
    source_id: str | None


@dataclass(frozen=True)
class HostContextAccess:
    """Process-bound MCP authority created from trusted local adapter configuration."""

    principal: str
    scopes: frozenset[str]
    modules: frozenset[str]
    host_class: Literal["remote_unknown", "proven_local"]
    host_model_egress: bool


class AptuniService(SourceCommands, MemoryCommands):
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self._vault: Vault | None = None

    # ---------------------------------------------------------------- lifecycle
    def init(self, vault_path: Path) -> Status:
        vault_path = vault_path.expanduser().resolve()
        state = self.workspace.state_dir.expanduser().resolve()
        if state == vault_path or vault_path in state.parents:
            raise AptuniError("state_inside_vault", "The state directory must be outside the Vault.")
        if (vault_path / "HEAD.json").exists():
            raise AptuniError("vault_exists", f"A Vault already exists at {vault_path}.")
        try:
            vault = Vault.init(vault_path, state)
        except VaultDirNotEmptyError as error:
            raise AptuniError("vault_dir_not_empty",
                              f"{vault_path} is not empty. Choose a new or empty folder for your Vault.") from error
        except UnsupportedFilesystemError as error:
            raise AptuniError("unsupported_filesystem", str(error)) from error
        vault.commit([default_policy()], expected_seq=0)
        self.workspace.save(vault_path)
        self._vault = vault
        return self.status()

    def vault(self) -> Vault:
        if self._vault is None:
            try:
                path = self.workspace.vault_path()
            except UNREADABLE as error:
                raise AptuniError("config_unreadable", f"Aptuni config is unreadable: {error}") from error
            if path is None:
                raise AptuniError("not_initialized", "No Vault configured. Run `aptuni init` first.")
            try:
                self._vault = Vault.open(path, self.workspace.state_dir)
            except FileNotFoundError as error:
                raise AptuniError("vault_missing", f"The configured Vault is missing: {path}") from error
            except UNREADABLE as error:
                message = f"The Vault cannot be read ({error}). Run `aptuni doctor`."
                raise AptuniError("vault_unreadable", message) from error
        return self._vault

    def snapshot(self) -> tuple[int, RecordSet]:
        try:
            return self.vault().snapshot()
        except UNREADABLE as error:
            message = f"The Vault cannot be read ({error}). Run `aptuni doctor`."
            raise AptuniError("vault_unreadable", message) from error

    # ---------------------------------------------------------------- queries
    def records(self) -> RecordSet:
        return self.snapshot()[1]

    @staticmethod
    def policy_of(records: RecordSet) -> ModulePolicy:
        policy = records.policy()
        if policy is None:
            raise AptuniError("policy_missing", "The Vault has no module policy; run `aptuni doctor`.")
        return policy

    def status(self) -> Status:
        seq, records = self.snapshot()
        policy = records.policy()
        vault = self.vault()
        return Status(
            vault_path=vault.root, state_dir=vault.state_dir, seq=seq, policy_epoch=policy.epoch if policy else 0,
            counts=dict(Counter(r.record_type for r in records.records())),
            modules={m: (s.ingest_enabled, s.expose_enabled) for m, s in (policy.modules if policy else {}).items()},
        )

    def facts(self, module: str | None = None, as_known_at: datetime | None = None) -> list[Any]:
        """Current facts as the owner sees them (including modules hidden from agents)."""
        return [f for f in self.records().current_facts(as_known_at) if module is None or f.module == module]

    def exposable(self) -> list[Any]:
        """What an agent may see under the current policy (fail closed)."""
        return self.records().exposable()

    def history(self) -> list[Any]:
        return [r for r in self.records().records() if r.record_type == "fact"]

    def export(self, target: Path) -> ExportReport:
        """Write a private, readable current-Profile copy outside the canonical Vault."""
        vault_root = self.vault().root.resolve()
        destination = target.expanduser().resolve(strict=False)
        if destination == vault_root or vault_root in destination.parents:
            raise AptuniError("export_inside_vault", "Choose an export folder outside the canonical Vault.")
        seq, records = self.snapshot()
        try:
            return export_profile(records, seq, target)
        except FileExistsError as error:
            raise AptuniError(
                "export_target_not_empty", "The export destination must be absent or an empty directory."
            ) from error
        except OSError as error:
            message = "The Profile export could not be written; nothing was changed."
            raise AptuniError("export_failed", message) from error

    def privacy_inventory(self) -> PrivacyInventory:
        """Return owner-visible copy metadata only; never record content."""
        seq, records = self.snapshot()
        return build_privacy_inventory(self.vault().root, self.workspace.state_dir, seq, records)

    def privacy_purge_preview(self, record_ids: tuple[str, ...]) -> PurgePreview:
        """Create a single-use exact preview; no canonical or derived copy is changed."""
        seq, records = self.snapshot()
        return create_purge_preview(
            self.vault().root, self.workspace.state_dir, records, seq, self.policy_of(records).epoch, record_ids
        )

    def pending_privacy_purge(self, action_id: str) -> PurgePreview:
        """Load one exact pending preview for terminal confirmation."""
        return load_purge_preview(self.workspace.state_dir, action_id)

    def confirm_privacy_purge(self, action_id: str, confirmed_digest: str) -> DeletionReceipt:
        """Commit/resume the durable purge intent; reachable only from the owner CLI."""
        return confirm_purge(self.vault(), self.workspace.state_dir, action_id, confirmed_digest)

    def cancel_privacy_purge(self, action_id: str) -> None:
        """Release a committed intent that deleted nothing canonical (Review 31 F1)."""
        cancel_purge(self.vault(), self.workspace.state_dir, action_id)

    # ---------------------------------------------------------------- backup and restore
    def create_backup(self, destination: Path) -> BackupSummary:
        """Write a verified restorable copy of the canonical Vault; `export` is not one."""
        return create_backup(self.vault(), self.workspace.state_dir, destination)

    @staticmethod
    def verify_backup(path: Path) -> BackupSummary:
        """Check a backup without touching the live Vault."""
        return verify_backup(path)

    @staticmethod
    def list_backups(directory: Path) -> tuple[BackupSummary, ...]:
        return list_backups(directory)

    def restore_preview(self, path: Path) -> RestorePreview:
        """Verify the backup and record one single-use preview; nothing is replaced yet."""
        return create_restore_preview(self.vault(), self.workspace.state_dir, path)

    def pending_restore(self, action_id: str) -> RestorePreview:
        return load_restore_preview(self.workspace.state_dir, action_id)

    def pending_restores(self) -> tuple[RestorePreview, ...]:
        return pending_restores(self.workspace.state_dir)

    def confirm_restore(self, action_id: str, confirmed_digest: str) -> RestoreReceipt:
        """Publish the verified backup as the next generation; reachable only from the owner CLI."""
        return confirm_restore(self.vault(), self.workspace.state_dir, action_id, confirmed_digest)

    def cancel_restore(self, action_id: str) -> None:
        cancel_restore(self.workspace.state_dir, action_id)

    # ---------------------------------------------------------------- retrieval projection
    def index_status(self) -> ProjectionStatus:
        seq, _ = self.snapshot()
        try:
            return SqliteProjection(self.workspace.state_dir).status(seq)
        except OSError as error:
            raise AptuniError("projection_failed", "The search index status is unavailable.") from error

    def rebuild_index(self) -> ProjectionStatus:
        seq, records = self.snapshot()
        try:
            return SqliteProjection(self.workspace.state_dir).rebuild(documents_for(records.exposable()), seq)
        except (OSError, ProjectionError) as error:
            message = "The search index could not be rebuilt; canonical data is safe."
            raise AptuniError("projection_failed", message) from error

    def delete_index(self) -> None:
        try:
            SqliteProjection(self.workspace.state_dir).delete()
        except (OSError, ProjectionError) as error:
            raise AptuniError("projection_failed", "The derived search index could not be deleted.") from error

    def search(self, query: str, *, module: str | None = None, limit: int = 5) -> list[SearchHit]:
        if module is not None:
            self._check_module(module)
        if not query.strip() or type(limit) is not int or not 1 <= limit <= 100:
            raise AptuniError("invalid_search", "Search needs a query and a limit between 1 and 100.")
        seq, final_records, rows = self._stable_search(query, module=module, limit=limit)
        del seq
        allowed = {record.id: record for record in final_records.exposable()}
        hits = []
        for row in rows:
            record = allowed.get(row.record_id)
            if record is None or (module is not None and record.module != module):
                continue
            text = getattr(record, "statement", None) or getattr(record, "excerpt", None) or record.subject
            hits.append(SearchHit(record.id, record.record_type, record.module, str(text), row.score,
                                  record.provenance.source_id))
        return hits

    def _stable_search(
        self,
        query: str,
        *,
        module: str | None = None,
        modules: tuple[str, ...] | None = None,
        record_types: tuple[str, ...] | None = None,
        limit: int = 5,
    ) -> tuple[int, RecordSet, list[SearchRow]]:
        projection = SqliteProjection(self.workspace.state_dir)
        for _ in range(3):
            seq, records = self.snapshot()
            try:
                projection.ensure(documents_for(records.exposable()), seq)
                rows = projection.search(
                    query,
                    module=module,
                    modules=modules,
                    record_types=record_types,
                    limit=limit,
                )
            except (OSError, ProjectionError, ValueError) as error:
                message = "The search index is unavailable; canonical data is safe."
                raise AptuniError("projection_failed", message) from error
            final_seq, final_records = self.snapshot()
            if final_seq != seq:
                continue
            allowed = {record.id: record for record in final_records.exposable()}
            filtered = [row for row in rows if row.record_id in allowed]
            return final_seq, final_records, filtered
        raise AptuniError("concurrent_write", "The Vault kept changing during search; run it again.")

    # ---------------------------------------------------------------- bounded context
    @staticmethod
    def _check_context_request(budget: int, audience: str, limit: int | None = None) -> None:
        if audience not in ("owner_cli", "host_mcp"):
            raise AptuniError("egress_not_authorized", "The requested context audience is not authorized.")
        if type(budget) is not int or not MIN_BUDGET <= budget <= MAX_BUDGET:
            raise AptuniError("invalid_context", f"Budget must be between {MIN_BUDGET} and {MAX_BUDGET} units.")
        if limit is not None and (type(limit) is not int or not 1 <= limit <= 100):
            raise AptuniError("invalid_context", "Context result limit must be between 1 and 100.")

    @staticmethod
    def _authorize_host(
        access: HostContextAccess | None,
        *,
        scope: str,
        modules: tuple[str, ...],
    ) -> None:
        if access is None or not access.principal or scope not in access.scopes:
            raise AptuniError("mcp_scope_denied", "The configured MCP principal lacks the required scope.")
        if not modules or not set(modules) <= access.modules:
            raise AptuniError("mcp_module_denied", "The configured MCP principal lacks module access.")
        if access.host_class != "proven_local" and not access.host_model_egress:
            raise AptuniError("host_model_egress_denied", "Host/model egress is not granted.")

    def identity_card(
        self,
        *,
        budget: int = 512,
        audience: str = "owner_cli",
        access: HostContextAccess | None = None,
    ) -> ContextResponse:
        self._check_context_request(budget, audience)
        if audience == "host_mcp":
            self._authorize_host(access, scope="identity.read", modules=("identity",))
        elif access is not None:
            raise AptuniError("invalid_context", "Host access is valid only for the host_mcp audience.")
        for _ in range(3):
            seq, records = self.snapshot()
            identity = sorted(
                (record for record in records.exposable()
                 if record.record_type == "fact" and record.module == "identity"
                 and record.trust == "user_declared"),
                key=lambda record: (record.recorded_at, record.id),
            )
            final_seq, final_records = self.snapshot()
            if final_seq != seq:
                continue
            allowed = {record.id for record in final_records.exposable()}
            identity = [record for record in identity if record.id in allowed]
            omitted = False
            while identity:
                card = section(
                    "L0",
                    "identity_card",
                    "\n".join(record.statement for record in identity),
                    canonical_ids=tuple(record.id for record in identity),
                )
                if 32 + unit_cost(card) <= budget:
                    packed = pack_units((card,), budget)
                    policy = self.policy_of(final_records)
                    response = response_from(packed, budget=budget, vault_seq=final_seq,
                                             policy_epoch=policy.epoch, more_results=omitted,
                                             audience=cast(Audience, audience))
                    if self.snapshot()[0] == final_seq:
                        return response
                    break
                identity.pop()
                omitted = True
            else:
                packed = pack_units((), budget)
                policy = self.policy_of(final_records)
                response = response_from(packed, budget=budget, vault_seq=final_seq,
                                         policy_epoch=policy.epoch, more_results=omitted,
                                         audience=cast(Audience, audience))
                if self.snapshot()[0] == final_seq:
                    return response
        raise AptuniError("concurrent_write", "The Vault kept changing during identity-card creation; run it again.")

    def context(
        self,
        query: str,
        *,
        modules: tuple[str, ...] = (),
        budget: int = 1500,
        include_evidence: bool = False,
        limit: int = 20,
        audience: str = "owner_cli",
        access: HostContextAccess | None = None,
    ) -> ContextResponse:
        self._check_context_request(budget, audience, limit)
        if not query.strip() or len(query.encode("utf-8")) > MAX_QUERY_BYTES:
            raise AptuniError(
                "invalid_context",
                f"Context query must be non-empty and at most {MAX_QUERY_BYTES} UTF-8 bytes.",
            )
        if type(include_evidence) is not bool:
            raise AptuniError("invalid_context", "include_evidence must be true or false.")
        for module_name in modules:
            self._check_module(module_name)
        selected = tuple(dict.fromkeys(cast(Module, module_name) for module_name in modules))
        if audience == "host_mcp":
            self._authorize_host(access, scope="context.read", modules=selected)
            if include_evidence:
                self._authorize_host(access, scope="evidence.read", modules=selected)
        elif access is not None:
            raise AptuniError("invalid_context", "Host access is valid only for the host_mcp audience.")
        record_types = ("fact", "memory", "evidence") if include_evidence else ("fact", "memory")
        for _ in range(3):
            seq, records, rows = self._stable_search(
                query,
                modules=selected or None,
                record_types=record_types,
                limit=limit + 1,
            )
            more = len(rows) > limit
            allowed = {record.id: record for record in records.exposable()}
            matched = [allowed[row.record_id] for row in rows[:limit] if row.record_id in allowed]
            policy = self.policy_of(records)
            visible_requested = tuple(name for name in selected if policy.modules[name].expose_enabled)
            selected_modules = visible_requested or tuple(dict.fromkeys(record.module for record in matched))
            counts = Counter(record.module for record in matched)
            index_text = "no matching permitted context" if not counts else "matches: " + ", ".join(
                f"{name}={counts[name]}" for name in sorted(counts)
            )
            modules_text = "selected modules: " + (", ".join(selected_modules) if selected_modules else "none")
            record_candidates = sorted(
                (record_unit(record) for record in matched),
                key=lambda item: 3 if item.layer == "L3" else 4,
            )
            candidates = (
                section("L1", "context_index", index_text),
                section("L2", "selected_modules", modules_text),
                *record_candidates,
            )
            packed = pack_units(candidates, budget)
            response = response_from(
                packed,
                budget=budget,
                vault_seq=seq,
                policy_epoch=policy.epoch,
                more_results=more,
                audience=cast(Audience, audience),
            )
            if self.snapshot()[0] == seq:
                return response
        raise AptuniError("concurrent_write", "The Vault kept changing during context creation; run it again.")

    # ---------------------------------------------------------------- commands
    def remember(self, statement: str, module: str, valid_from: str | None = None,
                 valid_until: str | None = None) -> Fact:
        """Record a user-declared fact about yourself."""
        self._check_module(module)
        seq, records = self.snapshot()
        policy = self._ingest_policy(records, module)
        fact = self._fact(statement, module, policy.epoch, valid_from=valid_from, valid_until=valid_until)
        self._commit([fact], seq)
        return fact

    def correct(self, fact_id: str, statement: str) -> Fact:
        """Replace what was believed (history is kept; the new record supersedes the old one)."""
        seq, records = self.snapshot()
        old = self._current_fact(records, fact_id)
        policy = self._ingest_policy(records, old.module)
        fact = self._fact(statement, old.module, policy.epoch, supersedes=(old.id,),
                          change_kind="correction", valid_from=old.valid_from, valid_until=old.valid_until)
        self._commit([fact], seq)
        return fact

    def retract(self, fact_id: str) -> Fact:
        """Withdraw a fact without asserting a replacement (not a deletion; always allowed)."""
        seq, records = self.snapshot()
        old = self._current_fact(records, fact_id)
        fact = self._fact(f"Retracted: {old.statement}"[:500], old.module, self.policy_of(records).epoch,
                          supersedes=(old.id,), change_kind="retraction")
        self._commit([fact], seq)
        return fact

    def set_module(self, module: str, *, ingest: bool | None = None, expose: bool | None = None) -> ModulePolicy:
        self._check_module(module)
        if ingest is None and expose is None:
            raise AptuniError("nothing_to_change", "Pass --ingest and/or --expose.")
        seq, records = self.snapshot()
        policy = with_switch(self.policy_of(records), module, ingest=ingest, expose=expose)
        self._commit([policy], seq)
        return policy

    def doctor(self) -> VerifyReport:
        vault = self.vault()
        vault.recover()
        return vault.verify()

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _check_module(module: str) -> None:
        if module not in MODULES:
            raise AptuniError("unknown_module", f"Unknown module '{module}'. Choose one of: {', '.join(MODULES)}.")

    def _ingest_policy(self, records: RecordSet, module: str) -> ModulePolicy:
        policy = self.policy_of(records)
        if not can_ingest(policy, module):
            raise AptuniError("module_ingest_disabled", f"Module '{module}' is not accepting new information.")
        return policy

    @staticmethod
    def _current_fact(records: RecordSet, fact_id: str) -> Any:
        for fact in records.current_facts():
            if fact.id == fact_id:
                return fact
        raise AptuniError("fact_not_current", f"No current fact with id {fact_id}.")

    @staticmethod
    def _fact(statement: str, module: str, epoch: int, *, supersedes: tuple[str, ...] = (),
              change_kind: str = "assert", valid_from: str | None = None, valid_until: str | None = None) -> Fact:
        now = utc_now()
        try:
            return Fact(
                record_type="fact", id=new_id("fct"), schema_version=1, recorded_at=now,
                valid_from=valid_from, valid_until=valid_until, module=module,
                provenance=Provenance(source_id=None, episode=CLI_EPISODE, locator=None),
                trust="user_declared", retention=DECLARED_RETENTION, policy_epoch=epoch, confidence=None,
                review_status="declared", supersedes=supersedes, change_kind=change_kind,
                type="declared_statement", subject="self", predicate="states", object=None,
                statement=statement.strip(), evidence_ids=(), memory_ids=(), observed_at=now, ingested_at=None,
            )
        except (ValidationError, ValueError) as error:
            raise AptuniError("invalid_record", f"Invalid fact: {error}") from error

    def _commit(self, records: list[Any], expected_seq: int) -> None:
        if committed_purge_intent(self.workspace.state_dir):
            message = "A confirmed privacy purge is in progress; retry or cancel it before writing."
            raise AptuniError("privacy_action_in_progress", message)
        try:
            self.vault().commit(records, expected_seq=expected_seq)
        except ConflictError as error:
            raise AptuniError("concurrent_write", "The Vault changed while this command ran; run it again.") from error
        except InvariantError as error:
            raise AptuniError("invariant_violation", str(error)) from error

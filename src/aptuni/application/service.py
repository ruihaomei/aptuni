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
from typing import Any

from pydantic import ValidationError

from aptuni.application.errors import AptuniError
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import MODULES, Fact, ModulePolicy, Provenance, RetentionLabel, SchemaVersionError
from aptuni.domain.temporal import utc_now
from aptuni.policy.modules import can_ingest, default_policy, with_switch
from aptuni.retrieval.sqlite import ProjectionError, ProjectionStatus, SqliteProjection, documents_for
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


class AptuniService(SourceCommands):
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
        projection = SqliteProjection(self.workspace.state_dir)
        for _ in range(3):
            seq, records = self.snapshot()
            try:
                projection.ensure(documents_for(records.exposable()), seq)
                rows = projection.search(query, module=module, limit=limit)
            except (OSError, ProjectionError, ValueError) as error:
                message = "The search index is unavailable; canonical data is safe."
                raise AptuniError("projection_failed", message) from error
            final_seq, final_records = self.snapshot()
            if final_seq != seq:
                continue
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
        raise AptuniError("concurrent_write", "The Vault kept changing during search; run it again.")

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
        try:
            self.vault().commit(records, expected_seq=expected_seq)
        except ConflictError as error:
            raise AptuniError("concurrent_write", "The Vault changed while this command ran; run it again.") from error
        except InvariantError as error:
            raise AptuniError("invariant_violation", str(error)) from error

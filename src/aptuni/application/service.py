"""Application service: the single entry point used by the CLI (and later MCP and the SDK).

Every write goes through the Vault's validated, atomic commit. The owner sees all current facts;
agent-facing views go through ``exposable()`` and the module policy (fail closed).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aptuni.application.errors import AptuniError
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import MODULES, Fact, ModulePolicy, Provenance, RetentionLabel
from aptuni.domain.temporal import utc_now
from aptuni.policy.modules import can_ingest, default_policy, with_switch
from aptuni.vault.fsgate import UnsupportedFilesystemError
from aptuni.vault.store import ConflictError, Vault, VerifyReport

CLI_EPISODE = "cli"
DECLARED_RETENTION = RetentionLabel(retention_class="canonical", purpose="user_declared_profile",
                                    expires_at=None, full_content=False)


@dataclass(frozen=True)
class Status:
    vault_path: Path
    state_dir: Path
    seq: int
    policy_epoch: int
    counts: dict[str, int]
    modules: dict[str, tuple[bool, bool]]  # module -> (ingest, expose)


class AptuniService:
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
        except UnsupportedFilesystemError as error:
            raise AptuniError("unsupported_filesystem", str(error)) from error
        vault.commit([default_policy()], expected_seq=0)
        self.workspace.save(vault_path)
        self._vault = vault
        return self.status()

    def vault(self) -> Vault:
        if self._vault is None:
            path = self.workspace.vault_path()
            if path is None:
                raise AptuniError("not_initialized", "No Vault configured. Run `aptuni init` first.")
            try:
                self._vault = Vault.open(path, self.workspace.state_dir)
            except FileNotFoundError as error:
                raise AptuniError("vault_missing", f"The configured Vault is missing: {path}") from error
        return self._vault

    # ---------------------------------------------------------------- queries
    def records(self) -> RecordSet:
        return self.vault().record_set()

    def policy(self) -> ModulePolicy:
        policy = self.records().policy()
        if policy is None:
            raise AptuniError("policy_missing", "The Vault has no module policy; run `aptuni doctor`.")
        return policy

    def status(self) -> Status:
        vault = self.vault()
        records = vault.record_set()
        policy = records.policy()
        return Status(
            vault_path=vault.root, state_dir=vault.state_dir, seq=vault.head().seq,
            policy_epoch=policy.epoch if policy else 0,
            counts=dict(Counter(r.record_type for r in records.records())),
            modules={m: (s.ingest_enabled, s.expose_enabled) for m, s in (policy.modules if policy else {}).items()},
        )

    def facts(self, module: str | None = None, as_known_at: datetime | None = None) -> list[Any]:
        """Current facts as the owner sees them (including modules hidden from agents)."""
        facts = self.records().current_facts(as_known_at)
        return [f for f in facts if module is None or f.module == module]

    def exposable(self) -> list[Any]:
        """What an agent may see under the current policy (fail closed)."""
        return self.records().exposable()

    def history(self) -> list[Any]:
        return [r for r in self.records().records() if r.record_type == "fact"]

    # ---------------------------------------------------------------- commands
    def remember(self, statement: str, module: str, valid_from: str | None = None,
                 valid_until: str | None = None) -> Fact:
        """Record a user-declared fact about yourself."""
        self._check_module(module)
        policy = self.policy()
        if not can_ingest(policy, module):
            raise AptuniError("module_ingest_disabled", f"Module '{module}' is not accepting new information.")
        fact = self._fact(statement, module, policy.epoch, valid_from=valid_from, valid_until=valid_until)
        self._commit([fact])
        return fact

    def correct(self, fact_id: str, statement: str) -> Fact:
        """Replace what was believed (history is kept; the new record supersedes the old one)."""
        old = self._current_fact(fact_id)
        fact = self._fact(statement, old.module, self.policy().epoch, supersedes=(old.id,),
                          change_kind="correction", valid_from=old.valid_from, valid_until=old.valid_until)
        self._commit([fact])
        return fact

    def retract(self, fact_id: str) -> Fact:
        """Withdraw a fact without asserting a replacement (not a deletion)."""
        old = self._current_fact(fact_id)
        fact = self._fact(f"Retracted: {old.statement}"[:500], old.module, self.policy().epoch,
                          supersedes=(old.id,), change_kind="retraction")
        self._commit([fact])
        return fact

    def set_module(self, module: str, *, ingest: bool | None = None, expose: bool | None = None) -> ModulePolicy:
        self._check_module(module)
        if ingest is None and expose is None:
            raise AptuniError("nothing_to_change", "Pass --ingest and/or --expose.")
        policy = with_switch(self.policy(), module, ingest=ingest, expose=expose)
        self._commit([policy])
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

    def _current_fact(self, fact_id: str) -> Any:
        for fact in self.records().current_facts():
            if fact.id == fact_id:
                return fact
        raise AptuniError("fact_not_current", f"No current fact with id {fact_id}.")

    def _fact(self, statement: str, module: str, epoch: int, *, supersedes: tuple[str, ...] = (),
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

    def _commit(self, records: list[Any]) -> None:
        vault = self.vault()
        try:
            vault.commit(records, expected_seq=vault.head().seq)
        except InvariantError as error:
            raise AptuniError("invariant_violation", str(error)) from error
        except ConflictError as error:
            raise AptuniError("concurrent_write", "The Vault changed during the write; try again.") from error

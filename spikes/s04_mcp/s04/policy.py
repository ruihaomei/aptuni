"""Disposable policy/journal core used to prove S04 adapter boundaries."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


class PolicyDenied(RuntimeError):
    """A stable content-free policy denial."""


@dataclass(frozen=True, slots=True)
class PendingAction:
    action_id: str
    principal: str
    kind: str
    scope: str
    digest: str
    epoch: int


@dataclass(frozen=True, slots=True)
class IntentReceipt:
    action_id: str
    state: str


class PolicyCore:
    """Small SQLite-backed model of the application-service security contract."""

    def __init__(self, database: Path | str = ":memory:") -> None:
        self.connection = sqlite3.connect(str(database), check_same_thread=False, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.egress_allowed = True
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value INTEGER NOT NULL);
            INSERT OR IGNORE INTO metadata(key, value) VALUES ('epoch', 1);
            CREATE TABLE IF NOT EXISTS actions(
                action_id TEXT PRIMARY KEY, principal TEXT NOT NULL, kind TEXT NOT NULL,
                scope TEXT NOT NULL, digest TEXT NOT NULL, epoch INTEGER NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS intents(
                action_id TEXT PRIMARY KEY REFERENCES actions(action_id), state TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidates(
                idempotency_key TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, statement_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS effects(action_id TEXT PRIMARY KEY REFERENCES actions(action_id));
            """
        )

    def close(self) -> None:
        self.connection.close()

    @property
    def epoch(self) -> int:
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key = 'epoch'"
        ).fetchone()
        return int(row[0])

    @property
    def external_effect_count(self) -> int:
        row = self.connection.execute("SELECT count(*) FROM effects").fetchone()
        return int(row[0])

    def read_identity(self, principal: str, *, host_class: str, strict_local: bool) -> dict[str, str]:
        if principal not in {"claude", "codex", "test-local"}:
            raise PolicyDenied("unknown_principal")
        if strict_local and host_class != "proven_local":
            raise PolicyDenied("host_model_egress_denied")
        return {"display_name": "Synthetic Learner", "locale": "zh-CN"}

    def request_action(self, principal: str, kind: str, scope: str) -> PendingAction:
        if principal not in {"claude", "codex"}:
            raise PolicyDenied("unknown_principal")
        if kind not in {"purge", "grant_module", "network_export"}:
            raise PolicyDenied("unknown_action")
        canonical = json.dumps(
            {"epoch": self.epoch, "kind": kind, "principal": principal, "scope": scope},
            separators=(",", ":"), sort_keys=True,
        )
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        action = PendingAction(uuid.uuid4().hex, principal, kind, scope, digest, self.epoch)
        with self.connection:
            self.connection.execute(
                "INSERT INTO actions(action_id, principal, kind, scope, digest, epoch) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (action.action_id, action.principal, action.kind, action.scope, action.digest, action.epoch),
            )
        return action

    def bump_epoch(self) -> None:
        with self.connection:
            self.connection.execute("UPDATE metadata SET value = value + 1 WHERE key = 'epoch'")

    def revoke_egress(self) -> None:
        self.egress_allowed = False
        self.bump_epoch()

    def approve(
        self,
        action_id: str,
        principal: str,
        *,
        channel: str,
        expected_digest: str | None = None,
        expected_scope: str | None = None,
    ) -> IntentReceipt:
        if channel != "terminal":
            raise PolicyDenied("terminal_only")
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                row = self.connection.execute(
                    "SELECT * FROM actions WHERE action_id = ?", (action_id,)
                ).fetchone()
                if row is None:
                    raise PolicyDenied("exact_action_id_required")
                if row["principal"] != principal:
                    raise PolicyDenied("principal_mismatch")
                if row["epoch"] != self.epoch:
                    raise PolicyDenied("stale_policy_epoch")
                if expected_digest is not None and row["digest"] != expected_digest:
                    raise PolicyDenied("action_digest_mismatch")
                if expected_scope is not None and row["scope"] != expected_scope:
                    raise PolicyDenied("scope_mismatch")
                if row["consumed"]:
                    raise PolicyDenied("already_consumed")
                self.connection.execute(
                    "UPDATE actions SET consumed = 1 WHERE action_id = ?", (action_id,)
                )
                self.connection.execute(
                    "INSERT INTO intents(action_id, state) VALUES (?, 'pending')", (action_id,)
                )
                self.connection.execute("COMMIT")
            except BaseException:
                self.connection.execute("ROLLBACK")
                raise
        return IntentReceipt(action_id, "pending")

    def terminal_approve(
        self,
        action_id: str,
        principal: str,
        *,
        expected_digest: str | None = None,
        expected_scope: str | None = None,
    ) -> IntentReceipt:
        return self.approve(
            action_id, principal, channel="terminal", expected_digest=expected_digest,
            expected_scope=expected_scope,
        )

    def race_terminal_approvals(self, action_id: str, principal: str, contenders: int) -> list[str]:
        def attempt(_: int) -> str:
            try:
                self.terminal_approve(action_id, principal)
                return "approved"
            except PolicyDenied as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=contenders) as executor:
            return list(executor.map(attempt, range(contenders)))

    def intent_count(self, action_id: str) -> int:
        row = self.connection.execute(
            "SELECT count(*) FROM intents WHERE action_id = ?", (action_id,)
        ).fetchone()
        return int(row[0])

    def run_worker(self, action_id: str, *, crash_after_effect: bool = False) -> str:
        with self.lock:
            row = self.connection.execute(
                "SELECT a.kind, i.state FROM actions a JOIN intents i USING(action_id) "
                "WHERE action_id = ?", (action_id,)
            ).fetchone()
            if row is None:
                raise PolicyDenied("intent_not_found")
            if row["state"] != "pending":
                return str(row["state"])
            if row["kind"] == "network_export" and not self.egress_allowed:
                state = "cancelled_policy"
            else:
                with self.connection:
                    self.connection.execute(
                        "INSERT OR IGNORE INTO effects(action_id) VALUES (?)", (action_id,)
                    )
                if crash_after_effect:
                    raise RuntimeError("injected_crash_after_effect")
                state = "complete"
            with self.connection:
                self.connection.execute(
                    "UPDATE intents SET state = ? WHERE action_id = ?", (state, action_id)
                )
            return state

    def observe(self, statement: str, idempotency_key: str) -> dict[str, object]:
        digest = hashlib.sha256(statement.encode()).hexdigest()
        candidate_id = "candidate-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:16]
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO candidates(idempotency_key, candidate_id, statement_digest) "
                "VALUES (?, ?, ?)", (idempotency_key, candidate_id, digest)
            )
        row = self.connection.execute(
            "SELECT candidate_id, statement_digest FROM candidates WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if row["statement_digest"] != digest:
            raise PolicyDenied("idempotency_conflict")
        return {"candidate_id": row["candidate_id"], "review_state": "quarantined", "exposable": False}

"""Private, content-free longitudinal dogfooding state for the maintainer."""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from aptuni.application.errors import AptuniError
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import sha256_text
from aptuni.domain.invariants import RecordSet
from aptuni.domain.temporal import utc_now
from aptuni.policy.profile_promotion import profile_review_state_of
from aptuni.policy.promotion import review_state_of
from aptuni.vault.locks import source_operations_lock

MAX_STATE_BYTES = 1_000_000
MAX_TRIALS = 2_000
MAX_SNAPSHOTS = 3_650
TRIAL_ID_RE = re.compile(r"^trial-[0-9a-f]{16}$")
CANONICAL_ID_RE = re.compile(r"^[a-z]{3}_[0-9A-Z]{26}$")
TEMP_NAME_RE = re.compile(r"^\.longitudinal\.[0-9]+\.[0-9a-f]{16}\.tmp$")
V1_SNAPSHOT_KEYS = {
    "captured_at", "vault_seq", "fact", "memory", "evidence", "observation", "candidate_memory",
    "memory_pending_review", "memory_pinned", "memory_revoked", "memory_corrections",
    "fact_corrections", "profile_promoted", "profile_pending_review", "profile_accepted",
    "profile_rejected",
}
SNAPSHOT_KEYS = V1_SNAPSHOT_KEYS | {
    "source_updates", "source_retractions", "superseded_records", "review_backlog",
    "review_decisions", "extended_metrics_available",
}
V1_TRIAL_KEYS = {
    "id", "query_digest", "vault_seq", "created_at", "record_ids", "useful_ids", "noise_ids",
}
V2_TRIAL_KEYS = V1_TRIAL_KEYS | {
    "requested_units", "used_units", "truncated", "exposure_violations", "context_metrics_available",
}
#: Schema v3 records which ordinary Context mode a trial measured: L3 only, or L3 plus L4 Evidence.
TRIAL_KEYS = V2_TRIAL_KEYS | {"include_evidence"}
SCHEMA_VERSION = 3
STATE_KEYS = {"schema_version", "trials", "snapshots"}


@dataclass(frozen=True)
class EvaluationItem:
    id: str
    kind: str
    module: str
    text: str


@dataclass(frozen=True)
class EvaluationTrial:
    id: str
    query_digest: str
    vault_seq: int
    created_at: str
    record_ids: tuple[str, ...]
    items: tuple[EvaluationItem, ...]
    scored: bool
    requested_units: int
    used_units: int
    truncated: bool
    exposure_violations: int
    useful_ids: tuple[str, ...] = ()
    noise_ids: tuple[str, ...] = ()
    include_evidence: bool = False


class EvaluationCommands:
    workspace: Workspace

    def snapshot(self) -> tuple[int, RecordSet]:
        raise NotImplementedError

    def sources(self) -> list[Any]:
        raise NotImplementedError

    def index_status(self) -> Any:
        raise NotImplementedError

    def _evaluation_context(self, query: str, limit: int, *, include_evidence: bool = False) -> Any:
        raise NotImplementedError

    @property
    def _evaluation_root(self) -> Path:
        return self.workspace.state_dir / "evaluation"

    @property
    def _evaluation_path(self) -> Path:
        return self._evaluation_root / "longitudinal.json"

    def evaluation_setup(self) -> dict[str, Any]:
        seq, records = self.snapshot()
        policy = records.policy()
        index = self.index_status()
        return {
            "vault_initialized": True,
            "vault_seq": seq,
            "source_types": sorted({source.source_type for source in self.sources()}),
            "enabled_ingest_modules": sorted(
                name for name, switch in (policy.modules if policy else {}).items() if switch.ingest_enabled
            ),
            "enabled_expose_modules": sorted(
                name for name, switch in (policy.modules if policy else {}).items() if switch.expose_enabled
            ),
            "canonical_counts": self._counts(records),
            "retrieval_projection": index.state,
            "memory_pending_review": sum(
                record.record_type == "memory"
                and review_state_of(record, records) == "auto_promoted_pending_review"
                for record in records.records()
            ),
            "profile_pending_review": sum(
                record.record_type == "fact" and record.type == "profile.promoted_memory"
                and profile_review_state_of(record, records) == "auto_promoted_pending_review"
                for record in records.records()
            ),
        }

    def evaluation_trial(self, query: str, *, limit: int = 5, include_evidence: bool = False) -> EvaluationTrial:
        if not query.strip() or type(limit) is not int or not 1 <= limit <= 20:
            raise AptuniError("invalid_evaluation_trial", "Evaluation needs a query and a limit from 1 to 20.")
        if type(include_evidence) is not bool:
            raise AptuniError("invalid_evaluation_trial", "The evaluation Evidence mode must be true or false.")
        # Evidence is the explicit L4 expansion (ADR-0005); a trial measures the mode it requested.
        response = self._evaluation_context(query, limit, include_evidence=include_evidence)
        items = tuple(
            EvaluationItem(unit.canonical_id, unit.kind, unit.module or "", unit.text)
            for unit in response.units if unit.canonical_id is not None
        )
        row = {
            "id": "trial-" + secrets.token_hex(8),
            "query_digest": sha256_text(query.strip()),
            "vault_seq": response.vault_seq,
            "created_at": utc_now().isoformat(),
            "record_ids": [item.id for item in items],
            "requested_units": response.requested_units,
            "used_units": response.used_units,
            "truncated": response.truncated,
            "exposure_violations": 0,
            "context_metrics_available": True,
            "include_evidence": include_evidence,
            "useful_ids": None,
            "noise_ids": None,
        }
        with source_operations_lock(self.workspace.state_dir):
            current_seq, current_records = self.snapshot()
            if current_seq != response.vault_seq:
                raise AptuniError(
                    "concurrent_write", "The Vault changed during the trial; run it again.",
                )
            policy = current_records.policy()
            row["exposure_violations"] = sum(
                record_id not in current_records.ids()
                or policy is None
                or not policy.modules[current_records.get(record_id).module].expose_enabled
                for record_id in row["record_ids"]
            )
            state = self._load_evaluation()
            if len(state["trials"]) >= MAX_TRIALS:
                raise AptuniError("evaluation_limit", "The longitudinal evaluation trial limit was reached.")
            state["trials"].append(row)
            self._write_evaluation(state)
        return self._trial(row, items)

    def score_evaluation_trial(
        self, trial_id: str, *, useful_ids: tuple[str, ...], noise_ids: tuple[str, ...], rest_noise: bool = False,
    ) -> EvaluationTrial:
        """Record the owner's exact labels; ``rest_noise`` marks every unlisted returned record noise."""
        with source_operations_lock(self.workspace.state_dir):
            state = self._load_evaluation()
            row = next((trial for trial in state["trials"] if trial["id"] == trial_id), None)
            if row is None:
                raise AptuniError("evaluation_trial_not_found", "No exact evaluation trial has that id.")
            expected = set(row["record_ids"])
            useful, noise = set(useful_ids), set(noise_ids)
            if rest_noise and (useful | noise) <= expected:
                noise |= expected - useful
            if useful & noise or useful | noise != expected:
                raise AptuniError(
                    "evaluation_labels_incomplete", "You must classify every returned record as useful or noise.",
                )
            row["useful_ids"] = sorted(useful)
            row["noise_ids"] = sorted(noise)
            self._write_evaluation(state)
            return self._trial(row)

    def discard_evaluation_trials(self, trial_ids: tuple[str, ...]) -> tuple[str, ...]:
        """Remove exact trials (for example test or mislabelled runs); all ids must exist or none go."""
        if not trial_ids or len(set(trial_ids)) != len(trial_ids) \
                or not all(TRIAL_ID_RE.fullmatch(trial_id) for trial_id in trial_ids):
            raise AptuniError("invalid_evaluation_trial", "Name one or more distinct exact trial ids.")
        with source_operations_lock(self.workspace.state_dir):
            state = self._load_evaluation()
            known = {trial["id"] for trial in state["trials"]}
            if not set(trial_ids) <= known:
                raise AptuniError("evaluation_trial_not_found", "No exact evaluation trial has that id.")
            if any(trial["id"] in trial_ids and trial["exposure_violations"] for trial in state["trials"]):
                # Permission evidence must survive: a trial that saw an exposure violation stays.
                raise AptuniError(
                    "evaluation_trial_protected", "A trial that recorded an exposure violation cannot be discarded.",
                )
            state["trials"] = [trial for trial in state["trials"] if trial["id"] not in set(trial_ids)]
            self._write_evaluation(state)
        return trial_ids

    def capture_evaluation_snapshot(self) -> dict[str, Any]:
        seq, records = self.snapshot()
        memories = [record for record in records.records() if record.record_type == "memory"]
        promoted = [record for record in records.records()
                    if record.record_type == "fact" and record.type == "profile.promoted_memory"]
        snapshot = {
            "captured_at": utc_now().isoformat(),
            "vault_seq": seq,
            **self._counts(records),
            "memory_pending_review": sum(
                review_state_of(memory, records) == "auto_promoted_pending_review" for memory in memories),
            "memory_pinned": sum(review_state_of(memory, records) == "pinned" for memory in memories),
            "memory_revoked": sum(review_state_of(memory, records) == "revoked" for memory in memories),
            "memory_corrections": sum(memory.change_kind == "correction" for memory in memories),
            "fact_corrections": sum(
                record.record_type == "fact" and record.change_kind == "correction"
                for record in records.records()),
            "profile_promoted": len(promoted),
            "profile_pending_review": sum(
                profile_review_state_of(fact, records) == "auto_promoted_pending_review" for fact in promoted),
            "profile_accepted": sum(
                profile_review_state_of(fact, records) == "accepted" for fact in promoted),
            "profile_rejected": sum(
                profile_review_state_of(fact, records) == "revoked" for fact in promoted),
            "source_updates": sum(
                record.record_type == "evidence" and record.change_kind in {"world_change", "correction"}
                for record in records.records()),
            "source_retractions": sum(
                record.record_type == "evidence" and record.change_kind == "retraction"
                for record in records.records()),
            "superseded_records": sum(
                bool(record.supersedes) for record in records.records() if hasattr(record, "supersedes")
            ),
            "review_backlog": sum(
                review_state_of(memory, records) == "auto_promoted_pending_review" for memory in memories
            ) + sum(
                profile_review_state_of(fact, records) == "auto_promoted_pending_review" for fact in promoted
            ),
            "review_decisions": sum(
                record.record_type == "review_event" and record.actor == "user_cli"
                for record in records.records()),
            "extended_metrics_available": True,
        }
        with source_operations_lock(self.workspace.state_dir):
            if self.snapshot()[0] != seq:
                raise AptuniError(
                    "concurrent_write", "The Vault changed during the snapshot; run it again.",
                )
            state = self._load_evaluation()
            existing = next((item for item in state["snapshots"] if item["vault_seq"] == seq), None)
            if existing is not None:
                if not existing["extended_metrics_available"]:
                    state["snapshots"][state["snapshots"].index(existing)] = snapshot
                    self._write_evaluation(state)
                    return snapshot
                return dict(existing)
            if len(state["snapshots"]) >= MAX_SNAPSHOTS:
                raise AptuniError("evaluation_limit", "The longitudinal evaluation snapshot limit was reached.")
            state["snapshots"].append(snapshot)
            self._write_evaluation(state)
            return snapshot

    def evaluation_report(self) -> dict[str, Any]:
        self.snapshot()  # open/recover before the source-operation lock; see locks.py lock order
        with source_operations_lock(self.workspace.state_dir):
            state = self._load_evaluation()
            scored = [trial for trial in state["trials"] if trial["useful_ids"] is not None]
            returned = sum(len(trial["record_ids"]) for trial in scored)
            useful_ids = [record_id for trial in scored for record_id in trial["useful_ids"]]
            noise = sum(len(trial["noise_ids"]) for trial in scored)
            measured = [trial for trial in scored if trial["context_metrics_available"]]
            used_units = sum(trial["used_units"] for trial in measured)
            measured_useful_ids = [
                record_id for trial in measured for record_id in trial["useful_ids"]
            ]
            _, records = self.snapshot()
            traceable = sum(self._traceable(records, record_id) for record_id in useful_ids)
            useful_trials = sum(bool(trial["useful_ids"]) for trial in scored)
            return {
                "schema_version": SCHEMA_VERSION,
                "retrieval": {
                    "trials": len(state["trials"]),
                    "scored_trials": len(scored),
                    "returned_records": returned,
                    "useful_records": len(useful_ids),
                    "noise_records": noise,
                    "useful_context_rate": len(useful_ids) / returned if returned else 0.0,
                    "noise_rate": noise / returned if returned else 0.0,
                    "traceable_useful_rate": traceable / len(useful_ids) if useful_ids else 0.0,
                    "unsupported_useful_records": len(useful_ids) - traceable,
                    "trials_with_useful_context_rate": useful_trials / len(scored) if scored else 0.0,
                    "used_context_units": used_units,
                    "measured_context_trials": len(measured),
                    "units_per_useful_record": (
                        used_units / len(measured_useful_ids) if measured_useful_ids else 0.0
                    ),
                    "useful_records_per_1000_units": (
                        1000 * len(measured_useful_ids) / used_units if used_units else 0.0
                    ),
                    "unscored_trial_ids": [
                        trial["id"] for trial in state["trials"] if trial["useful_ids"] is None
                    ],
                    "repeated_queries": self._repeated_queries(scored),
                    "by_context_mode": {
                        "profile_memory": self._mode_metrics(
                            [trial for trial in scored if not trial["include_evidence"]]),
                        "with_evidence": self._mode_metrics(
                            [trial for trial in scored if trial["include_evidence"]]),
                    },
                },
                "permissions": {
                    "exposure_violations": sum(
                        trial["exposure_violations"] for trial in state["trials"]
                        if trial["context_metrics_available"]
                    ),
                },
                "snapshots": list(state["snapshots"]),
            }

    def reset_evaluation(self) -> bool:
        """Delete only Aptuni's bounded derived evaluation state."""
        with source_operations_lock(self.workspace.state_dir):
            root = self._evaluation_root
            if root.is_symlink():
                raise AptuniError("evaluation_state_unsafe", "The evaluation state location is not safe.")
            if not root.exists():
                return False
            if not root.is_dir():
                raise AptuniError("evaluation_state_invalid", "The evaluation state is invalid.")
            children = self._managed_evaluation_children()
            for child in children:
                child.unlink()
            root.rmdir()
            directory_fd = os.open(self.workspace.state_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return True

    @staticmethod
    def _repeated_queries(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """First versus latest usefulness for each query digest the owner scored more than once."""
        groups: dict[tuple[str, bool], list[dict[str, Any]]] = {}
        for trial in scored:  # rows are stored in creation order
            groups.setdefault((trial["query_digest"], trial["include_evidence"]), []).append(trial)

        def rate(trial: dict[str, Any]) -> float:
            return len(trial["useful_ids"]) / len(trial["record_ids"]) if trial["record_ids"] else 0.0

        return [
            {
                "query_digest_prefix": digest.removeprefix("sha256:")[:12],
                "mode": "with_evidence" if evidence else "profile_memory",
                "scored_trials": len(trials),
                "first_useful_rate": rate(trials[0]),
                "latest_useful_rate": rate(trials[-1]),
            }
            for (digest, evidence), trials in groups.items() if len(trials) > 1
        ]

    @staticmethod
    def _mode_metrics(scored: list[dict[str, Any]]) -> dict[str, Any]:
        returned = sum(len(trial["record_ids"]) for trial in scored)
        useful = sum(len(trial["useful_ids"]) for trial in scored)
        noise = sum(len(trial["noise_ids"]) for trial in scored)
        return {
            "scored_trials": len(scored),
            "returned_records": returned,
            "useful_records": useful,
            "noise_records": noise,
            "useful_context_rate": useful / returned if returned else 0.0,
            "noise_rate": noise / returned if returned else 0.0,
            "trials_with_useful_context_rate": (
                sum(bool(trial["useful_ids"]) for trial in scored) / len(scored) if scored else 0.0
            ),
        }

    @staticmethod
    def _counts(records: RecordSet) -> dict[str, int]:
        return {
            name: sum(record.record_type == name for record in records.records())
            for name in ("fact", "memory", "evidence", "observation", "candidate_memory")
        }

    @staticmethod
    def _traceable(records: RecordSet, record_id: str) -> bool:
        if record_id not in records.ids():
            return False
        record = records.get(record_id)
        return bool(
            record.trust == "user_declared"
            or record.provenance.source_id
            or getattr(record, "evidence_ids", ())
            or getattr(record, "memory_ids", ())
            or getattr(record, "candidate_id", None)
        )

    @staticmethod
    def _trial(row: dict[str, Any], items: tuple[EvaluationItem, ...] = ()) -> EvaluationTrial:
        useful = row["useful_ids"]
        noise = row["noise_ids"]
        return EvaluationTrial(
            row["id"], row["query_digest"], row["vault_seq"], row["created_at"],
            tuple(row["record_ids"]), items, useful is not None,
            row["requested_units"], row["used_units"], row["truncated"], row["exposure_violations"],
            tuple(useful or ()), tuple(noise or ()), row["include_evidence"],
        )

    def _load_evaluation(self) -> dict[str, Any]:
        path = self._evaluation_path
        if self._evaluation_root.is_symlink() or path.is_symlink():
            raise AptuniError("evaluation_state_unsafe", "The evaluation state location is not safe.")
        if self._evaluation_root.exists() and (
            not self._evaluation_root.is_dir()
            or stat.S_IMODE(self._evaluation_root.stat().st_mode) != 0o700
        ):
            raise AptuniError("evaluation_state_invalid", "The evaluation state is invalid.")
        if self._evaluation_root.exists():
            self._managed_evaluation_children()
        if not path.exists():
            return {"schema_version": SCHEMA_VERSION, "trials": [], "snapshots": []}
        try:
            if path.stat().st_size > MAX_STATE_BYTES:
                raise ValueError("too_large")
            if not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise ValueError("unsafe_mode")
            state = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or set(state) != STATE_KEYS \
                    or type(state.get("schema_version")) is not int \
                    or state.get("schema_version") not in {1, 2, SCHEMA_VERSION} \
                    or not isinstance(state.get("trials"), list) \
                    or not isinstance(state.get("snapshots"), list):
                raise ValueError("invalid_schema")
            migrated = state["schema_version"] != SCHEMA_VERSION
            if state["schema_version"] == 1:
                state = self._migrate_v1(state)
            if state["schema_version"] == 2:
                state = self._migrate_v2(state)
            self._validate_evaluation(state)
            if migrated:
                self._write_evaluation(state)
            return cast(dict[str, Any], state)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, AttributeError) as error:
            raise AptuniError("evaluation_state_invalid", "The evaluation state is invalid.") from error

    @staticmethod
    def _migrate_v1(state: dict[str, Any]) -> dict[str, Any]:
        trials: list[dict[str, Any]] = []
        for raw in state["trials"]:
            if not isinstance(raw, dict) or set(raw) != V1_TRIAL_KEYS:
                raise ValueError("invalid_v1_trial")
            trial = dict(raw)
            trial.update({
                "requested_units": 4000,
                "used_units": 0,
                "truncated": False,
                "exposure_violations": 0,
                "context_metrics_available": False,
            })
            trials.append(trial)
        snapshots: list[dict[str, Any]] = []
        for raw in state["snapshots"]:
            if not isinstance(raw, dict) or set(raw) != V1_SNAPSHOT_KEYS:
                raise ValueError("invalid_v1_snapshot")
            snapshot = dict(raw)
            snapshot.update({
                "source_updates": 0,
                "source_retractions": 0,
                "superseded_records": 0,
                "review_backlog": 0,
                "review_decisions": 0,
                "extended_metrics_available": False,
            })
            snapshots.append(snapshot)
        return {"schema_version": 2, "trials": trials, "snapshots": snapshots}

    @staticmethod
    def _migrate_v2(state: dict[str, Any]) -> dict[str, Any]:
        """Every schema-v2 trial came from the L3-only default; none could request Evidence."""
        trials: list[dict[str, Any]] = []
        for raw in state["trials"]:
            if not isinstance(raw, dict) or set(raw) != V2_TRIAL_KEYS:
                raise ValueError("invalid_v2_trial")
            trials.append({**raw, "include_evidence": False})
        return {"schema_version": SCHEMA_VERSION, "trials": trials, "snapshots": state["snapshots"]}

    @staticmethod
    def _validate_evaluation(state: dict[str, Any]) -> None:
        trials, snapshots = state["trials"], state["snapshots"]
        if len(trials) > MAX_TRIALS or len(snapshots) > MAX_SNAPSHOTS:
            raise ValueError("too_many_rows")
        for trial in trials:
            if not isinstance(trial, dict) or set(trial) != TRIAL_KEYS:
                raise ValueError("invalid_trial")
            if not TRIAL_ID_RE.fullmatch(trial["id"]) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", trial["query_digest"]
            ):
                raise ValueError("invalid_trial_identity")
            if type(trial["vault_seq"]) is not int or trial["vault_seq"] < 0:
                raise ValueError("invalid_trial_seq")
            EvaluationCommands._validate_trial_metrics(trial)
            EvaluationCommands._aware_time(trial["created_at"])
            record_ids = trial["record_ids"]
            if not isinstance(record_ids, list) or len(record_ids) > 20 \
                    or len(record_ids) != len(set(record_ids)) \
                    or not all(isinstance(value, str) and CANONICAL_ID_RE.fullmatch(value) for value in record_ids):
                raise ValueError("invalid_trial_records")
            useful, noise = trial["useful_ids"], trial["noise_ids"]
            if (useful is None) != (noise is None):
                raise ValueError("partial_trial_score")
            if useful is not None and (
                not isinstance(useful, list) or not isinstance(noise, list)
                or set(useful) & set(noise) or set(useful) | set(noise) != set(record_ids)
            ):
                raise ValueError("invalid_trial_score")
        for snapshot in snapshots:
            if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_KEYS:
                raise ValueError("invalid_snapshot")
            EvaluationCommands._aware_time(snapshot["captured_at"])
            if type(snapshot["extended_metrics_available"]) is not bool:
                raise ValueError("invalid_snapshot_metric")
            if any(type(snapshot[key]) is not int or snapshot[key] < 0
                   for key in SNAPSHOT_KEYS - {"captured_at", "extended_metrics_available"}):
                raise ValueError("invalid_snapshot_metric")

    @staticmethod
    def _validate_trial_metrics(trial: dict[str, Any]) -> None:
        if (type(trial["requested_units"]) is not int or trial["requested_units"] <= 0
                or type(trial["used_units"]) is not int
                or not 0 <= trial["used_units"] <= trial["requested_units"]
                or type(trial["truncated"]) is not bool
                or type(trial["exposure_violations"]) is not int
                or trial["exposure_violations"] < 0
                or type(trial["context_metrics_available"]) is not bool
                or type(trial["include_evidence"]) is not bool):
            raise ValueError("invalid_trial_metrics")

    @staticmethod
    def _aware_time(value: Any) -> None:
        if not isinstance(value, str):
            raise ValueError("invalid_time")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("naive_time")

    def _write_evaluation(self, state: dict[str, Any]) -> None:
        root, path = self._evaluation_root, self._evaluation_path
        if root.is_symlink() or path.is_symlink():
            raise AptuniError("evaluation_state_unsafe", "The evaluation state location is not safe.")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        self._managed_evaluation_children()
        body = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        if len(body.encode("utf-8")) > MAX_STATE_BYTES:
            raise AptuniError("evaluation_limit", "The longitudinal evaluation state limit was reached.")
        temporary = root / f".longitudinal.{os.getpid()}.{secrets.token_hex(8)}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            try:
                remaining = memoryview(body.encode("utf-8"))
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written <= 0:
                        raise OSError("evaluation_state_write_failed")
                    remaining = remaining[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(temporary, path)
            directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    def _managed_evaluation_children(self) -> tuple[Path, ...]:
        if (self._evaluation_root.is_symlink() or not self._evaluation_root.is_dir()
                or stat.S_IMODE(self._evaluation_root.stat().st_mode) != 0o700):
            raise AptuniError("evaluation_state_unsafe", "The evaluation state location is not safe.")
        children = tuple(self._evaluation_root.iterdir())
        if len(children) > 32:
            raise AptuniError("evaluation_state_unsafe", "The evaluation state location is not safe.")
        for child in children:
            managed = child.name == "longitudinal.json" or TEMP_NAME_RE.fullmatch(child.name) is not None
            if not managed or child.is_symlink() or not child.is_file():
                raise AptuniError("evaluation_state_unsafe", "The evaluation state location is not safe.")
        return children

"""Crash-safe, single-writer Vault protocol prototype (S01 spike; ADR-0001/0010).

Layout::

    <vault>/HEAD.json                 committed manifest (atomic rename), hash-chained
    <vault>/records/seg-NNNNNN-*.jsonl immutable JSONL segments (one per commit)
    <state>/writer.lock               flock target (kernel releases it when the holder dies)
    <state>/deletion-ledger.jsonl     irreversible id digests, outside the Vault and backups

Commit protocol (under an exclusive flock, optimistic ``expected_seq``):
write segment tmp -> full fsync -> rename -> dir fsync -> write HEAD tmp -> full fsync ->
rename -> dir fsync. A segment not listed in HEAD is an orphan and is removed by ``recover``.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from s01.fsgate import check_vault_filesystem
from s01.invariants import InvariantError, RecordSet
from s01.records import (
    CopyResult, DeletionLedgerEntry, DeletionReceipt, canonical_json, new_id, parse_record, sha256_text,
)

CRASH_POINTS = ("after_segment_tmp", "after_segment_rename", "after_head_tmp", "after_head_rename")
GENESIS = "0" * 64
READ_RETRIES = 50


class ConflictError(RuntimeError):
    """The Vault advanced since the caller read it (lost update prevented)."""


class VaultIntegrityError(RuntimeError):
    """A committed segment does not match its hash in HEAD (out-of-band edit or corruption)."""


@dataclass(frozen=True)
class Head:
    seq: int
    segments: tuple[dict[str, Any], ...]
    chain: str


@dataclass
class RecoveryReport:
    removed: list[str] = field(default_factory=list)
    remaining_orphans: list[str] = field(default_factory=list)


def _crash_point(name: str) -> None:
    if os.environ.get("S01_CRASH_AT") == name:
        os._exit(137)


def _full_fsync(fd: int) -> None:
    try:
        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
    except (AttributeError, OSError):
        os.fsync(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        _full_fsync(fd)
    finally:
        os.close(fd)


def _write_durable(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        _full_fsync(fd)
    finally:
        os.close(fd)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Vault:
    def __init__(self, root: Path, state_dir: Path) -> None:
        self.root = root
        self.state_dir = state_dir
        self.records_dir = root / "records"
        check_vault_filesystem(root)
        check_vault_filesystem(state_dir)

    # ---------------------------------------------------------------- lifecycle
    @classmethod
    def init(cls, root: Path, state_dir: Path) -> Vault:
        for directory in (root / "records", state_dir):
            directory.mkdir(parents=True, exist_ok=False if directory == root / "records" else True)
        vault = cls(root, state_dir)
        vault._write_head(Head(0, (), GENESIS))
        return vault

    @contextmanager
    def writer_lock(self) -> Iterator[None]:
        with open(self.state_dir / "writer.lock", "a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def try_writer_lock(self) -> bool:
        with open(self.state_dir / "writer.lock", "a+b") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            return True

    # ---------------------------------------------------------------- reading
    def head(self) -> Head:
        data = json.loads((self.root / "HEAD.json").read_text(encoding="utf-8"))
        return Head(data["seq"], tuple(data["segments"]), data["chain"])

    def read_all(self) -> list[Any]:
        """Return a consistent committed snapshot; retries if a purge swapped segments mid-read."""
        for _ in range(READ_RETRIES):
            head = self.head()
            try:
                return self._read_segments(head)
            except FileNotFoundError:
                time.sleep(0.01)
        raise VaultIntegrityError("could not obtain a stable snapshot")

    def _read_segments(self, head: Head) -> list[Any]:
        records: list[Any] = []
        for segment in head.segments:
            data = (self.records_dir / segment["name"]).read_bytes()
            if "sha256:" + hashlib.sha256(data).hexdigest() != segment["sha256"]:
                raise VaultIntegrityError(f"segment hash mismatch: {segment['name']}")
            lines = data.decode("utf-8").splitlines()
            if len(lines) != segment["count"]:
                raise VaultIntegrityError(f"segment record count mismatch: {segment['name']}")
            records.extend(parse_record(json.loads(line)) for line in lines)
        return records

    # ---------------------------------------------------------------- writing
    def commit(self, records: list[Any], expected_seq: int) -> Head:
        with self.writer_lock():
            head = self.head()
            if head.seq != expected_seq:
                raise ConflictError(f"expected seq {expected_seq}, vault is at {head.seq}")
            existing = self._read_segments(head)
            RecordSet(existing + records).validate()
            return self._append_segment(head, records)

    def _append_segment(self, head: Head, records: list[Any]) -> Head:
        payload = ("\n".join(canonical_json(r) for r in records) + "\n").encode("utf-8")
        name = f"seg-{head.seq + 1:06d}-{os.urandom(4).hex()}.jsonl"
        tmp = self.records_dir / f".tmp-{name}"
        _write_durable(tmp, payload)
        _crash_point("after_segment_tmp")
        os.replace(tmp, self.records_dir / name)
        _fsync_dir(self.records_dir)
        _crash_point("after_segment_rename")
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        entry = {"name": name, "sha256": digest, "count": len(records)}
        new_head = Head(head.seq + 1, head.segments + (entry,),
                        hashlib.sha256((head.chain + digest).encode("ascii")).hexdigest())
        self._write_head(new_head)
        return new_head

    def _write_head(self, head: Head) -> None:
        body = json.dumps({"format": 1, "seq": head.seq, "segments": list(head.segments),
                           "chain": head.chain}, sort_keys=True, indent=1).encode("utf-8")
        tmp = self.root / f".HEAD.{os.getpid()}.{os.urandom(4).hex()}.tmp"
        _write_durable(tmp, body)
        _crash_point("after_head_tmp")
        os.replace(tmp, self.root / "HEAD.json")
        _crash_point("after_head_rename")
        _fsync_dir(self.root)

    def recover(self) -> RecoveryReport:
        """Remove uncommitted tmp files/orphan segments, then finish any ledgered purge.

        The ledger entry is made durable before a purge rewrites segments, so a crash at any later
        boundary is completed here instead of resurrecting purged content.
        """
        report = RecoveryReport()
        with self.writer_lock():
            self._remove_orphans(report)
            head = self.head()
            ledger = self.ledger_digests()
            unfinished = {r.id for r in self._read_segments(head) if sha256_text(r.id) in ledger}
            if unfinished:
                self._purge_locked(head, unfinished, write_ledger=False)
                self._remove_orphans(report)
            committed = {s["name"] for s in self.head().segments}
            report.remaining_orphans = [p.name for p in self.records_dir.iterdir() if p.name not in committed]
        return report

    def _remove_orphans(self, report: RecoveryReport) -> None:
        committed = {s["name"] for s in self.head().segments}
        for path in list(self.records_dir.iterdir()) + list(self.root.glob(".HEAD.*.tmp")):
            if path.name not in committed:
                path.unlink()
                report.removed.append(path.name)

    # ---------------------------------------------------------------- purge / backup / restore
    def purge(self, record_ids: set[str], expected_seq: int) -> DeletionReceipt:
        """Privacy purge: rewrite segments without targets, ledger their id digests."""
        with self.writer_lock():
            head = self.head()
            if head.seq != expected_seq:
                raise ConflictError(f"expected seq {expected_seq}, vault is at {head.seq}")
            return self._purge_locked(head, record_ids)

    def _purge_locked(self, head: Head, record_ids: set[str], *, write_ledger: bool = True) -> DeletionReceipt:
        kept = [self._unlink(r, record_ids) for r in self._read_segments(head) if r.id not in record_ids]
        RecordSet(kept).validate()
        if write_ledger:
            self._append_ledger(record_ids)
        old = [s["name"] for s in head.segments]
        new_head = self._append_segment(Head(head.seq, (), head.chain), kept) if kept else Head(head.seq + 1, (), head.chain)
        if not kept:
            self._write_head(new_head)
        for name in old:
            (self.records_dir / name).unlink(missing_ok=True)
        _fsync_dir(self.records_dir)
        return DeletionReceipt(id=new_id("rcp"), schema_version=1, recorded_at=_now(), purge_id=new_id("rcp"),
                               terminal_state="complete_managed",
                               per_copy=(CopyResult(copy_class="canonical", result="deleted"),))

    @staticmethod
    def _unlink(record: Any, purged: set[str]) -> Any:
        updates = {}
        for name in ("evidence_ids", "memory_ids", "derived_from", "contradicts", "supersedes"):
            links = getattr(record, name, None)
            if links and purged.intersection(links):
                updates[name] = tuple(x for x in links if x not in purged)
        if not updates:
            return record
        raw = json.loads(canonical_json(record)) | {k: list(v) for k, v in updates.items()}
        try:
            return parse_record(raw)
        except ValueError as exc:
            raise InvariantError(f"purge would orphan {record.id}; purge it too") from exc

    def _append_ledger(self, record_ids: set[str]) -> None:
        path = self.state_dir / "deletion-ledger.jsonl"
        lines = "".join(
            canonical_json(DeletionLedgerEntry(id=new_id("led"), recorded_at=_now(),
                                               target_digest=sha256_text(rid))) + "\n"
            for rid in sorted(record_ids)
        )
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
            handle.flush()
            _full_fsync(handle.fileno())

    def ledger_digests(self) -> set[str]:
        path = self.state_dir / "deletion-ledger.jsonl"
        if not path.exists():
            return set()
        return {json.loads(line)["target_digest"] for line in path.read_text(encoding="utf-8").splitlines()}

    def backup_to(self, destination: Path) -> None:
        with self.writer_lock():
            shutil.copytree(self.root, destination)

    @classmethod
    def restore_from(cls, backup: Path, root: Path, state_dir: Path) -> Vault:
        """Restore a backup generation, then reapply the deletion ledger (no resurrection)."""
        staging = root.with_name(root.name + ".restoring")
        shutil.copytree(backup, staging)
        shutil.rmtree(root)
        os.replace(staging, root)
        vault = cls(root, state_dir)
        with vault.writer_lock():
            head = vault.head()
            ledger = vault.ledger_digests()
            doomed = {r.id for r in vault._read_segments(head) if sha256_text(r.id) in ledger}
            if doomed:
                vault._purge_locked(head, doomed, write_ledger=False)
        return vault

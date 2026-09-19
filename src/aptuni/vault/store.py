"""Crash-safe, single-writer canonical Vault (ADR-0001/0010; protocol proven in S01).

Layout::

    <vault>/HEAD.json                  committed manifest (atomic rename), hash-chained
    <vault>/records/seg-NNNNNN-*.jsonl immutable canonical JSONL segments (one per commit)
    <state>/writer.lock                flock target (the kernel releases it when the holder dies)
    <state>/deletion-ledger.jsonl      irreversible id digests, outside the Vault and its backups

Commit (exclusive flock + optimistic ``expected_seq``): write segment tmp -> full fsync -> rename
-> dir fsync -> write HEAD tmp -> full fsync -> rename -> dir fsync. A segment not listed in HEAD
is an orphan; ``recover()`` removes it and completes any ledgered purge. ``open()`` always runs
``recover()`` first (S01 F3). The chain detects uninformed edits only: HEAD is self-attesting.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aptuni.domain.ids import new_id, sha256_bytes, sha256_text
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import (
    CanonicalRecord,
    CopyResult,
    DeletionLedgerEntry,
    DeletionReceipt,
    canonical_json,
    parse_record,
)
from aptuni.domain.temporal import utc_now
from aptuni.vault.fsgate import check_vault_filesystem

CRASH_POINTS = ("after_segment_tmp", "after_segment_rename", "after_head_tmp", "after_head_rename")
GENESIS = "0" * 64
READ_RETRIES = 50
HEAD_FORMAT = 1


class ConflictError(RuntimeError):
    """The Vault advanced since the caller read it (lost update prevented)."""


class VaultIntegrityError(RuntimeError):
    """A committed segment does not match HEAD (out-of-band edit or corruption)."""


@dataclass(frozen=True)
class Head:
    seq: int
    segments: tuple[dict[str, Any], ...]
    chain: str


@dataclass
class RecoveryReport:
    removed: list[str] = field(default_factory=list)
    remaining_orphans: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerifyReport:
    ok: bool
    seq: int
    records: int
    problems: tuple[str, ...]


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


def _chain(previous: str, digest: str) -> str:
    return hashlib.sha256((previous + digest).encode("ascii")).hexdigest()


class Vault:
    def __init__(self, root: Path, state_dir: Path) -> None:
        self.root = root
        self.state_dir = state_dir
        self.records_dir = root / "records"
        self.crash_hook: Callable[[str], None] | None = None  # fault-injection seam for tests
        self._segment_cache: dict[tuple[str, str], list[CanonicalRecord]] = {}
        check_vault_filesystem(root)
        check_vault_filesystem(state_dir)

    # ---------------------------------------------------------------- lifecycle
    @classmethod
    def init(cls, root: Path, state_dir: Path) -> Vault:
        if (root / "HEAD.json").exists():
            raise FileExistsError(f"a Vault already exists at {root}")
        (root / "records").mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(state_dir, 0o700)
        vault = cls(root, state_dir)
        vault._write_head(Head(0, (), GENESIS))
        return vault

    @classmethod
    def open(cls, root: Path, state_dir: Path) -> Vault:
        """Open an existing Vault and recover before any read (S01 F3)."""
        if not (root / "HEAD.json").exists():
            raise FileNotFoundError(f"no Vault at {root}")
        vault = cls(root, state_dir)
        vault.recover()
        return vault

    def _crash(self, name: str) -> None:
        if self.crash_hook is not None:
            self.crash_hook(name)

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
        if data.get("format") != HEAD_FORMAT:
            raise VaultIntegrityError(f"unsupported HEAD format {data.get('format')!r}")
        return Head(data["seq"], tuple(data["segments"]), data["chain"])

    def read_all(self) -> list[CanonicalRecord]:
        """Return a consistent committed snapshot; retries if a purge swapped segments mid-read."""
        for _ in range(READ_RETRIES):
            head = self.head()
            try:
                return self._read_segments(head)
            except FileNotFoundError:
                time.sleep(0.01)
        raise VaultIntegrityError("could not obtain a stable snapshot")

    def record_set(self) -> RecordSet:
        return RecordSet(self.read_all())

    def _read_segments(self, head: Head) -> list[CanonicalRecord]:
        records: list[CanonicalRecord] = []
        for segment in head.segments:
            key = (segment["name"], segment["sha256"])
            cached = self._segment_cache.get(key)
            if cached is None:
                data = (self.records_dir / segment["name"]).read_bytes()
                if sha256_bytes(data) != segment["sha256"]:
                    raise VaultIntegrityError(f"segment hash mismatch: {segment['name']}")
                lines = data.decode("utf-8").splitlines()
                if len(lines) != segment["count"]:
                    raise VaultIntegrityError(f"segment record count mismatch: {segment['name']}")
                cached = [parse_record(json.loads(line)) for line in lines]
                self._segment_cache[key] = cached
            records.extend(cached)
        return records

    # ---------------------------------------------------------------- writing
    def commit(self, records: list[CanonicalRecord], expected_seq: int) -> Head:
        """Append ``records`` atomically; only the new records are validated (S01 F1)."""
        if not records:
            raise ValueError("commit requires at least one record")
        with self.writer_lock():
            head = self.head()
            if head.seq != expected_seq:
                raise ConflictError(f"expected seq {expected_seq}, vault is at {head.seq}")
            existing = self._read_segments(head)
            RecordSet([*existing, *records]).validate(only={r.id for r in records})
            return self._append_segment(head, records)

    def _append_segment(self, head: Head, records: list[CanonicalRecord]) -> Head:
        payload = ("\n".join(canonical_json(r) for r in records) + "\n").encode("utf-8")
        name = f"seg-{head.seq + 1:06d}-{os.urandom(4).hex()}.jsonl"
        tmp = self.records_dir / f".tmp-{name}"
        _write_durable(tmp, payload)
        self._crash("after_segment_tmp")
        os.replace(tmp, self.records_dir / name)
        _fsync_dir(self.records_dir)
        self._crash("after_segment_rename")
        digest = sha256_bytes(payload)
        entry = {"name": name, "sha256": digest, "count": len(records)}
        new_head = Head(head.seq + 1, (*head.segments, entry), _chain(head.chain, digest))
        self._write_head(new_head)
        return new_head

    def _write_head(self, head: Head) -> None:
        body = json.dumps({"format": HEAD_FORMAT, "seq": head.seq, "segments": list(head.segments),
                           "chain": head.chain}, sort_keys=True, indent=1).encode("utf-8")
        tmp = self.root / f".HEAD.{os.getpid()}.{os.urandom(4).hex()}.tmp"
        _write_durable(tmp, body)
        self._crash("after_head_tmp")
        os.replace(tmp, self.root / "HEAD.json")
        self._crash("after_head_rename")
        _fsync_dir(self.root)

    # ---------------------------------------------------------------- recovery and verification
    def recover(self) -> RecoveryReport:
        """Remove uncommitted tmp files and orphan segments, then finish any ledgered purge."""
        report = RecoveryReport()
        with self.writer_lock():
            self._remove_orphans(report)
            head = self.head()
            ledger = self.ledger_digests()
            if ledger:
                unfinished = {r.id for r in self._read_segments(head) if sha256_text(r.id) in ledger}
                if unfinished:
                    self._purge_locked(head, unfinished, write_ledger=False)
                    self._remove_orphans(report)
            committed = {s["name"] for s in self.head().segments}
            report.remaining_orphans = [p.name for p in self.records_dir.iterdir() if p.name not in committed]
        return report

    def _remove_orphans(self, report: RecoveryReport) -> None:
        committed = {s["name"] for s in self.head().segments}
        for path in [*self.records_dir.iterdir(), *self.root.glob(".HEAD.*.tmp")]:
            if path.name not in committed:
                path.unlink()
                report.removed.append(path.name)

    def verify(self) -> VerifyReport:
        """Full check for ``doctor``: segment hashes, chain, and every cross-record invariant."""
        problems: list[str] = []
        head = self.head()
        chain = GENESIS
        for segment in head.segments:
            chain = _chain(chain, segment["sha256"])
        count = 0
        try:
            self._segment_cache.clear()
            records = self._read_segments(head)
            count = len(records)
            RecordSet(records).validate()
        except (VaultIntegrityError, InvariantError, ValueError) as error:
            problems.append(str(error))
        if not problems and chain != head.chain and not self.ledger_digests():
            problems.append("hash chain does not match the committed segments")
        return VerifyReport(not problems, head.seq, count, tuple(problems))

    # ---------------------------------------------------------------- purge
    def purge(self, record_ids: set[str], expected_seq: int) -> DeletionReceipt:
        """Privacy purge: ledger the id digests first, then rewrite segments without the targets."""
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
        if kept:
            self._append_segment(Head(head.seq, (), head.chain), kept)
        else:
            self._write_head(Head(head.seq + 1, (), head.chain))
        for name in old:
            (self.records_dir / name).unlink(missing_ok=True)
        _fsync_dir(self.records_dir)
        self._segment_cache.clear()
        return DeletionReceipt(id=new_id("rcp"), schema_version=1, recorded_at=utc_now(), purge_id=new_id("rcp"),
                               terminal_state="complete_managed",
                               per_copy=(CopyResult(copy_class="canonical", result="deleted"),))

    @staticmethod
    def _unlink(record: CanonicalRecord, purged: set[str]) -> CanonicalRecord:
        updates: dict[str, list[str]] = {}
        for name in ("evidence_ids", "memory_ids", "derived_from", "contradicts", "supersedes"):
            links = getattr(record, name, None)
            if links and purged.intersection(links):
                updates[name] = [x for x in links if x not in purged]
        if not updates:
            return record
        raw = json.loads(canonical_json(record)) | updates
        try:
            return parse_record(raw)
        except ValueError as exc:
            raise InvariantError(f"purge would orphan {record.id}; purge it too") from exc

    def _append_ledger(self, record_ids: set[str]) -> None:
        lines = "".join(
            canonical_json(DeletionLedgerEntry(id=new_id("led"), recorded_at=utc_now(),
                                               target_digest=sha256_text(rid))) + "\n"
            for rid in sorted(record_ids)
        )
        with open(self.state_dir / "deletion-ledger.jsonl", "a", encoding="utf-8") as handle:
            handle.write(lines)
            handle.flush()
            _full_fsync(handle.fileno())

    def ledger_digests(self) -> set[str]:
        path = self.state_dir / "deletion-ledger.jsonl"
        if not path.exists():
            return set()
        return {json.loads(line)["target_digest"] for line in path.read_text(encoding="utf-8").splitlines()}

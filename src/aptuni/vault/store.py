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
import re
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aptuni.domain.ids import DIGEST_PATTERN, new_id, sha256_bytes, sha256_text
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
from aptuni.vault.locks import source_operations_lock

CRASH_POINTS = ("after_segment_tmp", "after_segment_rename", "after_head_tmp", "after_head_rename")
GENESIS = "0" * 64
READ_RETRIES = 50
HEAD_FORMAT = 2
SUPPORTED_HEAD_FORMATS = (1, HEAD_FORMAT)
SEGMENT_RE = re.compile(r"^seg-\d{6}-[0-9a-f]{8}\.jsonl$")
TMP_SEGMENT_RE = re.compile(r"^\.tmp-seg-\d{6}-[0-9a-f]{8}\.jsonl$")


class VaultDirNotEmptyError(FileExistsError):
    """``init`` refuses folders that already contain files (never adopt or clean user data)."""


class ConflictError(RuntimeError):
    """The Vault advanced since the caller read it (lost update prevented)."""


class VaultIntegrityError(RuntimeError):
    """A committed segment does not match HEAD (out-of-band edit or corruption)."""


@dataclass(frozen=True)
class Head:
    seq: int
    segments: tuple[dict[str, Any], ...]
    chain: str
    chain_base: str = GENESIS
    head_format: int = HEAD_FORMAT

    def chain_matches(self) -> bool:
        chain = self.chain_base
        for segment in self.segments:
            chain = _chain(chain, segment["sha256"])
        return chain == self.chain


@dataclass
class RecoveryReport:
    removed: list[str] = field(default_factory=list)
    remaining_orphans: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)  # foreign files: reported, never deleted


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


def _unlink_durable(path: Path) -> None:
    path.unlink(missing_ok=True)
    _fsync_dir(path.parent)


def _chain(previous: str, digest: str) -> str:
    return hashlib.sha256((previous + digest).encode("ascii")).hexdigest()


def _parse_head_value(data: dict[str, Any]) -> Head:
    """Parse an authenticated manifest without allowing bool-as-int or path-shaped names."""
    head_format = data.get("format")
    if type(head_format) is not int or head_format not in SUPPORTED_HEAD_FORMATS:
        raise VaultIntegrityError(f"unsupported HEAD format {head_format!r}")
    try:
        seq, segments, chain = data["seq"], data["segments"], data["chain"]
        base = data.get("chain_base", GENESIS)
        valid_scalars = type(seq) is int and seq >= 0 and isinstance(chain, str)
        valid_scalars = valid_scalars and re.fullmatch(r"[0-9a-f]{64}", chain) is not None
        valid_scalars = valid_scalars and isinstance(base, str)
        valid_scalars = valid_scalars and re.fullmatch(r"[0-9a-f]{64}", base) is not None
        if not valid_scalars or not isinstance(segments, list):
            raise ValueError
        names: set[str] = set()
        for segment in segments:
            name, digest, count = segment["name"], segment["sha256"], segment["count"]
            if (not isinstance(name, str) or not SEGMENT_RE.fullmatch(name) or name in names
                    or not isinstance(digest, str) or not re.fullmatch(DIGEST_PATTERN, digest)
                    or type(count) is not int or count < 0):
                raise ValueError
            names.add(name)
    except (KeyError, TypeError, ValueError) as error:
        raise VaultIntegrityError("HEAD contains invalid fields or segment entries") from error
    return Head(seq, tuple(segments), chain, base, head_format)


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
        if root.exists() and any(root.iterdir()):
            raise VaultDirNotEmptyError(f"{root} is not empty")
        (root / "records").mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        for private in (root, root / "records", state_dir):
            os.chmod(private, 0o700)
        vault = cls(root, state_dir)
        vault._write_head(Head(0, (), GENESIS, GENESIS))
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
        return _parse_head_value(data)

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

    def snapshot(self) -> tuple[int, RecordSet]:
        """A consistent (seq, records) pair: decisions based on it commit with that seq."""
        for _ in range(READ_RETRIES):
            head = self.head()
            try:
                return head.seq, RecordSet(self._read_segments(head))
            except FileNotFoundError:
                time.sleep(0.01)
        raise VaultIntegrityError("could not obtain a stable snapshot")

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
            ledger = self.ledger_digests()
            purged = [r.id for r in records if sha256_text(r.id) in ledger]
            if purged:
                raise InvariantError(f"purged ids cannot be committed again: {purged}")
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
        new_head = Head(head.seq + 1, (*head.segments, entry), _chain(head.chain, digest), head.chain_base)
        self._write_head(new_head)
        return new_head

    def _write_head(self, head: Head) -> None:
        body = json.dumps({"format": HEAD_FORMAT, "seq": head.seq, "segments": list(head.segments),
                           "chain": head.chain, "chain_base": head.chain_base},
                          sort_keys=True, indent=1).encode("utf-8")
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
        with source_operations_lock(self.state_dir), self.writer_lock():
            self._recover_restore_locked()
            self._migrate_head_format()
            self._remove_orphans(report)
            head = self.head()
            ledger = self.ledger_digests()
            if ledger:
                unfinished = {r.id for r in self._read_segments(head) if sha256_text(r.id) in ledger}
                if unfinished:
                    self._purge_locked(head, unfinished, write_ledger=False)
                    self._remove_orphans(report)
            committed = {s["name"] for s in self.head().segments}
            report.remaining_orphans = [p.name for p in self.records_dir.iterdir()
                                        if p.name not in committed and SEGMENT_RE.match(p.name)]
        return report

    def _legacy_purged_head(self, head: Head) -> bool:
        """True for a format-1 HEAD that a pre-``chain_base`` purge re-anchored.

        Format 1 recorded no ``chain_base``, and a purge under that code re-anchored ``chain`` onto
        the pre-purge value without writing it down, so the anchor cannot be derived from the HEAD.
        A mismatch with no purge in the ledger is not this artifact: that is corruption, and it stays
        a problem.
        """
        return head.head_format == 1 and not head.chain_matches() and bool(self.ledger_digests())

    def _migrate_head_format(self) -> None:
        """Bring a format-1 HEAD to the current format so its chain is verifiable from now on.

        An unpurged legacy HEAD is anchored at GENESIS and only needs the format stamp. A legacy
        purged HEAD has an unrecoverable anchor, so its recorded chain is preserved *as* the new
        anchor -- the same re-anchoring the current purge performs, except now it is written down.
        """
        head = self.head()
        if head.head_format == HEAD_FORMAT:
            return
        if head.chain_matches():
            self._write_head(Head(head.seq, head.segments, head.chain, head.chain_base))
            return
        if not self._legacy_purged_head(head):
            return  # genuine corruption; leave it for verify() to report
        chain = head.chain
        for segment in head.segments:
            chain = _chain(chain, segment["sha256"])
        self._write_head(Head(head.seq, head.segments, chain, head.chain))

    def _restore_journal_path(self) -> Path:
        return self.state_dir / "restore-intent.json"

    def _write_restore_journal(self, value: dict[str, Any]) -> None:
        path = self._restore_journal_path()
        body = (json.dumps(value, sort_keys=True, indent=1) + "\n").encode("utf-8")
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
        _write_durable(tmp, body)
        os.replace(tmp, path)
        _fsync_dir(path.parent)

    def _recover_restore_locked(self) -> None:
        path = self._restore_journal_path()
        if not path.exists():
            return
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("format") != 1:
                raise ValueError
            old_seq = value["old_seq"]
            old_chain = value["old_chain"]
            if type(old_seq) is not int or old_seq < 0 or not isinstance(old_chain, str):
                raise ValueError
            if re.fullmatch(r"[0-9a-f]{64}", old_chain) is None:
                raise ValueError
            old_segments = tuple(value["old_segments"])
            if (any(not isinstance(name, str) or not SEGMENT_RE.fullmatch(name) for name in old_segments)
                    or len(set(old_segments)) != len(old_segments)):
                raise ValueError
            raw_head = value["new_head"]
            new_head = _parse_head_value({"format": HEAD_FORMAT, **raw_head})
            chain = new_head.chain_base
            for segment in new_head.segments:
                chain = _chain(chain, segment["sha256"])
            if chain != new_head.chain:
                raise ValueError
            self._read_segments(new_head)
            current = self.head()
            if not ((current.seq == old_seq and current.chain == old_chain)
                    or (current.seq == new_head.seq and current.chain == new_head.chain)):
                raise ValueError
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise VaultIntegrityError("restore journal is invalid or does not match the live Vault") from error
        self._clear_source_state()
        if self.head().chain != new_head.chain:
            self._write_head(new_head)
        for name in old_segments:
            if isinstance(name, str) and SEGMENT_RE.fullmatch(name):
                (self.records_dir / name).unlink(missing_ok=True)
        _fsync_dir(self.records_dir)
        self._segment_cache.clear()
        _unlink_durable(path)

    def _remove_orphans(self, report: RecoveryReport) -> None:
        """Remove only this protocol's own leftovers; report anything else and leave it alone."""
        committed = {s["name"] for s in self.head().segments}
        for path in self.records_dir.iterdir():
            if path.name in committed:
                continue
            if path.is_file() and (SEGMENT_RE.match(path.name) or TMP_SEGMENT_RE.match(path.name)):
                path.unlink()
                report.removed.append(path.name)
            else:
                report.unexpected.append(path.name)
        for path in self.root.glob(".HEAD.*.tmp"):
            path.unlink()
            report.removed.append(path.name)

    def unexpected_files(self) -> list[str]:
        committed = {s["name"] for s in self.head().segments}
        return sorted(p.name for p in self.records_dir.iterdir()
                      if p.name not in committed and not SEGMENT_RE.match(p.name))

    def verify(self) -> VerifyReport:
        """Full check for ``doctor``: segment hashes, chain, and every cross-record invariant."""
        problems: list[str] = []
        head = self.head()
        chain = head.chain_base
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
        if not problems and chain != head.chain:
            problems.append("hash chain does not match the committed segments")
        problems.extend(f"unexpected file in records/ (left untouched): {name}" for name in self.unexpected_files())
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
            self._append_segment(Head(head.seq, (), head.chain, head.chain), kept)
        else:
            self._write_head(Head(head.seq + 1, (), head.chain, head.chain))
        for name in old:
            (self.records_dir / name).unlink(missing_ok=True)
        _fsync_dir(self.records_dir)
        self._segment_cache.clear()
        return DeletionReceipt(id=new_id("rcp"), schema_version=1, recorded_at=utc_now(), purge_id=new_id("rcp"),
                               terminal_state="complete_managed",
                               per_copy=(CopyResult(copy_class="canonical", result="deleted"),))

    def restore_from(self, backup: Path, expected_seq: int) -> Vault:
        """Atomically publish a verified backup as a new chain-linked generation.

        The live Vault is never removed. The replacement segment is durable before HEAD changes,
        deletion-ledger digests are reapplied before publication, and source replay state is dropped
        so it cannot contradict the restored canonical generation.
        """
        backup = backup.expanduser().resolve()
        root = self.root.resolve()
        if backup == root or backup in root.parents or root in backup.parents:
            raise VaultIntegrityError("restore backup must be separate from the live Vault")
        if (backup / "HEAD.json").is_symlink() or (backup / "records").is_symlink():
            raise VaultIntegrityError("restore backup cannot contain symlinked Vault control paths")
        backup_vault = Vault(backup, self.state_dir)
        backup_head = backup_vault.head()
        if any((backup / "records" / segment["name"]).is_symlink() for segment in backup_head.segments):
            raise VaultIntegrityError("restore backup cannot contain symlinked committed segments")
        restored_records = backup_vault._read_segments(backup_head)
        RecordSet(restored_records).validate()
        backup_chain = backup_head.chain_base
        for segment in backup_head.segments:
            backup_chain = _chain(backup_chain, segment["sha256"])
        if backup_chain != backup_head.chain and not self._legacy_purged_head(backup_head):
            raise VaultIntegrityError("restore backup hash chain does not match its committed segments")

        with source_operations_lock(self.state_dir), self.writer_lock():
            live_head = self.head()
            if live_head.seq != expected_seq:
                raise ConflictError(f"expected seq {expected_seq}, vault is at {live_head.seq}")
            ledger = self.ledger_digests()
            doomed = {record.id for record in restored_records if sha256_text(record.id) in ledger}
            kept = [self._unlink(record, doomed) for record in restored_records if record.id not in doomed]
            RecordSet(kept).validate()
            old = [segment["name"] for segment in live_head.segments]
            if kept:
                payload = ("\n".join(canonical_json(record) for record in kept) + "\n").encode("utf-8")
                name = f"seg-{live_head.seq + 1:06d}-{os.urandom(4).hex()}.jsonl"
                tmp = self.records_dir / f".tmp-{name}"
                _write_durable(tmp, payload)
                self._crash("after_segment_tmp")
                os.replace(tmp, self.records_dir / name)
                _fsync_dir(self.records_dir)
                self._crash("after_segment_rename")
                digest = sha256_bytes(payload)
                new_head = Head(live_head.seq + 1, ({"name": name, "sha256": digest, "count": len(kept)},),
                                _chain(live_head.chain, digest), live_head.chain)
            else:
                new_head = Head(live_head.seq + 1, (), live_head.chain, live_head.chain)
            self._write_restore_journal({
                "format": 1, "old_seq": live_head.seq, "old_chain": live_head.chain,
                "old_segments": old,
                "new_head": {"seq": new_head.seq, "segments": list(new_head.segments),
                             "chain": new_head.chain, "chain_base": new_head.chain_base},
            })
            self._recover_restore_locked()
        return self

    def _clear_source_state(self) -> None:
        sources = self.root / "sources"
        if sources.is_symlink():
            raise VaultIntegrityError("source replay state directory is a symlink")
        if not sources.exists():
            return
        for path in sources.iterdir():
            if path.is_dir() and not path.is_symlink():
                raise VaultIntegrityError("source replay state contains an unexpected directory")
            path.unlink()
        _fsync_dir(sources)

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
        path = self.state_dir / "deletion-ledger.jsonl"
        _drop_torn_tail(path)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)
            handle.flush()
            _full_fsync(handle.fileno())

    def ledger_digests(self) -> set[str]:
        path = self.state_dir / "deletion-ledger.jsonl"
        if not path.exists():
            return set()
        digests: set[str] = set()
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            try:
                digests.add(json.loads(line)["target_digest"])
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                if number == len(lines):
                    break  # torn tail from a crash mid-append; the purge itself never completed
                raise VaultIntegrityError(f"deletion ledger line {number} is malformed") from error
        return digests


def _drop_torn_tail(path: Path) -> None:
    """Cut an interrupted final append back to the last newline so it cannot merge with new entries.

    Called under the writer lock before every ledger append (review 19 N1). Complete lines are
    never touched; only the fragment after the final newline is removed.
    """
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return
    if not data or data.endswith(b"\n"):
        return
    os.truncate(path, data.rfind(b"\n") + 1)
    fd = os.open(path, os.O_RDONLY)
    try:
        _full_fsync(fd)
    finally:
        os.close(fd)

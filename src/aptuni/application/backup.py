"""The owner's restorable backup format: canonical segments plus a self-describing manifest.

`aptuni export` writes a readable current-view copy and says in its own output that it is not a
restorable backup. This module writes the other thing: a byte-exact copy of the canonical Vault that
`restore.py` can publish back.

The manifest is why a backup is a format rather than a folder copy. It carries the source sequence,
the hash chain, every segment digest, the record count, **and the deletion-ledger digests as of
creation**. That last field is the fix for KI-021: the ledger that enforces "purged stays purged"
lives in the state directory, so a Vault copy alone loses it, and restoring such a copy on a machine
with no ledger re-admits a record the owner deleted. Carrying the digests in the backup makes
deletion travel with the data. The digests are one-way hashes of record ids, so the manifest stays
content-free.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aptuni.application.confirmations import fsync_dir, preview_digest, write_private_json
from aptuni.application.errors import AptuniError
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.temporal import utc_now
from aptuni.vault.fsgate import UnsupportedFilesystemError, check_vault_filesystem
from aptuni.vault.store import Vault, VaultIntegrityError

MANIFEST_NAME = "aptuni-backup.json"
MANIFEST_SCHEMA = 1
UNREADABLE = (OSError, json.JSONDecodeError, VaultIntegrityError, InvariantError, UnsupportedFilesystemError,
              ValueError, KeyError, TypeError)


@dataclass(frozen=True)
class BackupSummary:
    """Content-free description of one backup directory; safe to print and to log."""

    path: str
    ok: bool
    schema_version: int
    created_at: str
    vault_seq: int
    record_count: int
    segment_count: int
    deletion_digest_count: int
    problems: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MAX_TIMESTAMP = 40


def _timestamp(value: Any) -> str:
    """A bounded ISO-8601 instant. The manifest's holder controls this text (Review 35 B4)."""
    text = str(value)
    if len(text) > MAX_TIMESTAMP:
        raise ValueError("manifest timestamp is too long")
    datetime.fromisoformat(text)  # raises ValueError for anything that is not a timestamp
    return text


def _manifest_fields(value: dict[str, Any]) -> dict[str, Any]:
    """Exactly the fields the manifest digest covers, in a stable shape."""
    return {
        "schema_version": int(value["schema_version"]),
        "created_at": _timestamp(value["created_at"]),
        "vault_seq": int(value["vault_seq"]),
        "chain": str(value["chain"]),
        "chain_base": str(value["chain_base"]),
        "segments": [{"name": str(s["name"]), "sha256": str(s["sha256"]), "count": int(s["count"])}
                     for s in value["segments"]],
        "record_count": int(value["record_count"]),
        "deletion_digests": sorted(str(item) for item in value["deletion_digests"]),
    }


def _digest_of(fields: dict[str, Any]) -> str:
    return preview_digest(fields)


def _unverified(message: str) -> AptuniError:
    return AptuniError("backup_unverified", message)


def read_manifest(path: Path) -> dict[str, Any]:
    """Load and self-check the manifest. Raises `backup_unverified` for anything unusable."""
    manifest_path = path / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise _unverified(
            f"{path} has no Aptuni backup manifest, so it is not a backup Aptuni can restore. "
            "A folder copied by hand is not a supported restore input; use `aptuni backup create`."
        )
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        fields = _manifest_fields(raw)
        recorded = str(raw["digest"])
    except UNREADABLE as error:
        raise _unverified(f"The backup manifest in {path} is malformed: {error}") from error
    if fields["schema_version"] != MANIFEST_SCHEMA:
        raise _unverified(
            f"The backup manifest says format {fields['schema_version']}; this Aptuni writes "
            f"{MANIFEST_SCHEMA}. Restore it with the version that wrote it."
        )
    if recorded != _digest_of(fields):
        raise _unverified(f"The backup manifest in {path} was changed after it was written.")
    return {**fields, "digest": recorded}


def _check_against_disk(path: Path, manifest: dict[str, Any]) -> list[str]:
    """Every way the bytes on disk can disagree with what the manifest promises."""
    problems: list[str] = []
    records_dir = path / "records"
    if not records_dir.is_dir() or records_dir.is_symlink():
        return [f"{path} has no readable records/ directory"]

    for control in ("HEAD.json", "records", MANIFEST_NAME):
        if (path / control).is_symlink():
            return [f"{control} in {path} is a symlink, so the backup cannot be trusted"]

    expected = {str(segment["name"]) for segment in manifest["segments"]}
    problems.extend(f"records/{item.name} is a symlink, so the backup cannot be trusted"
                    for item in sorted(records_dir.iterdir()) if item.is_symlink())
    present = {item.name for item in records_dir.iterdir() if not item.name.startswith(".")}
    for extra in sorted(present - expected):
        problems.append(f"records/{extra} is not listed in the manifest")

    try:
        vault = Vault(path, path)  # segment reads only; nothing is written to a backup
        head = vault.head()
    except UNREADABLE as error:
        return [f"{path} has no readable HEAD.json: {error}"]
    if head.seq != manifest["vault_seq"] or head.chain != manifest["chain"]:
        problems.append("HEAD.json and the manifest describe different generations")
    if [dict(item) for item in head.segments] != manifest["segments"]:
        problems.append("HEAD.json and the manifest list different segments")

    try:
        records = vault._read_segments(head)  # segment digests are this module's job
        RecordSet(records).validate()
    except UNREADABLE as error:
        return [*problems, f"the backed-up records do not verify: {error}"]
    if len(records) != manifest["record_count"]:
        problems.append(f"the manifest says {manifest['record_count']} records; the segments hold {len(records)}")

    report = vault.verify()
    problems.extend(report.problems)
    if set(vault.ledger_digests()) != set(manifest["deletion_digests"]):
        problems.append("the backed-up deletion ledger and the manifest record different deletions")
    return problems


def verify_backup(path: Path) -> BackupSummary:
    """Check a backup end to end without touching any live Vault. Never raises for a bad backup."""
    path = path.expanduser()
    try:
        manifest = read_manifest(path)
    except AptuniError as error:
        return BackupSummary(str(path), False, 0, "", -1, -1, -1, -1, (error.message,))
    problems = tuple(_check_against_disk(path, manifest))
    return BackupSummary(
        str(path), not problems, MANIFEST_SCHEMA, manifest["created_at"], manifest["vault_seq"],
        manifest["record_count"], len(manifest["segments"]), len(manifest["deletion_digests"]), problems,
    )


def list_backups(directory: Path) -> tuple[BackupSummary, ...]:
    """Every immediate child that looks like a backup, oldest generation first."""
    directory = directory.expanduser()
    if not directory.is_dir():
        raise AptuniError("backup_directory_missing", f"No such directory: {directory}")
    found = [verify_backup(child) for child in sorted(directory.iterdir())
             if child.is_dir() and not child.is_symlink() and (child / MANIFEST_NAME).is_file()]
    return tuple(sorted(found, key=lambda item: (item.vault_seq, item.path)))


def _validate_destination(destination: Path, vault_root: Path) -> None:
    resolved = destination.expanduser()
    root = vault_root.resolve()
    parent = resolved.parent.resolve() if resolved.parent.exists() else resolved.parent
    candidate = resolved.resolve() if resolved.exists() else parent / resolved.name
    if candidate == root or root in candidate.parents or candidate in root.parents:
        raise AptuniError(
            "invalid_backup_destination",
            "A backup must live outside your Vault, and never in a folder that contains it. "
            "Choose a separate location, ideally on separate storage.",
        )
    if resolved.is_symlink():
        raise AptuniError("invalid_backup_destination", f"{destination} is a symlink.")
    if resolved.exists() and any(resolved.iterdir()):
        raise AptuniError(
            "invalid_backup_destination",
            f"{destination} already has files in it. Aptuni never overwrites a folder you own; "
            "choose an empty or new location.",
        )
    probe = resolved if resolved.is_dir() else resolved.parent
    try:
        check_vault_filesystem(probe)
    except UnsupportedFilesystemError as error:
        raise AptuniError(
            "invalid_backup_destination",
            f"Aptuni will not write a backup to {destination} ({error}). A backup is a complete "
            "unencrypted copy of your records, so Aptuni only writes one where it can verify it and "
            "where it will not be uploaded for you. Choose local storage that is not a synchronized "
            "folder.",
        ) from error


def _copy_segment(source: Path, target: Path) -> None:
    """Byte-exact copy at mode 0600, durable before the manifest names it."""
    shutil.copyfile(source, target)
    os.chmod(target, 0o600)
    descriptor = os.open(target, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create_backup(vault: Vault, state_dir: Path, destination: Path) -> BackupSummary:
    """Write a verified backup, or leave nothing behind.

    The copy is taken under the writer lock so the segments, HEAD and ledger describe one generation.
    """
    _validate_destination(destination, vault.root)
    destination = destination.expanduser()
    existed = destination.exists()
    written: list[Path] = []
    try:
        with vault.writer_lock():
            head = vault.head()
            digests = sorted(vault.ledger_digests())
            destination.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(destination, 0o700)
            records_dir = destination / "records"
            records_dir.mkdir(exist_ok=True, mode=0o700)
            os.chmod(records_dir, 0o700)
            count = 0
            for segment in head.segments:
                target = records_dir / str(segment["name"])
                _copy_segment(vault.records_dir / str(segment["name"]), target)
                written.append(target)
                count += int(segment["count"])
            fsync_dir(records_dir)
            head_body = (vault.root / "HEAD.json").read_bytes()
            write_private_json(destination / "HEAD.json", json.loads(head_body))
            written.append(destination / "HEAD.json")
            if vault.ledger_path.is_file():
                # The ledger is part of the Vault (ADR-0016), so deletion travels with the backup.
                _copy_segment(vault.ledger_path, destination / vault.ledger_path.name)
                written.append(destination / vault.ledger_path.name)
            fields = _manifest_fields({
                "schema_version": MANIFEST_SCHEMA,
                "created_at": utc_now().isoformat(),
                "vault_seq": head.seq,
                "chain": head.chain,
                "chain_base": head.chain_base,
                "segments": [dict(item) for item in head.segments],
                "record_count": count,
                "deletion_digests": digests,
            })
            write_private_json(destination / MANIFEST_NAME, {**fields, "digest": _digest_of(fields)})
            written.append(destination / MANIFEST_NAME)
        summary = verify_backup(destination)
    except AptuniError:
        _clean_up(destination, written, existed)
        raise
    except UNREADABLE as error:
        _clean_up(destination, written, existed)
        raise AptuniError("backup_write_failed", f"The backup could not be written: {error}") from error

    if not summary.ok:
        _clean_up(destination, written, existed)
        raise AptuniError(
            "backup_write_failed",
            "The backup did not verify immediately after it was written, so it was removed: "
            + "; ".join(summary.problems),
        )
    return summary


def _clean_up(destination: Path, written: list[Path], existed: bool) -> None:
    """Remove exactly what this call created, so a failure never leaves an unverifiable backup.

    A folder the owner made themselves is emptied of Aptuni's files but kept, so it stays usable for
    the next attempt (Review 35 N5).
    """
    if not existed:
        shutil.rmtree(destination, ignore_errors=True)
        return
    for path in reversed(written):
        with contextlib.suppress(OSError):
            path.unlink()
    with contextlib.suppress(OSError):
        (destination / "records").rmdir()

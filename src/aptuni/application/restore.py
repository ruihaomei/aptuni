"""Digest-bound restore: publish a verified backup as the next canonical generation (ADR-0016).

`Vault.restore_from` already does the dangerous part atomically — it stages the replacement, journals
it, and never removes the live Vault before the new HEAD is durable. This module owns the decision in
front of it: verify the backup completely, show the owner exactly what changes, bind one expiring
single-use confirmation to that text, and seed the live deletion ledger from the backup manifest so a
purge recorded on *either* side survives the restore (KI-021).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from aptuni.application import backup as backup_api
from aptuni.application.confirmations import (
    action_lock,
    new_action_id,
    new_nonce,
    preview_digest,
    unlink_durable,
    validate_action_id,
    write_private_json,
)
from aptuni.application.errors import AptuniError
from aptuni.domain.ids import sha256_text
from aptuni.domain.invariants import InvariantError
from aptuni.domain.temporal import utc_now
from aptuni.retrieval.sqlite import SqliteProjection
from aptuni.vault.store import ConflictError, Vault, VaultIntegrityError

RESTORE_TTL = timedelta(minutes=10)
FAMILY = "backup"
UNREADABLE = (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)


@dataclass(frozen=True)
class RestorePreview:
    """Exactly what the owner approves. Every field is shown before the confirmation is accepted."""

    schema_version: int
    action_id: str
    backup_path: str
    backup_created_at: str
    backup_seq: int
    backup_record_count: int
    live_seq: int
    live_record_count: int
    ledger_drop_count: int
    discarded_record_count: int
    new_ledger_digest_count: int
    clears_source_state: bool
    invalidates_projection: bool
    nonce_id: str
    expires_at: str
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RestoreReceipt:
    action_id: str
    restored_from_seq: int
    published_seq: int
    restored_record_count: int
    ledger_dropped_count: int
    discarded_record_count: int
    cleared_source_state: bool
    invalidated_projection: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def pending_path(state_dir: Path, action_id: str) -> Path:
    return state_dir / FAMILY / "pending" / f"{action_id}.json"


def _fields_of(preview: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in preview.items() if key != "digest"}


def _validate(action_id: str) -> None:
    validate_action_id(action_id, "invalid_restore_action_id",
                       "An exact core-generated restore action ID is required.")


def create_restore_preview(vault: Vault, state_dir: Path, path: Path) -> RestorePreview:
    """Verify the backup completely, then record one single-use preview. Changes nothing."""
    summary = backup_api.verify_backup(path)
    if not summary.ok:
        raise AptuniError(
            "backup_unverified",
            "This backup does not verify, so Aptuni will not restore from it: "
            + "; ".join(summary.problems),
        )
    manifest = backup_api.read_manifest(path.expanduser())
    live_seq, live_records = vault.snapshot()

    # Every precondition the restore itself enforces, checked here so the preview can never describe
    # a restore that will be refused (Review 35 B5).
    try:
        restored = vault.check_restore_source(path)
    except (VaultIntegrityError, InvariantError, OSError, ValueError) as error:
        raise AptuniError(
            "backup_unverified",
            f"This backup cannot be restored into your Vault: {error}",
        ) from error

    # What the union of both ledgers will drop, and what the live generation loses, so both counts are
    # honest before the owner confirms rather than a surprise in the receipt.
    ledger = vault.ledger_digests() | set(manifest["deletion_digests"])
    dropped = sum(1 for record in restored if sha256_text(record.id) in ledger)
    surviving = {record.id for record in restored if sha256_text(record.id) not in ledger}
    discarded = sum(1 for record in live_records.records() if record.id not in surviving)

    fields: dict[str, Any] = {
        "schema_version": 1,
        "action_id": new_action_id(),
        "backup_path": str(path.expanduser()),
        "backup_created_at": str(manifest["created_at"]),
        "backup_seq": int(manifest["vault_seq"]),
        "backup_record_count": int(manifest["record_count"]),
        "live_seq": live_seq,
        "live_record_count": len(live_records),
        "ledger_drop_count": dropped,
        "discarded_record_count": discarded,
        "new_ledger_digest_count": len(set(manifest["deletion_digests"]) - vault.ledger_digests()),
        "clears_source_state": True,
        "invalidates_projection": True,
        "nonce_id": new_nonce(),
        "expires_at": (utc_now() + RESTORE_TTL).isoformat(),
    }
    preview = RestorePreview(**fields, digest=preview_digest(fields))
    with action_lock(state_dir, FAMILY):
        write_private_json(pending_path(state_dir, preview.action_id), preview.to_dict())
    return preview


def load_restore_preview(state_dir: Path, action_id: str) -> RestorePreview:
    _validate(action_id)
    path = pending_path(state_dir, action_id)
    if not path.is_file():
        raise AptuniError("restore_action_not_found", "No pending restore with that id. Preview it again.")
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        fields = _fields_of(stored)
        recorded = str(stored["digest"])
        if int(fields["schema_version"]) != 1 or str(fields["action_id"]) != action_id:
            raise ValueError("action mismatch")
        if recorded != preview_digest(fields):
            raise AptuniError("restore_action_invalid",
                              "The pending restore was changed; preview it again.")
        return RestorePreview(**fields, digest=recorded)
    except AptuniError:
        raise
    except UNREADABLE as error:
        raise AptuniError("restore_action_invalid",
                          "The pending restore is invalid; preview it again.") from error


def pending_restores(state_dir: Path) -> tuple[RestorePreview, ...]:
    directory = state_dir / FAMILY / "pending"
    if not directory.is_dir():
        return ()
    found = []
    for child in sorted(directory.iterdir()):
        if child.suffix != ".json":
            continue
        try:
            found.append(load_restore_preview(state_dir, child.stem))
        except AptuniError:
            continue
    return tuple(found)


def cancel_restore(state_dir: Path, action_id: str) -> None:
    """Drop a pending preview. Nothing canonical has changed, so there is nothing to roll back."""
    _validate(action_id)
    with action_lock(state_dir, FAMILY):
        path = pending_path(state_dir, action_id)
        if not path.is_file():
            raise AptuniError("restore_action_not_found", "No pending restore with that id.")
        unlink_durable(path)


def confirm_restore(vault: Vault, state_dir: Path, action_id: str, confirmed_digest: str) -> RestoreReceipt:
    """Publish the backup as the next generation, after the exact preview is confirmed."""
    _validate(action_id)
    with action_lock(state_dir, FAMILY):
        preview = load_restore_preview(state_dir, action_id)
        if confirmed_digest != preview.digest:
            raise AptuniError(
                "restore_digest_mismatch",
                "That is not the digest of the restore you were shown. Preview it again and confirm "
                "the exact plan.",
            )
        if utc_now() > _expiry(preview):
            unlink_durable(pending_path(state_dir, action_id))
            raise AptuniError("restore_action_expired",
                              "This restore preview expired. Preview it again to see current effects.")

        path = Path(preview.backup_path)
        summary = backup_api.verify_backup(path)
        if not summary.ok or summary.vault_seq != preview.backup_seq:
            raise AptuniError(
                "backup_unverified",
                "The backup changed since the preview, so the restore was refused: "
                + "; ".join(summary.problems or ("its generation no longer matches the preview",)),
            )
        manifest = backup_api.read_manifest(path)
        if vault.head().seq != preview.live_seq:
            raise AptuniError(
                "restore_confirmation_stale",
                "Your Vault changed after this preview was made, so the restore would destroy records "
                "the preview never showed you. Preview the restore again.",
            )

        # Deletion travels with the backup. The digests are applied inside `restore_from`'s own
        # critical section, after its preconditions and its sequence gate, so a refused restore can
        # never leave them behind (Review 35 B5).
        try:
            vault.restore_from(path, preview.live_seq,
                               frozenset(str(digest) for digest in manifest["deletion_digests"]))
        except ConflictError as error:
            raise AptuniError(
                "restore_confirmation_stale",
                "Your Vault changed while the restore was starting. Nothing was restored; preview it "
                "again.",
            ) from error
        published = vault.head()

        SqliteProjection(state_dir).delete()
        unlink_durable(pending_path(state_dir, action_id))
        receipt = RestoreReceipt(
            action_id=action_id,
            restored_from_seq=preview.backup_seq,
            published_seq=published.seq,
            restored_record_count=sum(int(segment["count"]) for segment in published.segments),
            ledger_dropped_count=preview.backup_record_count
            - sum(int(segment["count"]) for segment in published.segments),
            discarded_record_count=preview.discarded_record_count,
            cleared_source_state=True,
            invalidated_projection=True,
        )
        write_private_json(state_dir / FAMILY / "receipts" / f"{action_id}.json", {
            "schema_version": 1, "action_digest": preview.digest, "receipt": receipt.to_dict(),
        })
        return receipt


def _expiry(preview: RestorePreview) -> datetime:
    try:
        return datetime.fromisoformat(preview.expires_at)
    except ValueError as error:
        raise AptuniError("restore_action_invalid", "The pending restore has no usable expiry.") from error

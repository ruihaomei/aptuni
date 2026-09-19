"""Content-free owner inventory of Aptuni-managed and externally controlled copies (ADR-0010)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aptuni.domain.invariants import RecordSet


@dataclass(frozen=True)
class InventoryCopy:
    id: str
    copy_class: str
    location: str
    present: bool | None
    bytes: int | None
    modified_at: str | None
    managed: bool
    retention: str
    backup_inclusion: str
    deletion_control: str
    purpose: str


@dataclass(frozen=True)
class PrivacyInventory:
    schema_version: int
    vault_seq: int
    generated_at: str
    copies: tuple[InventoryCopy, ...]
    actions: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "vault_seq": self.vault_seq,
            "generated_at": self.generated_at,
            "copies": [asdict(item) for item in self.copies],
            "actions": dict(self.actions),
        }


def _regular_files(path: Path) -> list[os.stat_result]:
    """Stat only regular files beneath a core-owned path; never follow symlinks."""
    if not path.exists() or path.is_symlink():
        return []
    if path.is_file():
        return [path.stat(follow_symlinks=False)]
    found: list[os.stat_result] = []
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_file(follow_symlinks=False):
                    found.append(entry.stat(follow_symlinks=False))
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
            except OSError:
                continue
    return found


def _measure(*paths: Path) -> tuple[bool, int, str | None]:
    present = any(path.exists() and not path.is_symlink() for path in paths)
    stats = [info for path in paths for info in _regular_files(path)]
    latest = max((info.st_mtime for info in stats), default=None)
    modified = datetime.fromtimestamp(latest, UTC).isoformat() if latest is not None else None
    return present, sum(info.st_size for info in stats), modified


def _managed_copy(copy_id: str, copy_class: str, path: Path, retention: str, backup: str,
                  deletion: str, purpose: str, *extra_paths: Path) -> InventoryCopy:
    present, size, modified = _measure(path, *extra_paths)
    return InventoryCopy(copy_id, copy_class, str(path), present, size, modified, True, retention, backup,
                         deletion, purpose)


def _grant_external_copies(grants: Path) -> list[InventoryCopy]:
    copies: list[InventoryCopy] = []
    if not grants.is_dir():
        return copies
    for path in sorted(grants.glob("grant-*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            grant_id = str(value["grant_id"])
            host = str(value["host"])
            destination = str(value["destination"])
            retention = str(value["retention"])
            if path.name != f"{grant_id}.json" or host not in {"claude", "codex"}:
                raise ValueError
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            copies.append(InventoryCopy(
                f"host_external_unknown:{path.stem}", "host_transcript_cache", "unknown", None, None, None,
                False, "externally_controlled_unknown", "external_provider_policy",
                "externally_controlled_unknown", "a malformed grant may already have released personal context",
            ))
            continue  # never echo malformed grant content
        copies.append(InventoryCopy(
            f"host_external:{grant_id}", "host_transcript_cache", destination, None, None, None, False,
            retention, "external_provider_policy", "externally_controlled_unknown",
            f"personal context released to the configured {host} host/model",
        ))
    return copies


def build_privacy_inventory(vault_root: Path, state_dir: Path, seq: int, records: RecordSet) -> PrivacyInventory:
    """Build one content-free snapshot; original sources are named but never opened or statted."""
    canonical_present, canonical_bytes, canonical_modified = _measure(vault_root / "HEAD.json",
                                                                       vault_root / "records")
    copies = [
        InventoryCopy("canonical_vault", "canonical", str(vault_root), canonical_present, canonical_bytes,
                      canonical_modified, True, "canonical", "user_environment",
                      "managed_purge_with_deletion_ledger", "Profile, Memory, Evidence and history"),
        _managed_copy("source_state", "source_minimized", vault_root / "sources", "source_minimized",
                      "included_with_vault", "managed_unlink_or_purge", "incremental source identity and replay"),
        _managed_copy("retrieval_projection", "derived", state_dir / "projections" / "retrieval.sqlite", "derived",
                      "excluded", "delete_and_rebuild", "local search acceleration"),
        _managed_copy("adapter_grants", "grant", state_dir / "adapters" / "grants", "until_revoked", "excluded",
                      "managed_revoke", "host/module/scope egress authorization"),
        _managed_copy("adapter_bundles", "configuration", state_dir / "adapters" / "bundles", "until_uninstall",
                      "excluded", "managed_uninstall", "generated host configuration"),
        _managed_copy("pending_actions", "temporary", state_dir / "adapters" / "pending", "until_applied_or_expired",
                      "excluded", "managed_cleanup", "unapplied adapter previews"),
        _managed_copy("memory_confirmations", "temporary", state_dir / "memory-confirmations", "ten_minutes",
                      "excluded", "managed_expiry_or_cancel", "single-use owner confirmation previews"),
        _managed_copy("deletion_ledger", "deletion_ledger", state_dir / "deletion-ledger.jsonl",
                      "irreversible_identifier_digests", "excluded", "retained_to_prevent_resurrection",
                      "content-free purge history"),
        InventoryCopy("profile_exports", "unmanaged_export", "untracked", None, None, None, False,
                      "user_controlled", "user_environment", "user_must_delete", "readable Profile copies"),
    ]
    for source in sorted((r for r in records.records() if r.record_type == "source_config"), key=lambda r: r.id):
        copies.append(InventoryCopy(
            f"source_original:{source.id}", "source_original", source.roots[0], None, None, None, False,
            "source_owner_policy", "source_owner_policy", "never_deleted_by_aptuni",
            f"approved read-only {source.source_type} source",
        ))
    copies.extend(_grant_external_copies(state_dir / "adapters" / "grants"))
    actions = {
        "unlink_source": "remove Aptuni source configuration/state; never delete the original source",
        "forget": "revoke visibility; keep canonical audit history",
        "purge": "remove selected managed content and derived copies; external host copies require user action",
        "uninstall": "remove Aptuni state/bundles; keep the Vault, original sources, exports and external host copies",
    }
    return PrivacyInventory(1, seq, datetime.now(UTC).isoformat(), tuple(copies), actions)

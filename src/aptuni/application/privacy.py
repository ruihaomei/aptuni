"""Content-free owner inventory of Aptuni-managed and externally controlled copies (ADR-0010)."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aptuni.application.confirmations import ACTION_RE, new_action_id, new_nonce
from aptuni.application.confirmations import action_lock as _action_lock
from aptuni.application.confirmations import preview_digest as _preview_digest
from aptuni.application.confirmations import unlink_durable as _unlink_durable
from aptuni.application.confirmations import write_private_json as _write_private_json
from aptuni.application.errors import AptuniError
from aptuni.domain.ids import ID_PATTERN, new_id, sha256_text
from aptuni.domain.invariants import InvariantError, RecordSet
from aptuni.domain.records import CopyResult, DeletionReceipt
from aptuni.domain.temporal import utc_now
from aptuni.retrieval.sqlite import SqliteProjection
from aptuni.vault.locks import source_operations_lock
from aptuni.vault.store import ConflictError, Vault

PURGE_TTL = timedelta(minutes=10)
PURGEABLE_TYPES = frozenset({"fact", "evidence", "observation", "candidate_memory", "memory", "source_config"})


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


@dataclass(frozen=True)
class PurgePreview:
    schema_version: int
    action_id: str
    requested_record_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    vault_seq: int
    policy_epoch: int
    nonce_id: str
    expires_at: str
    copy_effects: tuple[str, ...]
    managed_copy_ids: tuple[str, ...]
    external_copies: tuple[dict[str, str], ...]
    irreversible: bool
    external_action_needed: bool
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _preview_from_dict(value: dict[str, Any]) -> PurgePreview:
    try:
        schema_version = int(value["schema_version"])
        action_id = str(value["action_id"])
        requested = tuple(str(item) for item in value["requested_record_ids"])
        record_ids = tuple(str(item) for item in value["record_ids"])
        source_ids = tuple(str(item) for item in value["source_ids"])
        vault_seq = int(value["vault_seq"])
        policy_epoch = int(value["policy_epoch"])
        nonce_id = str(value["nonce_id"])
        expires_at = str(value["expires_at"])
        effects = tuple(str(item) for item in value["copy_effects"])
        managed_copy_ids = tuple(str(item) for item in value["managed_copy_ids"])
        raw_external = value["external_copies"]
        if not isinstance(raw_external, list):
            raise TypeError
        external_copies = tuple({str(key): str(item[key]) for key in item} for item in raw_external)
        irreversible = value["irreversible"] is True
        external = value["external_action_needed"] is True
        digest = str(value["digest"])
    except (KeyError, TypeError, ValueError) as error:
        message = "The pending privacy action is invalid; preview it again."
        raise AptuniError("privacy_action_invalid", message) from error
    fields = {
        "schema_version": schema_version, "action_id": action_id, "requested_record_ids": requested,
        "record_ids": record_ids, "source_ids": source_ids, "vault_seq": vault_seq,
        "policy_epoch": policy_epoch, "nonce_id": nonce_id, "expires_at": expires_at,
        "copy_effects": effects, "managed_copy_ids": managed_copy_ids, "external_copies": external_copies,
        "irreversible": irreversible, "external_action_needed": external,
    }
    if schema_version != 1 or not ACTION_RE.fullmatch(action_id):
        raise AptuniError("privacy_action_invalid", "The pending privacy action is invalid; preview it again.")
    if digest != _preview_digest(fields):
        raise AptuniError("privacy_action_invalid", "The pending privacy action is invalid; preview it again.")
    return PurgePreview(schema_version, action_id, requested, record_ids, source_ids, vault_seq,
                        policy_epoch, nonce_id, expires_at, effects, managed_copy_ids, external_copies,
                        irreversible, external, digest)


def _validate_requested(by_id: dict[str, Any], requested: tuple[str, ...]) -> None:
    if not requested or len(set(requested)) != len(requested):
        raise AptuniError("invalid_purge_scope", "Choose one or more unique exact record IDs.")
    for record_id in requested:
        if not re.fullmatch(ID_PATTERN, record_id) or record_id not in by_id:
            raise AptuniError("record_not_found", f"No exact canonical record with id {record_id}.")
        if by_id[record_id].record_type not in PURGEABLE_TYPES:
            raise AptuniError("record_not_purgeable", "Control and audit records cannot be selected directly.")


def _add_source_scope(by_id: dict[str, Any], selected: set[str], source_ids: set[str]) -> bool:
    for record_id in tuple(selected):
        record = by_id[record_id]
        if record.record_type == "source_config":
            source_ids.add(record.id)
        if record.record_type == "evidence" and record.provenance.source_id:
            source_ids.add(record.provenance.source_id)
    additions = {
        record.id for record in by_id.values()
        if (record.record_type == "source_config" and record.id in source_ids)
        or (record.record_type == "evidence" and record.provenance.source_id in source_ids)
    } - selected
    selected.update(additions)
    return bool(additions)


def _add_supersession_scope(by_id: dict[str, Any], selected: set[str]) -> bool:
    additions: set[str] = set()
    for record in by_id.values():
        links = set(getattr(record, "supersedes", ()))
        if record.id in selected or links.intersection(selected):
            additions.update(links | {record.id})
    additions -= selected
    selected.update(additions)
    return bool(additions)


def _required_by_selected(record: Any, selected: set[str]) -> bool:
    if record.record_type == "review_event":
        return bool(record.target_id in selected)
    if record.record_type == "memory":
        return bool(record.candidate_id in selected)
    if record.record_type == "candidate_memory":
        return bool(record.derived_from) and set(record.derived_from) <= selected
    if record.record_type == "fact" and record.trust != "user_declared":
        support = set(record.evidence_ids) | set(record.memory_ids)
        return bool(support) and support <= selected
    return False


def _expand_purge(records: RecordSet, requested: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    by_id = {record.id: record for record in records.records()}
    _validate_requested(by_id, requested)
    selected = set(requested)
    source_ids: set[str] = set()
    changed = True
    while changed:
        changed = _add_source_scope(by_id, selected, source_ids)
        changed = _add_supersession_scope(by_id, selected) or changed
        required = {record.id for record in by_id.values() if _required_by_selected(record, selected)} - selected
        selected.update(required)
        changed = bool(required) or changed
    return tuple(sorted(selected)), tuple(sorted(source_ids))


def _owned_child(root: Path, *parts: str) -> Path:
    """Resolve a fixed core-owned child without following any parent alias."""
    if root.is_symlink():
        raise OSError("owned_root_is_symlink")
    current = root
    for part in parts[:-1]:
        if part in {"", ".", ".."} or "/" in part:
            raise OSError("owned_path_invalid")
        current = current / part
        if current.is_symlink():
            raise OSError("owned_parent_is_symlink")
    final = current / parts[-1]
    if parts[-1] in {"", ".", ".."} or "/" in parts[-1]:
        raise OSError("owned_path_invalid")
    return final


def _direct_names(root: Path, *parts: str) -> tuple[str, ...]:
    path = _owned_child(root, *parts)
    if path.is_symlink():
        raise OSError("owned_directory_is_symlink")
    if not path.is_dir():
        return ()
    return tuple(sorted(entry.name for entry in os.scandir(path)))


def _grant_external_scope(state_dir: Path, names: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    copies: list[dict[str, str]] = []
    for name in names:
        path = _owned_child(state_dir, "adapters", "grants", name)
        try:
            if path.is_symlink():
                raise OSError("grant_is_symlink")
            value = json.loads(path.read_text(encoding="utf-8"))
            copies.append({
                "copy_id": "host_external:" + str(value["grant_id"]),
                "provider": str(value["host"]),
                "destination": str(value["destination"]),
                "data_class": "minimized_context; modules=" + ",".join(str(item) for item in value["modules"])
                + "; scopes=" + ",".join(str(item) for item in value["scopes"]),
            })
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            copies.append({"copy_id": f"host_external_unknown:{name}", "provider": "unknown",
                           "destination": "unknown", "data_class": "personal_context_unknown"})
    return tuple(copies)


def _snapshot_copy_scope(
    vault_root: Path, state_dir: Path, source_ids: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    tokens: list[str] = []
    for source_id in source_ids:
        for suffix, label in ((".json", "current"), (".pending.json", "pending")):
            if _owned_child(vault_root, "sources", source_id + suffix).exists():
                tokens.append(f"source_state:{source_id}:{label}")
    _owned_child(state_dir, "projections", "retrieval.sqlite")
    tokens.append("retrieval_projection")  # always-run invalidation covers creation after preview
    grants = _direct_names(state_dir, "adapters", "grants")
    tokens.extend(f"adapter_grant:{name}" for name in grants)
    tokens.extend(f"adapter_bundle:{name}" for name in _direct_names(state_dir, "adapters", "bundles"))
    tokens.extend(f"adapter_pending:{name}" for name in _direct_names(state_dir, "adapters", "pending"))
    tokens.extend(f"memory_confirmation:{name}" for name in _direct_names(state_dir, "memory-confirmations"))
    return tuple(tokens), _grant_external_scope(state_dir, grants)


def create_purge_preview(
    vault_root: Path, state_dir: Path, records: RecordSet, vault_seq: int, policy_epoch: int,
    requested: tuple[str, ...],
) -> PurgePreview:
    record_ids, source_ids = _expand_purge(records, requested)
    try:
        managed_copy_ids, external_copies = _snapshot_copy_scope(vault_root, state_dir, source_ids)
    except OSError as error:
        message = "An Aptuni-owned copy location is not safe to inspect; run `aptuni doctor`."
        raise AptuniError("privacy_copy_scope_unsafe", message) from error
    sources = {record.id: record for record in records.records() if record.record_type == "source_config"}
    external_copies = (*external_copies, *(
        {"copy_id": f"source_original:{source_id}", "provider": sources[source_id].source_type,
         "destination": sources[source_id].roots[0], "data_class": "original_source_unmodified"}
        for source_id in source_ids if source_id in sources
    ))
    fields: dict[str, Any] = {
        "schema_version": 1,
        "action_id": new_action_id(),
        "requested_record_ids": tuple(requested),
        "record_ids": record_ids,
        "source_ids": source_ids,
        "vault_seq": vault_seq,
        "policy_epoch": policy_epoch,
        "nonce_id": new_nonce(),
        "expires_at": (utc_now() + PURGE_TTL).isoformat(),
        "copy_effects": (
            "canonical records: irreversible deletion with deletion-ledger digests",
            "managed copies: exactly the ones listed below are deleted, and nothing else",
            "source replay state: deleted for every affected source; the original source is untouched",
            "retrieval projection: always invalidated, so a later rebuild excludes purged records",
            "adapter grants/bundles/pending plans listed below: revoked and deleted",
            "host transcripts, original sources and exported copies: user action required",
        ),
        "managed_copy_ids": managed_copy_ids,
        "external_copies": external_copies,
        "irreversible": True,
        "external_action_needed": True,
    }
    preview = PurgePreview(
        1, str(fields["action_id"]), tuple(requested), record_ids, source_ids, vault_seq, policy_epoch,
        str(fields["nonce_id"]), str(fields["expires_at"]), tuple(fields["copy_effects"]), managed_copy_ids,
        external_copies, True, True, _preview_digest(fields),
    )
    _write_private_json(state_dir / "privacy" / "pending" / f"{preview.action_id}.json", preview.to_dict())
    return preview


def load_purge_preview(state_dir: Path, action_id: str) -> PurgePreview:
    _validate_action_id(action_id)
    pending = state_dir / "privacy" / "pending" / f"{action_id}.json"
    intent = state_dir / "privacy" / "intents" / f"{action_id}.json"
    try:
        if pending.exists():
            value = json.loads(pending.read_text(encoding="utf-8"))
        elif intent.exists():
            value = json.loads(intent.read_text(encoding="utf-8"))["preview"]
        else:
            raise FileNotFoundError
        if not isinstance(value, dict):
            raise TypeError
        return _preview_from_dict(value)
    except FileNotFoundError as error:
        raise AptuniError("privacy_action_not_found", "No exact pending privacy action was found.") from error
    except (json.JSONDecodeError, OSError, KeyError, TypeError) as error:
        message = "The pending privacy action is invalid; preview it again."
        raise AptuniError("privacy_action_invalid", message) from error


def committed_purge_intent(state_dir: Path) -> bool:
    """True while any durable purge intent owns the canonical scope (Review 31 F1).

    The frozen preview is exact, so a record written after the intent commits can reference an
    in-scope record and make the approved deletion unsatisfiable. Every canonical writer waits for
    the intent to reach a terminal receipt or be cancelled; an unreadable intent also stops writes.
    """
    intents = state_dir / "privacy" / "intents"
    if not intents.is_dir():
        return False
    return any(intents.glob("act-*.json"))


def _validate_action_id(action_id: str) -> None:
    if not ACTION_RE.fullmatch(action_id):
        raise AptuniError("invalid_privacy_action_id", "An exact core-generated privacy action ID is required.")


def _remove_owned(root: Path, *parts: str) -> bool:
    path = _owned_child(root, *parts)
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
    return True


def _receipt_path(state_dir: Path, action_id: str) -> Path:
    return state_dir / "privacy" / "receipts" / f"{action_id}.json"


def _load_receipt(state_dir: Path, action_id: str, digest: str) -> DeletionReceipt | None:
    try:
        value = json.loads(_receipt_path(state_dir, action_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if value.get("action_digest") != digest:
        raise AptuniError("confirmation_stale", "The confirmation does not match this privacy action.")
    return DeletionReceipt.model_validate(value["receipt"])


def _reap_terminal_intents(state_dir: Path) -> None:
    directory = state_dir / "privacy" / "intents"
    if not directory.is_dir():
        return
    for path in directory.glob("act-*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            preview = _preview_from_dict(value["preview"])
            receipt = _load_receipt(state_dir, preview.action_id, preview.digest)
            if receipt is not None and receipt.terminal_state != "incomplete_retryable":
                _unlink_durable(path)
        except (AptuniError, OSError, json.JSONDecodeError, KeyError, TypeError):
            continue


def _load_or_commit_intent(
    state_dir: Path, action_id: str, confirmed_digest: str, vault_seq: int, policy_epoch: int,
) -> tuple[Path, dict[str, Any], PurgePreview]:
    intent_path = state_dir / "privacy" / "intents" / f"{action_id}.json"
    if intent_path.exists():
        intent = json.loads(intent_path.read_text(encoding="utf-8"))
        preview = _preview_from_dict(intent["preview"])
    else:
        _reap_terminal_intents(state_dir)
        active = [path for path in (state_dir / "privacy" / "intents").glob("act-*.json")
                  if path != intent_path]
        if active:
            raise AptuniError("privacy_action_in_progress", "Retry the committed privacy purge before another one.")
        preview = load_purge_preview(state_dir, action_id)
        if confirmed_digest != preview.digest:
            raise AptuniError("confirmation_stale", "The digest does not match this preview; nothing changed.")
        if datetime.fromisoformat(preview.expires_at) <= utc_now():
            raise AptuniError("confirmation_expired", "The purge confirmation expired; preview it again.")
        if preview.vault_seq != vault_seq or preview.policy_epoch != policy_epoch:
            raise AptuniError("confirmation_stale", "The Vault or policy changed; preview the purge again.")
        intent = {"schema_version": 1, "preview": preview.to_dict(), "results": {}}
        _write_private_json(intent_path, intent)
        (state_dir / "privacy" / "pending" / f"{action_id}.json").unlink(missing_ok=True)
    if confirmed_digest != preview.digest:
        raise AptuniError("confirmation_stale", "The confirmation does not match this privacy action.")
    return intent_path, intent, preview


def _purge_canonical(
    vault: Vault, records: RecordSet, vault_seq: int, preview: PurgePreview,
) -> str:
    target_digests = {sha256_text(record_id) for record_id in preview.record_ids}
    if set(preview.record_ids).intersection(records.ids()):
        try:
            vault.purge(set(preview.record_ids), expected_seq=vault_seq)
            return "deleted"
        except ConflictError as error:
            raise AptuniError("confirmation_stale", "The Vault changed; preview the purge again.") from error
        except InvariantError:
            return "failed_retryable"  # a dependent record landed on the frozen scope; stay content-free
    return "deleted" if target_digests <= vault.ledger_digests() else "failed_retryable"


def _delete_projection(state_dir: Path) -> bool:
    _owned_child(state_dir, "projections", "retrieval.sqlite")
    projection = SqliteProjection(state_dir)
    present = projection.path.exists()
    projection.delete()
    return present


def _remove_managed_copy(vault: Vault, state_dir: Path, token: str) -> bool:
    if token == "retrieval_projection":
        return _delete_projection(state_dir)
    kind, _, name = token.partition(":")
    if kind == "source_state":
        source_id, _, state_kind = name.partition(":")
        if not re.fullmatch(ID_PATTERN, source_id) or state_kind not in {"current", "pending"}:
            raise OSError("managed_copy_id_invalid")
        suffix = ".json" if state_kind == "current" else ".pending.json"
        return _remove_owned(vault.root, "sources", source_id + suffix)
    roots = {
        "adapter_grant": ("adapters", "grants"),
        "adapter_bundle": ("adapters", "bundles"),
        "adapter_pending": ("adapters", "pending"),
        "memory_confirmation": ("memory-confirmations",),
    }
    parts = roots.get(kind)
    if parts is None or not name or "/" in name or name in {".", ".."}:
        raise OSError("managed_copy_id_invalid")
    return _remove_owned(state_dir, *parts, name)


def _run_cleanups(
    vault: Vault, state_dir: Path, preview: PurgePreview, intent_path: Path,
    intent: dict[str, Any], results: dict[str, str],
) -> None:
    for copy_id in preview.managed_copy_ids:
        if results.get(copy_id) in {"deleted", "not_present"}:
            continue
        try:
            results[copy_id] = "deleted" if _remove_managed_copy(vault, state_dir, copy_id) else "not_present"
        except OSError:
            results[copy_id] = "failed_retryable"
        intent["results"] = results
        _write_private_json(intent_path, intent)


def _build_receipt(action_id: str, preview: PurgePreview, results: dict[str, str]) -> DeletionReceipt:
    managed_failed = any(value == "failed_retryable" for value in results.values())
    per_copy = [CopyResult(copy_class=name, result=value) for name, value in sorted(results.items())]
    per_copy.extend((
        CopyResult(copy_class="deletion_ledger", result="retained"),
        CopyResult(copy_class="privacy_receipt", result="retained"),
        CopyResult(copy_class="profile_exports", result="external_action_needed"),
    ))
    per_copy.extend(
        CopyResult(copy_class=item["copy_id"], result="external_action_needed",
                   provider=item["provider"], destination=item["destination"], data_class=item["data_class"])
        for item in preview.external_copies
    )
    return DeletionReceipt(
        id=new_id("rcp"), schema_version=1, recorded_at=utc_now(), purge_id=action_id,
        terminal_state="incomplete_retryable" if managed_failed else "complete_managed_external_action_needed",
        per_copy=tuple(per_copy),
    )


def confirm_purge(
    vault: Vault, state_dir: Path, action_id: str, confirmed_digest: str,
) -> DeletionReceipt:
    _validate_action_id(action_id)
    with _action_lock(state_dir, "privacy"):
        prior = _load_receipt(state_dir, action_id, confirmed_digest)
        if prior is not None and prior.terminal_state != "incomplete_retryable":
            _unlink_durable(state_dir / "privacy" / "intents" / f"{action_id}.json")
            return prior
        with source_operations_lock(state_dir):
            vault_seq, records = vault.snapshot()
            policy = records.policy()
            if policy is None:
                raise AptuniError("vault_unreadable", "The Vault has no module policy.")
            intent_path, intent, preview = _load_or_commit_intent(
                state_dir, action_id, confirmed_digest, vault_seq, policy.epoch
            )
            results: dict[str, str] = dict(intent.get("results", {}))
            if "canonical" not in results:
                results["canonical"] = _purge_canonical(vault, records, vault_seq, preview)
                intent["results"] = results
                _write_private_json(intent_path, intent)
            _run_cleanups(vault, state_dir, preview, intent_path, intent, results)
            receipt = _build_receipt(action_id, preview, results)
            _write_private_json(_receipt_path(state_dir, action_id), {
                "schema_version": 1, "action_digest": preview.digest,
                "receipt": receipt.model_dump(mode="json"),
            })
            if receipt.terminal_state != "incomplete_retryable":
                _unlink_durable(intent_path)
            return receipt


def cancel_purge(vault: Vault, state_dir: Path, action_id: str) -> None:
    """Abandon a committed intent that destroyed nothing canonical; the receipt stays as audit.

    The recorded result is written *after* the canonical purge returns, so it cannot be the only
    evidence: a crash in that window would let cancel claim nothing was deleted. The deletion ledger
    is durable before any rewrite (ADR-0010), so it is the authority here (Review 32 N2).
    """
    _validate_action_id(action_id)
    with _action_lock(state_dir, "privacy"):
        intent_path = state_dir / "privacy" / "intents" / f"{action_id}.json"
        if not intent_path.exists():
            raise AptuniError("privacy_action_not_found", "No committed privacy action with that id.")
        try:
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            preview = _preview_from_dict(intent["preview"])
            results = intent.get("results", {})
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise AptuniError("privacy_action_invalid", "The committed privacy action is invalid.") from error
        ledgered = vault.ledger_digests().intersection(
            sha256_text(record_id) for record_id in preview.record_ids
        )
        if ledgered or (isinstance(results, dict) and results.get("canonical") == "deleted"):
            message = "Canonical records were already deleted; retry this purge instead of cancelling it."
            raise AptuniError("privacy_cancel_refused", message)
        _unlink_durable(intent_path)


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
                      "excluded", "managed_unlink_or_purge",
                      "incremental source identity and replay; an Aptuni backup omits it and a restore "
                      "clears it, so the next sync rebuilds it from the restored generation"),
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
        _managed_copy("privacy_actions", "temporary", state_dir / "privacy" / "pending", "ten_minutes",
                      "excluded", "managed_expiry_retry_or_cancel", "privacy previews and committed retry intents",
                      state_dir / "privacy" / "intents"),
        _managed_copy("privacy_receipts", "audit", state_dir / "privacy" / "receipts", "content_free_bounded",
                      "excluded", "retained_audit", "content-free per-copy purge outcomes"),
        _managed_copy("deletion_ledger", "deletion_ledger", vault_root / "deletion-ledger.jsonl",
                      "irreversible_identifier_digests", "included_with_vault",
                      "retained_to_prevent_resurrection",
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

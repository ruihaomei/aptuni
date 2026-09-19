"""Path + content-hash reconciliation shared by keyed providers (Folder, GitHub).

Rules (conservative, ADR-0006):
- same key, same hash      -> unchanged (or ``modify`` with ``parser_upgrade``)
- same key, new hash       -> ``modify``
- new key whose hash matches exactly one vanished item, and that hash is not
  shared by another new key -> ``move`` (identity kept)
- several vanished/new items share a hash -> ``ambiguous`` for review; the
  vanished candidates are *not* tombstoned while under review
- other new keys -> ``add`` with a fresh deterministic subject id
- other vanished keys -> ``remove`` (tombstone proposal) only under complete coverage
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from s05a.records import (
    ContractError,
    Extension,
    Operation,
    Snapshot,
    SnapshotItem,
    SourceLocator,
    canonical_json,
)


@dataclass(frozen=True)
class Observed:
    key: str
    content_hash: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KeyedSpec:
    source_id: str
    provider: str
    schema: str
    version: int
    key_field: str


@dataclass(frozen=True)
class Reconciled:
    snapshot: Snapshot
    operations: tuple[Operation, ...]


def snapshot_id_for(source_id: str, coverage: str, items: tuple[SnapshotItem, ...]) -> str:
    body = [
        [item.locator.subject_id, canonical_json(dict(item.locator.extension.fields)), item.content_hash]
        for item in items
    ]
    digest = hashlib.sha256(canonical_json([source_id, coverage, body]).encode("utf-8"))
    return "snap-" + digest.hexdigest()[:24]


def _new_subject(spec: KeyedSpec, base_id: str | None, observed: Observed) -> str:
    seed = canonical_json([spec.source_id, base_id, observed.key, observed.content_hash])
    return f"{spec.provider}-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def reconcile_keyed(
    spec: KeyedSpec,
    previous: Snapshot | None,
    observed: list[Observed],
    coverage: str,
    parser_changed: bool,
) -> Reconciled:
    def locator(subject: str, item: Observed) -> SourceLocator:
        fields = {spec.key_field: item.key, **item.fields}
        return SourceLocator(spec.source_id, spec.provider, subject, Extension(spec.schema, spec.version, fields))

    old_by_key = {
        item.locator.extension.fields[spec.key_field]: item for item in (previous.items if previous else ())
    }
    new_by_key = {item.key: item for item in observed}
    ops: list[Operation] = []
    items: list[SnapshotItem] = []

    for key in sorted(new_by_key.keys() & old_by_key.keys()):
        old, new = old_by_key[key], new_by_key[key]
        after = locator(old.locator.subject_id, new)
        items.append(SnapshotItem(after, new.content_hash))
        if old.content_hash != new.content_hash:
            ops.append(Operation.modify(old.locator, after, new.content_hash, reasons=("content_changed",)))
        elif parser_changed:
            ops.append(Operation.modify(old.locator, after, new.content_hash, reasons=("parser_upgrade",)))

    vanished = {key: old_by_key[key] for key in old_by_key.keys() - new_by_key.keys()}
    appeared = sorted(new_by_key.keys() - old_by_key.keys())
    vanished_by_hash: dict[str, list[str]] = defaultdict(list)
    for key, item in vanished.items():
        vanished_by_hash[item.content_hash].append(key)
    appeared_by_hash: dict[str, list[str]] = defaultdict(list)
    for key in appeared:
        appeared_by_hash[new_by_key[key].content_hash].append(key)

    consumed: set[str] = set()
    base_id = previous.snapshot_id if previous else None
    for key in appeared:
        new = new_by_key[key]
        old_keys = sorted(vanished_by_hash.get(new.content_hash, []))
        if len(old_keys) == 1 and len(appeared_by_hash[new.content_hash]) == 1:
            old = vanished[old_keys[0]]
            after = locator(old.locator.subject_id, new)
            items.append(SnapshotItem(after, new.content_hash))
            ops.append(Operation.move(old.locator.subject_id, old.locator, after, new.content_hash,
                                      reasons=("exact_hash_unique",)))
            consumed.add(old_keys[0])
            continue
        subject = _new_subject(spec, base_id, new)
        after = locator(subject, new)
        items.append(SnapshotItem(after, new.content_hash))
        if old_keys:
            candidates = tuple(vanished[k].locator.subject_id for k in old_keys)
            if len(candidates) == 1:
                candidates = (*candidates, subject)  # "same as old" vs "genuinely new"
            ops.append(Operation.ambiguous(after, candidates, ("duplicate_hash",), content_hash=new.content_hash))
            consumed.update(old_keys)
        else:
            ops.append(Operation.add(after, new.content_hash))

    unresolved = [key for key in vanished if key not in consumed]
    if coverage == "complete":
        for key in sorted(unresolved):
            old = vanished[key]
            ops.append(Operation.remove(old.locator.subject_id, old.locator, old.content_hash,
                                        reasons=("source_item_missing",)))
    else:
        # Not observed is not gone: carry the old item forward unchanged.
        items.extend(vanished[key] for key in sorted(unresolved))

    ordered = tuple(sorted(items, key=lambda item: item.locator.subject_id))
    if len({item.locator.subject_id for item in ordered}) != len(ordered):
        raise ContractError("subject_collision")
    snapshot = Snapshot(snapshot_id_for(spec.source_id, coverage, ordered), spec.source_id, coverage, ordered)
    return Reconciled(snapshot, tuple(ops))

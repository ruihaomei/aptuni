"""Path + content-hash reconciliation shared by keyed providers (Folder, GitHub).

Rules (conservative, ADR-0006; hardened by S05A review round 1):
- same key, same hash      -> unchanged (or ``modify`` with ``parser_upgrade``)
- same key, new hash       -> ``modify``
- new key whose hash matches exactly one vanished item, that hash is not shared
  by another new key, and coverage is complete -> ``move`` (identity kept)
- the same match under *partial* coverage -> ``ambiguous``: an unobserved item is
  not evidence of a move
- several vanished/new items share a hash -> ``ambiguous``
- old items named as ambiguity candidates are carried forward ``held``: never
  re-matched or tombstoned until review resolves them; a held item re-observed
  at its own key is released with its identity (changed bytes -> reviewable
  ``modify`` with ``held_item_changed``)
- other new keys -> ``add``; other vanished keys -> ``remove`` (tombstone
  proposal) only under complete coverage, otherwise carried forward
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field, replace
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
        [item.locator.subject_id, canonical_json(dict(item.locator.extension.fields)), item.content_hash,
         item.held]
        for item in items
    ]
    digest = hashlib.sha256(canonical_json([source_id, coverage, body]).encode("utf-8"))
    return "snap-" + digest.hexdigest()[:24]


def _new_subject(spec: KeyedSpec, base_id: str | None, observed: Observed) -> str:
    seed = canonical_json([spec.source_id, base_id, observed.key, observed.content_hash])
    return f"{spec.provider}-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


class _Run:
    def __init__(self, spec: KeyedSpec, previous: Snapshot | None, observed: list[Observed]) -> None:
        self.spec = spec
        self.base_id = previous.snapshot_id if previous else None
        key = spec.key_field
        prior = previous.items if previous else ()
        self.old_by_key = {i.locator.extension.fields[key]: i for i in prior if not i.held}
        self.held = [i for i in prior if i.held]
        self.new_by_key = {item.key: item for item in observed}
        self.ops: list[Operation] = []
        self.items: list[SnapshotItem] = []

    def locator(self, subject: str, item: Observed) -> SourceLocator:
        fields = {self.spec.key_field: item.key, **item.fields}
        extension = Extension(self.spec.schema, self.spec.version, fields)
        return SourceLocator(self.spec.source_id, self.spec.provider, subject, extension)

    def release_held(self) -> None:
        """A held item seen again at its own key keeps its identity; changed bytes go to review."""
        still_held = []
        for item in self.held:
            key = item.locator.extension.fields[self.spec.key_field]
            new = self.new_by_key.get(key)
            if new is None or key in self.old_by_key:
                still_held.append(item)
                continue
            after = self.locator(item.locator.subject_id, new)
            self.items.append(SnapshotItem(after, new.content_hash))
            if new.content_hash != item.content_hash:
                self.ops.append(Operation.modify(item.locator, after, new.content_hash,
                                                 reasons=("content_changed", "held_item_changed"),
                                                 review_state="needs_review"))
            del self.new_by_key[key]
        self.held = still_held

    def same_keys(self, parser_changed: bool) -> None:
        for key in sorted(self.new_by_key.keys() & self.old_by_key.keys()):
            old, new = self.old_by_key[key], self.new_by_key[key]
            after = self.locator(old.locator.subject_id, new)
            self.items.append(SnapshotItem(after, new.content_hash))
            if old.content_hash != new.content_hash:
                self.ops.append(Operation.modify(old.locator, after, new.content_hash, reasons=("content_changed",)))
            elif parser_changed:
                self.ops.append(Operation.modify(old.locator, after, new.content_hash, reasons=("parser_upgrade",)))

    def new_keys(self, coverage: str) -> set[str]:
        vanished = {k: v for k, v in self.old_by_key.items() if k not in self.new_by_key}
        appeared = sorted(self.new_by_key.keys() - self.old_by_key.keys())
        vanished_by_hash: dict[str, list[str]] = defaultdict(list)
        for key, item in vanished.items():
            vanished_by_hash[item.content_hash].append(key)
        appeared_by_hash: dict[str, list[str]] = defaultdict(list)
        for key in appeared:
            appeared_by_hash[self.new_by_key[key].content_hash].append(key)

        consumed: set[str] = set()
        for key in appeared:
            new = self.new_by_key[key]
            old_keys = sorted(vanished_by_hash.get(new.content_hash, []))
            unique = len(old_keys) == 1 and len(appeared_by_hash[new.content_hash]) == 1
            if unique and coverage == "complete":
                old = vanished[old_keys[0]]
                after = self.locator(old.locator.subject_id, new)
                self.items.append(SnapshotItem(after, new.content_hash))
                self.ops.append(Operation.move(old.locator.subject_id, old.locator, after, new.content_hash,
                                               reasons=("exact_hash_unique",)))
                consumed.add(old_keys[0])
                continue
            subject = _new_subject(self.spec, self.base_id, new)
            after = self.locator(subject, new)
            self.items.append(SnapshotItem(after, new.content_hash))
            if not old_keys:
                self.ops.append(Operation.add(after, new.content_hash))
                continue
            candidates = tuple(vanished[k].locator.subject_id for k in old_keys)
            if len(candidates) == 1:
                candidates = (*candidates, subject)  # "same as old" vs "genuinely new"
            reason = "duplicate_hash" if not unique else "partial_coverage_match"
            self.ops.append(Operation.ambiguous(after, candidates, (reason,), content_hash=new.content_hash))
            for old_key in old_keys:
                if old_key not in consumed:
                    self.held.append(replace(vanished[old_key], held=True))
            consumed.update(old_keys)
        return {k for k in vanished if k not in consumed}

    def vanished(self, unresolved: set[str], coverage: str) -> None:
        for key in sorted(unresolved):
            old = self.old_by_key[key]
            if coverage == "complete":
                self.ops.append(Operation.remove(old.locator.subject_id, old.locator, old.content_hash,
                                                 reasons=("source_item_missing",)))
            else:
                self.items.append(old)  # not observed is not gone

    def snapshot(self, coverage: str) -> Snapshot:
        ordered = tuple(sorted([*self.items, *self.held], key=lambda item: item.locator.subject_id))
        if len({item.locator.subject_id for item in ordered}) != len(ordered):
            raise ContractError("subject_collision")
        return Snapshot(snapshot_id_for(self.spec.source_id, coverage, ordered), self.spec.source_id,
                        coverage, ordered)


def reconcile_keyed(
    spec: KeyedSpec,
    previous: Snapshot | None,
    observed: list[Observed],
    coverage: str,
    parser_changed: bool,
) -> Reconciled:
    run = _Run(spec, previous, observed)
    run.release_held()
    run.same_keys(parser_changed)
    unresolved = run.new_keys(coverage)
    run.vanished(unresolved, coverage)
    return Reconciled(run.snapshot(coverage), tuple(run.ops))

"""Identity-exact snapshots and deltas for MarginNote 4 concepts (ADR-0006, ADR-0015).

Native ``ZNOTEID`` values are the subject identity, so there is no content matching and nothing
is guessed: a parent change is a move, a digest change is a modify, a new ID is an add, and a
vanished ID is a removal. The locator (``marginnote.locator@2``) holds IDs and structure only.
"""

from __future__ import annotations

from dataclasses import dataclass

from aptuni.sources.marginnote4.digest import Digest
from aptuni.sources.marginnote4.store import MarginNoteStoreError
from aptuni.sources.reconcile import snapshot_id_for
from aptuni.sources.records import CandidateDelta, Extension, Operation, Snapshot, SnapshotItem, SourceLocator

SCHEMA = ("marginnote.locator", 2)
PARSER = ("marginnote4.store", "1")


@dataclass(frozen=True)
class Rendered:
    subject: str
    summary: str


@dataclass(frozen=True)
class MarginNoteScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]
    rendered: dict[str, Rendered]  # note id -> bounded Evidence text, held in memory only
    notes: tuple[str, ...] = ()


def _locator(source_id: str, digest: Digest, note_id: str) -> SourceLocator:
    concept = digest.concepts[note_id]
    fields = {
        "database_id": digest.database_id, "notebook_id": concept.notebook_id, "note_id": note_id,
        "revision": concept.revision, "parent_id": concept.parent_id, "depth": concept.depth,
        "sibling_index": concept.sibling_index, "child_count": len(concept.children),
        "subtree_concepts": concept.subtree_concepts, "excerpt_count": concept.subtree_excerpts,
    }
    return SourceLocator(source_id, "marginnote", note_id, Extension(*SCHEMA, fields))


def scan_marginnote(digest: Digest, source_id: str, previous: MarginNoteScan | None,
                    missing_notebooks: frozenset[str] = frozenset()) -> MarginNoteScan:
    """Diff the digest against the previous snapshot by native note ID."""
    if previous is not None and previous.snapshot.items and not digest.concepts and not missing_notebooks:
        raise MarginNoteStoreError("marginnote_store_empty")  # never read a vanished library as mass deletion
    items: list[SnapshotItem] = []
    rendered: dict[str, Rendered] = {}
    for note_id in sorted(digest.concepts):
        concept = digest.concepts[note_id]
        summary = digest.summary(concept)
        rendered[note_id] = Rendered(digest.subject(concept), summary)
        items.append(SnapshotItem(_locator(source_id, digest, note_id),
                                  concept.fingerprint(digest.covers(concept), summary)))
    prior = {item.locator.subject_id: item for item in previous.snapshot.items} if previous else {}
    present = {item.locator.subject_id for item in items}
    # Partial coverage cannot prove disappearance: carry every unobserved card, never an observed one.
    carried = [item for subject, item in prior.items() if subject not in present] if missing_notebooks else []
    ops: list[Operation] = []
    for item in items:
        before = prior.get(item.locator.subject_id)
        if before is None:
            ops.append(Operation.add(item.locator, item.content_hash))
            continue
        old_fields, new_fields = before.locator.extension.fields, item.locator.extension.fields
        if old_fields.get("parent_id") != new_fields.get("parent_id"):
            changed = ("content_changed",) if before.content_hash != item.content_hash else ()
            ops.append(Operation.move(item.locator.subject_id, before.locator, item.locator, item.content_hash,
                                      reasons=("native_id_match", *changed)))
        elif before.content_hash != item.content_hash:
            ops.append(Operation.modify(before.locator, item.locator, item.content_hash,
                                        reasons=("native_id_match",)))
    coverage = "partial" if missing_notebooks else "complete"
    if coverage == "complete":
        ops.extend(Operation.remove(subject, item.locator, item.content_hash, reasons=("source_note_missing",))
                   for subject, item in sorted(prior.items()) if subject not in present)
    all_items = tuple(sorted([*items, *carried], key=lambda i: i.locator.subject_id))
    snapshot = Snapshot(snapshot_id_for(source_id, coverage, all_items), source_id, coverage, all_items)
    base = previous.snapshot.snapshot_id if previous else None
    sequence = previous.delta.sequence + 1 if previous else 1
    delta = CandidateDelta.build(source_id, base, snapshot.snapshot_id, PARSER, tuple(ops), sequence)
    notes = tuple(f"marginnote_notebook_missing:{n}" for n in sorted(missing_notebooks))
    return MarginNoteScan(snapshot, delta, PARSER, rendered, notes)

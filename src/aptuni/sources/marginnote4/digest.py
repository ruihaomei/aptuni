"""Compress a MarginNote 4 library into a knowledge digest (ADR-0015).

A *concept* is a standalone card with a title or with mind-map children. Untitled excerpt leaves
and merged excerpts (``ZGROUPNOTEID``) do not become concepts; they are counted on the concept
they belong to. Each concept keeps what an agent needs to understand the learning structure
(where it sits, what it covers, how deep the study went, from which source and when) in a few
bounded fields, never the excerpt or comment text itself.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from aptuni.sources.marginnote4.store import NoteRow, StoreSnapshot

UUID = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}")
CORE_DATA_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
LABEL_CHARS = 32
PATH_LABELS = 5
COVERS = 8
SUMMARY_CHARS = 280


def _clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _clip(text: str, limit: int) -> str:
    text = _clean(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _month(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    try:
        return (CORE_DATA_EPOCH + timedelta(seconds=seconds)).strftime("%Y-%m")
    except (OverflowError, ValueError):
        return None


@dataclass
class Concept:
    note_id: str
    notebook_id: str
    revision: int
    label: str
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    depth: int = 0
    sibling_index: int = 0
    excerpts: int = 0  # untitled excerpt leaves and merged excerpts owned by this concept
    annotated: int = 0
    subtree_concepts: int = 0
    subtree_excerpts: int = 0
    levels_below: int = 0
    months: set[str] = field(default_factory=set)
    pages: dict[str, tuple[int, int]] = field(default_factory=dict)  # book md5 -> (first, last)
    path: tuple[str, ...] = ()

    def fingerprint(self, covers: tuple[str, ...], summary: str) -> str:
        """Content hash of the minimized digest: any change the agent could see is a modify."""
        body = json.dumps([self.label, self.parent_id, self.path, covers, summary], ensure_ascii=False)
        return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Digest:
    database_id: str
    concepts: dict[str, Concept]
    notebooks: dict[str, str]
    books: dict[str, str]

    def covers(self, concept: Concept) -> tuple[str, ...]:
        return tuple(self.concepts[c].label for c in concept.children)

    def subject(self, concept: Concept) -> str:
        return " › ".join(concept.path)

    def summary(self, concept: Concept) -> str:
        """≤280-character structured summary: path, coverage, depth, source, time. No source text."""
        covers = self.covers(concept)
        parts = [f"{self.subject(concept)} [{_clip(self.notebooks.get(concept.notebook_id, ''), 24)}]"]
        if covers:
            more = f" (+{len(covers) - COVERS})" if len(covers) > COVERS else ""
            parts.append("covers: " + ", ".join(covers[:COVERS]) + more)
        parts.append(f"{concept.subtree_excerpts} excerpts, {concept.annotated} annotated, "
                     f"{concept.subtree_concepts} sub-concepts, {concept.levels_below} levels below")
        if concept.pages:
            md5, (first, last) = min(concept.pages.items())
            pages = f"p.{first}" if first == last else f"p.{first}–{last}"
            parts.append(f"from {_clip(self.books.get(md5, 'document'), 28)} {pages}")
        if concept.months:
            first_m, last_m = min(concept.months), max(concept.months)
            parts.append(first_m if first_m == last_m else f"{first_m}→{last_m}")
        return _clip("; ".join(parts), SUMMARY_CHARS)


def build_digest(snapshot: StoreSnapshot) -> Digest:
    notes = {row.note_id: row for row in snapshot.notes}
    direct = {row.note_id: row.group_id for row in snapshot.notes
              if row.group_id and row.group_id != row.note_id and row.group_id in notes}
    owner: dict[str, str] = {n: _final_owner(n, direct) for n in direct}
    links = {row.note_id: [c for c in dict.fromkeys(UUID.findall(row.mindlinks))
                           if c in notes and c != row.note_id and c not in owner
                           and notes[c].notebook_id == row.notebook_id]
             for row in snapshot.notes if row.note_id not in owner}
    parent: dict[str, str] = {}
    for note_id, children in links.items():
        for child in children:
            parent.setdefault(child, note_id)
    has_children = {n for n, children in links.items() if children}
    concept_ids = {n for n in links if _clean(notes[n].title) or n in has_children}
    concepts = {n: _concept(notes[n]) for n in concept_ids}
    _attach(notes, owner, links, parent, concepts)
    for concept in concepts.values():
        concept.parent_id = _nearest(concept.parent_id, parent, concepts)
    for concept in sorted(concepts.values(), key=lambda c: c.note_id):
        if concept.parent_id is not None:
            concepts[concept.parent_id].children.append(concept.note_id)
    _order_children(concepts, links)
    seen: set[str] = set()
    for root in sorted((c for c in concepts.values() if c.parent_id is None), key=lambda c: c.note_id):
        _walk(concepts, root, (), 0, seen)
    for orphan in sorted((c for c in concepts.values() if c.note_id not in seen), key=lambda c: c.note_id):
        orphan.parent_id = None  # a mind-map cycle: break it deterministically at the smallest ID
        _walk(concepts, orphan, (), 0, seen)
    return Digest(snapshot.database_id, concepts, snapshot.notebooks, snapshot.books)


def _final_owner(note_id: str, direct: dict[str, str]) -> str:
    """Follow merge chains (an excerpt merged into an already-merged card) to the final card."""
    seen = {note_id}
    current = direct[note_id]
    while current in direct and direct[current] not in seen:
        seen.add(current)
        current = direct[current]
    return current


def _nearest(start: str | None, parent: dict[str, str], concepts: dict[str, Concept]) -> str | None:
    """Climb raw mind-map parents to the nearest concept; a cycle without a concept yields None."""
    visited: set[str] = set()
    node = start
    while node is not None and node not in concepts:
        if node in visited:
            return None
        visited.add(node)
        node = parent.get(node)
    return node


def _concept(row: NoteRow) -> Concept:
    label = _clip(row.title, LABEL_CHARS) if _clean(row.title) else _clip(row.excerpt_head, LABEL_CHARS) or "(image)"
    return Concept(row.note_id, row.notebook_id, row.revision, label)


def _attach(notes: dict[str, NoteRow], owner: dict[str, str], links: dict[str, list[str]],
            parent: dict[str, str], concepts: dict[str, Concept]) -> None:
    """Give every note to its nearest concept: merged excerpts to their card, leaves to their parent."""
    for note_id, row in notes.items():
        found = _nearest(owner.get(note_id) or note_id, parent, concepts)
        if found is None:
            continue
        home = found
        concept = concepts[home]
        if note_id != home and row.has_excerpt:
            concept.excerpts += 1
        concept.annotated += int(row.annotated)
        month = _month(row.note_date)
        if month:
            concept.months.add(month)
        if row.book_md5 and row.start_page is not None:
            first, last = concept.pages.get(row.book_md5, (row.start_page, row.end_page or row.start_page))
            concept.pages[row.book_md5] = (min(first, row.start_page), max(last, row.end_page or row.start_page))
        if note_id == home and home in parent:
            concept.parent_id = parent[home]


def _order_children(concepts: dict[str, Concept], links: dict[str, list[str]]) -> None:
    order = {child: index for children in links.values() for index, child in enumerate(children)}
    for concept in concepts.values():
        concept.children.sort(key=lambda c: (order.get(c, 1 << 30), c))
        for index, child in enumerate(concept.children):
            concepts[child].sibling_index = index


def _walk(concepts: dict[str, Concept], concept: Concept, path: tuple[str, ...], depth: int,
          seen: set[str]) -> None:
    if concept.note_id in seen:
        return
    seen.add(concept.note_id)
    concept.depth = depth
    concept.path = (*path, concept.label)[-PATH_LABELS:]
    concept.subtree_concepts, concept.subtree_excerpts, concept.levels_below = 0, concept.excerpts, 0
    for child_id in concept.children:
        child = concepts[child_id]
        _walk(concepts, child, (*path, concept.label), depth + 1, seen)
        concept.subtree_concepts += 1 + child.subtree_concepts
        concept.subtree_excerpts += child.subtree_excerpts
        concept.annotated += child.annotated
        concept.months |= child.months
        for md5, (first, last) in child.pages.items():  # the page range spans the whole subtree
            own = concept.pages.get(md5, (first, last))
            concept.pages[md5] = (min(own[0], first), max(own[1], last))
        concept.levels_below = max(concept.levels_below, child.levels_below + 1)

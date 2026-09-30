"""Knowledge State: a derived, per-concept projection of Evidence (ADR-0029 item 8).

Nothing here is canonical. Counts come from exposable Evidence; owner-declared Facts are counted
separately and never raise the evidence level. The level is a ladder read directly from the counts
and is described everywhere as derived from Evidence, never as a proficiency measure.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from aptuni.domain.evidence_profile import EVIDENCE_PROFILE_TYPE, strongest_signal
from aptuni.knowledge.classify import CONCEPT_SCHEMA
from aptuni.knowledge.concepts import (
    concept_by_id,
    is_placeholder,
    is_structural,
    label_concept,
    normalize,
    resolve_label,
    resolve_text,
)

__all__ = ["DIMENSIONS", "LEVELS", "KnowledgeIndex", "KnowledgeState", "evidence_level"]

DIMENSIONS = ("exposure", "studied", "applied", "demonstrated")
LEVELS = ("unknown", "exposed", "studied", "practiced", "strongly_practiced", "demonstrated")
DECLARED_MODULES = frozenset({"knowledge", "skills", "experience", "projects"})
PATH_SEPARATOR = " › "
LEVEL_NOTE = "derived from Evidence, not a proficiency measure"
#: An unregistered card title found under this many different parent topics is a section heading.
HEADING_PARENTS = 5


def evidence_level(counts: dict[str, int], contexts: dict[str, int]) -> str:
    """The six-step ladder of ADR-0029 item 8, from observed Evidence only."""
    if counts.get("demonstrated", 0):
        return "demonstrated"
    if contexts.get("applied", 0) >= 2:
        return "strongly_practiced"
    if counts.get("applied", 0):
        return "practiced"
    if counts.get("studied", 0):
        return "studied"
    return "exposed" if counts.get("exposure", 0) else "unknown"


@dataclass
class _Accumulator:
    label: str
    evidence: dict[str, list[str]] = field(default_factory=lambda: {d: [] for d in DIMENSIONS})
    sources: dict[str, set[str]] = field(default_factory=lambda: {d: set() for d in DIMENSIONS})
    declared: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class KnowledgeState:
    concept_id: str
    label: str
    counts: dict[str, int]
    contexts: dict[str, int]
    declared: int
    evidence_ids: tuple[str, ...]  # strongest dimension first
    declared_ids: tuple[str, ...]

    @property
    def level(self) -> str:
        return evidence_level(self.counts, self.contexts)

    @property
    def signals(self) -> tuple[str, ...]:
        return tuple(d for d in DIMENSIONS if self.counts.get(d))

    def summary(self) -> str:
        """One compact, cited line; only dimensions with Evidence are listed."""
        parts = [f"{d} {self.counts[d]} ({self.contexts[d]} source{'s' if self.contexts[d] != 1 else ''})"
                 for d in reversed(DIMENSIONS) if self.counts[d]]
        observed = ", ".join(parts) if parts else "no observed evidence"
        claims = f"; owner-declared claims {self.declared}" if self.declared else ""
        return f"Knowledge state · {self.label}: evidence level {self.level} ({LEVEL_NOTE}). {observed}{claims}."

    def payload(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id, "label": self.label, "level": self.level,
            "level_note": LEVEL_NOTE, "counts": dict(self.counts), "contexts": dict(self.contexts),
            "declared": self.declared, "evidence_ids": list(self.evidence_ids),
            "declared_ids": list(self.declared_ids),
        }


def _path(record: Any) -> list[str]:
    return [part for part in record.subject.split(PATH_SEPARATOR) if part]


def _card_concepts(path: list[str], headings: set[str]) -> tuple[tuple[str, str], ...]:
    """A card is about its own title, or, for a heading or placeholder card, about its parent topic."""
    for label in reversed(path[-2:]):
        if is_placeholder(label):
            continue
        if normalize(label) in headings or (is_structural(label) and not resolve_text(label)):
            continue
        return resolve_label(label)
    return ()


def _evidence_concepts(record: Any, headings: set[str]) -> tuple[tuple[str, str], ...]:
    locator = record.provenance.locator
    schema = locator.extension.schema_name if locator is not None else ""
    if schema == CONCEPT_SCHEMA:
        concept_id = str(locator.extension.fields.get("concept_id", ""))
        concept = concept_by_id(concept_id)
        return ((concept_id, concept.label),) if concept is not None else ()
    if schema == "marginnote.locator":
        return _card_concepts(_path(record), headings)
    if schema == "github.locator":
        return ()  # a file: its concepts arrive as github.concept items
    stem = PurePosixPath(record.subject).stem  # other documents: named registry concepts only
    found = (concept_by_id(cid) for cid in resolve_text(stem))
    return tuple((concept.id, concept.label) for concept in found if concept is not None)


def _headings(records: list[Any]) -> set[str]:
    """Unregistered card titles that recur under at least ``HEADING_PARENTS`` different parents."""
    parents: dict[str, set[str]] = {}
    for record in records:
        locator = getattr(record, "provenance", None) and record.provenance.locator
        if record.record_type != "evidence" or locator is None or locator.extension.schema_name != "marginnote.locator":
            continue
        path = _path(record)
        if len(path) >= 2:
            parents.setdefault(normalize(path[-1]), set()).add(normalize(path[-2]))
    return {label for label, seen in parents.items() if len(seen) >= HEADING_PARENTS and not resolve_text(label)}


class KnowledgeIndex:
    """Concept -> Knowledge State over one set of exposable records (built once per Vault sequence)."""

    def __init__(self, records: Iterable[Any]) -> None:
        self._acc: dict[str, _Accumulator] = {}
        self._by_record: dict[str, tuple[str, ...]] = {}
        derived: list[Any] = []
        records = list(records)
        self._heading_labels = _headings(records)
        for record in records:
            if record.record_type == "evidence" and record.change_kind != "retraction":
                self._add_evidence(record)
            elif record.record_type == "fact" and record.type == EVIDENCE_PROFILE_TYPE:
                derived.append(record)  # 1:1 with its Evidence: mapped, never counted twice
            elif (record.record_type == "fact" and record.trust == "user_declared"
                  and record.module in DECLARED_MODULES):
                self._add_declared(record)
        for fact in derived:
            concepts = self._by_record.get(fact.evidence_ids[0]) if fact.evidence_ids else None
            if concepts:
                self._by_record[fact.id] = concepts
        self._states = {cid: self._state(cid, acc) for cid, acc in self._acc.items()}

    def _entry(self, concept_id: str, label: str) -> _Accumulator:
        return self._acc.setdefault(concept_id, _Accumulator(label))

    def _add_evidence(self, record: Any) -> None:
        signal = strongest_signal(record.signals) or ("exposure" if "exposure" in record.signals else None)
        concepts = _evidence_concepts(record, self._heading_labels)
        if signal is None or not concepts:
            return
        self._by_record[record.id] = tuple(cid for cid, _ in concepts)
        for concept_id, label in concepts:
            entry = self._entry(concept_id, label)
            entry.evidence[signal].append(record.id)
            entry.sources[signal].add(record.provenance.source_id or "")

    def _add_declared(self, record: Any) -> None:
        concepts = resolve_text(record.statement)
        self._by_record[record.id] = concepts
        for concept_id in concepts:
            concept = concept_by_id(concept_id)
            if concept is not None:
                self._entry(concept_id, concept.label).declared.append(record.id)

    @staticmethod
    def _state(concept_id: str, acc: _Accumulator) -> KnowledgeState:
        ordered = tuple(i for d in reversed(DIMENSIONS) for i in sorted(acc.evidence[d]))
        return KnowledgeState(
            concept_id, acc.label, {d: len(acc.evidence[d]) for d in DIMENSIONS},
            {d: len(acc.sources[d]) for d in DIMENSIONS}, len(acc.declared), ordered, tuple(sorted(acc.declared)),
        )

    def __len__(self) -> int:
        return len(self._states)

    def get(self, concept_id: str) -> KnowledgeState | None:
        return self._states.get(concept_id)

    def concepts_of(self, record_id: str) -> tuple[str, ...]:
        return self._by_record.get(record_id, ())

    def relevant(self, query: str, record_ids: Iterable[str], limit: int) -> list[KnowledgeState]:
        """Concepts named in the query first, then those of the given ranked records."""
        wanted = list(resolve_text(query))
        fallback = label_concept(query)
        if fallback is not None:
            wanted.append(fallback[0])
        for record_id in record_ids:
            wanted.extend(self.concepts_of(record_id))
        seen: list[KnowledgeState] = []
        for concept_id in dict.fromkeys(wanted):
            state = self._states.get(concept_id)
            if state is not None and (state.evidence_ids or state.declared):
                seen.append(state)
            if len(seen) >= limit:
                break
        return seen

    def top(self, limit: int) -> list[KnowledgeState]:
        """The concepts with the strongest evidence level, then the most Evidence."""
        return sorted(self._states.values(),
                      key=lambda s: (-LEVELS.index(s.level), -len(s.evidence_ids), s.label))[:limit]

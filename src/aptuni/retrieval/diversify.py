"""Order relevance-ranked Context records so distinct concepts come first (ADR-0005 2026-10-01).

A MarginNote topic reaches retrieval as an Evidence record, its derived Profile Fact, and often
nested repeats of the same path ("A › A › B"). Without this step they fill the budget with one
concept. Nothing is dropped: repeats and records beyond ``per_root`` from one notebook move after
the distinct concepts, keeping their relative rank, so a large budget still includes them.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from typing import Any

from aptuni.domain.evidence_profile import EVIDENCE_PROFILE_TYPE

PATH_SEPARATOR = "›"
DEFAULT_PER_ROOT = 3


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split()).rstrip(". ")


def concept_key(record: Any) -> str:
    """Evidence and Evidence-derived Facts share their subject; other records use their statement."""
    derived = record.record_type == "fact" and getattr(record, "type", None) == EVIDENCE_PROFILE_TYPE
    if record.record_type == "evidence" or derived:
        text = str(record.subject)
    else:
        text = str(getattr(record, "statement", None) or getattr(record, "subject", ""))
    segments: list[str] = []
    for part in (_normalize(piece) for piece in text.split(PATH_SEPARATOR)):
        if part and (not segments or segments[-1] != part):
            segments.append(part)
    return f" {PATH_SEPARATOR} ".join(segments)


def diversify[R](records: Sequence[R], per_root: int = DEFAULT_PER_ROOT) -> list[R]:
    """Distinct concepts first (at most ``per_root`` per notebook), then crowded ones, then repeats."""
    seen: set[str] = set()
    per_notebook: dict[str, int] = {}
    first: list[R] = []
    crowded: list[R] = []
    repeats: list[R] = []
    for record in records:
        key = concept_key(record)
        if key in seen:
            repeats.append(record)
            continue
        seen.add(key)
        root = key.split(f" {PATH_SEPARATOR} ")[0]
        per_notebook[root] = per_notebook.get(root, 0) + 1
        (first if per_notebook[root] <= per_root else crowded).append(record)
    return [*first, *crowded, *repeats]

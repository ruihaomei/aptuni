"""Item-level signal classifiers capped at source authority (ADR-0029 items 2–3).

Authority is a ceiling: the classifier judges what one item shows, and a source may only emit that
signal when its effective authority names ``<module>.<signal>``; otherwise the item is
``exposure``. Classifiers read only locator fields (and, for pre-ADR MarginNote Evidence, Aptuni's
own structured summary), so a judgement can be recomputed from the Vault alone.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, cast

from aptuni.domain.records import Signal

__all__ = ["CONCEPT_SCHEMA", "capped", "classified_signals", "github_concept_signal", "item_signal",
           "marginnote_signal"]

CONCEPT_SCHEMA = "github.concept"
_ANNOTATED = re.compile(r"\b(\d+) annotated\b")


def _count(value: Any) -> int:
    return value if type(value) is int and value > 0 else 0


def marginnote_signal(fields: Mapping[str, Any], summary: str | None = None) -> str:
    """``studied`` for a card that organises, collects or annotates; an isolated card is exposure."""
    annotated = fields.get("annotated")
    if annotated is None and summary:  # pre-ADR-0029 locator: read Aptuni's own summary, else 0
        match = _ANNOTATED.search(summary)
        annotated = int(match.group(1)) if match else 0
    if _count(fields.get("child_count")) >= 1 or _count(fields.get("excerpt_count")) >= 2 or _count(annotated) >= 1:
        return "studied"
    return "exposure"


def github_concept_signal(fields: Mapping[str, Any]) -> str:
    return "applied" if fields.get("usage") == "applied" else "exposure"


def capped(signal: str, module: str, authority: Iterable[str]) -> tuple[Signal, ...]:
    """The classified signal if the ceiling allows it, else exposure."""
    allowed = signal == "exposure" or f"{module}.{signal}" in set(authority)
    return (cast(Signal, signal),) if allowed else ("exposure",)


def item_signal(source_type: str, locator: Any, summary: str | None) -> str:
    """The uncapped judgement for one item of a source type."""
    extension = locator.extension
    schema = getattr(extension, "schema_name", None) or getattr(extension, "schema", "")
    if source_type == "marginnote4" and schema == "marginnote.locator":
        return marginnote_signal(extension.fields, summary)
    if source_type == "github" and schema == CONCEPT_SCHEMA:
        return github_concept_signal(extension.fields)
    return "exposure"


def classified_signals(evidence: Any, source_type: str, authority: Iterable[str]) -> tuple[Signal, ...]:
    """What a current Evidence item should carry now under the classifier and the ceiling."""
    signal = item_signal(source_type, evidence.provenance.locator, evidence.excerpt)
    return capped(signal, evidence.module, authority)

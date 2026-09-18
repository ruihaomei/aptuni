"""Disposable SQLite FTS5 implementations compared by S03."""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType


VARIANTS = ("unicode61", "trigram", "cjk_lexemes")
_SEGMENTS = re.compile(r"[a-zA-Z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]+")
_CJK = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff]+$")


@dataclass(frozen=True, slots=True)
class SearchDocument:
    doc_id: str
    text: str
    lang: str
    visible: bool = True
    current: bool = True


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _deduplicate(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def cjk_lexemes(text: str) -> list[str]:
    """Return stable ASCII terms and overlapping 2–4-character CJK lexemes."""
    lexemes: list[str] = []
    for segment in _SEGMENTS.findall(_normalize(text)):
        if not _CJK.fullmatch(segment):
            lexemes.append(segment)
            continue
        if len(segment) == 1:
            lexemes.append(segment)
            continue
        for width in range(2, min(4, len(segment)) + 1):
            lexemes.extend(segment[start : start + width] for start in range(len(segment) - width + 1))
    return _deduplicate(lexemes)


def _quoted_and(terms: Iterable[str]) -> str | None:
    safe = [term.replace('"', '""') for term in terms if term]
    if not safe:
        return None
    return " AND ".join(f'"{term}"' for term in safe)


def _query_for(variant: str, text: str) -> str | None:
    segments = _SEGMENTS.findall(_normalize(text))
    if variant == "unicode61":
        return _quoted_and(segments)
    if variant == "trigram":
        return _quoted_and(segment for segment in segments if len(segment) >= 3)
    return _quoted_and(cjk_lexemes(text))


class SqliteRetriever:
    """Small FTS5 projection with permission and current-state filters."""

    def __init__(
        self,
        variant: str,
        documents: Iterable[SearchDocument],
        database: str | Path = ":memory:",
    ) -> None:
        if variant not in VARIANTS:
            raise ValueError(f"unknown retrieval variant: {variant}")
        self.variant = variant
        self.connection = sqlite3.connect(str(database))
        tokenizer = "trigram" if variant == "trigram" else "unicode61"
        self.connection.execute(
            "CREATE VIRTUAL TABLE search USING fts5("
            "doc_id UNINDEXED, lang UNINDEXED, visible UNINDEXED, current UNINDEXED, body, "
            f"tokenize='{tokenizer}')"
        )
        rows = []
        for document in documents:
            body = " ".join(cjk_lexemes(document.text)) if variant == "cjk_lexemes" else document.text
            rows.append(
                (document.doc_id, document.lang, int(document.visible), int(document.current), body)
            )
        self.connection.executemany(
            "INSERT INTO search(doc_id, lang, visible, current, body) VALUES (?, ?, ?, ?, ?)", rows
        )
        self.connection.commit()

    def search(self, query: str, limit: int = 5) -> list[str]:
        if limit < 1:
            raise ValueError("limit must be positive")
        expression = _query_for(self.variant, query)
        if expression is None:
            return []
        rows = self.connection.execute(
            "SELECT doc_id FROM search "
            "WHERE search MATCH ? AND visible = 1 AND current = 1 "
            "ORDER BY bm25(search), doc_id LIMIT ?",
            (expression, limit),
        )
        return [str(row[0]) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SqliteRetriever:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

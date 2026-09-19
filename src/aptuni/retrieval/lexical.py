"""Deterministic bilingual lexical normalization selected by the S03 spike."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

LEXEME_VERSION = 1
_SEGMENTS = re.compile(r"[a-zA-Z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]+")
_CJK = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff]+$")


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _deduplicate(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def cjk_lexemes(text: str) -> list[str]:
    """Return stable ASCII terms and overlapping 2–4-character CJK lexemes."""
    lexemes: list[str] = []
    for segment in _SEGMENTS.findall(_normalize(text)):
        if not _CJK.fullmatch(segment) or len(segment) == 1:
            lexemes.append(segment)
            continue
        for width in range(2, min(4, len(segment)) + 1):
            lexemes.extend(segment[start : start + width] for start in range(len(segment) - width + 1))
    return _deduplicate(lexemes)


def query_expression(text: str) -> str | None:
    """Build an FTS expression from data terms only; caller text is never parsed as FTS syntax."""
    terms = [term.replace('"', '""') for term in cjk_lexemes(text) if term]
    if not terms:
        return None
    return " AND ".join(f'"{term}"' for term in terms)

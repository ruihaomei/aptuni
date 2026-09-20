"""Deterministic bilingual lexical normalization selected by the S03 spike."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Literal

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


# Function words that carry no retrieval signal in task-shaped requests ("help me prepare for ...").
STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "about", "at", "by", "from",
    "is", "are", "be", "i", "me", "my", "you", "your", "we", "our", "it", "this", "that", "what", "how",
    "why", "can", "could", "would", "should", "please", "help", "teach", "tell", "explain", "give",
    "some", "any", "do", "does", "want", "need", "like", "things", "thing",
    "我", "你", "的", "了", "是", "在", "和", "教我", "帮我", "请", "如何", "怎么", "什么", "一个", "一些",
    "我们", "你们", "我的", "你的", "可以", "这个", "那个", "需要", "想要",
})
QueryMode = Literal["all", "any"]


def _any_terms(text: str) -> tuple[list[str], list[str]]:
    terms = [term for term in cjk_lexemes(text) if term]
    filtered = [term for term in terms if term not in STOPWORDS
                and not (_CJK.fullmatch(term)
                         and any(term.startswith(word) for word in STOPWORDS if _CJK.fullmatch(word)))]
    return terms, filtered


def query_expression(text: str, mode: QueryMode = "all") -> str | None:
    """Build an FTS expression from data terms only; caller text is never parsed as FTS syntax.

    ``all`` requires every term (precise). ``any`` drops stopwords and CJK lexemes that contain a
    stopword prefix, then ORs the rest for bm25-ranked recall on task-shaped requests.
    """
    terms, filtered = _any_terms(text)
    if mode == "any":
        terms = filtered
    if not terms:
        return None
    joiner = " AND " if mode == "all" else " OR "
    return joiner.join('"' + term.replace('"', '""') + '"' for term in terms)


def fallback_expression(text: str) -> str | None:
    """Return an any-term expression only when task-language removal changed the query."""
    terms, filtered = _any_terms(text)
    if not filtered or filtered == terms:
        return None
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in filtered)

"""Deterministic bilingual lexical normalization selected by the S03 spike."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from itertools import pairwise
from typing import Literal

LEXEME_VERSION = 1
_SEGMENTS = re.compile(r"[a-zA-Z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]+")
_CJK = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff]+$")
# A keyword is a run of letters, digits and CJK; only spaces and punctuation separate keywords.
_KEYWORDS = re.compile(r"[a-zA-Z0-9\u3400-\u4dbf\u4e00-\u9fff]+")


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


def _quote(term: str) -> str:
    return '"' + term.replace('"', '""') + '"'


def _keyword_groups(text: str) -> list[list[str]]:
    """Return each distinct non-stopword keyword of the query as its own all-lexeme group."""
    groups: list[list[str]] = []
    for keyword in dict.fromkeys(_KEYWORDS.findall(_normalize(text))):
        if keyword in STOPWORDS:
            continue
        lexemes = cjk_lexemes(keyword)
        if lexemes:
            groups.append(lexemes)
    return groups


def fallback_expression(text: str) -> str | None:
    """Return the any-term expression used when the precise all-term query fills too few slots.

    Task-language requests ("help me prepare for ...", "教我...") OR their remaining lexemes. A list of
    two or more keywords ORs whole keywords: each keyword still needs every one of its lexemes, so
    a compact keyword such as "金融危机" never degrades to a fragment such as "金融" (ADR-0004).
    """
    terms, filtered = _any_terms(text)
    if filtered and filtered != terms:
        return " OR ".join(_quote(term) for term in filtered)
    groups = _keyword_groups(text)
    if len(groups) < 2:
        return None
    return " OR ".join(
        _quote(group[0]) if len(group) == 1 else "(" + " AND ".join(_quote(term) for term in group) + ")"
        for group in groups
    )


def _group_expression(group: list[str]) -> str:
    return _quote(group[0]) if len(group) == 1 else "(" + " AND ".join(_quote(term) for term in group) + ")"


def concept_expressions(concept: str) -> tuple[str | None, str | None]:
    """Return the strict and relaxed expressions for one host-supplied concept (ADR-0030).

    Strict requires every keyword of the concept. A concept of three or more keywords that matches
    nothing may relax to its adjacent keyword pairs; it never degrades to a single keyword, which is
    what lets generic words ("training", "plan") leak in the plain-query fallback (KI-018).
    """
    groups = _keyword_groups(concept)
    if not groups:
        return None, None
    strict = " AND ".join(_group_expression(group) for group in groups)
    relaxed = None
    if len(groups) >= 3:
        relaxed = " OR ".join(
            f"({_group_expression(first)} AND {_group_expression(second)})"
            for first, second in pairwise(groups)
        )
    return strict, relaxed

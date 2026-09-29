"""Rendering helpers shared by every owner-facing surface.

Any value that came from outside the core -- a folder name, a host destination, a source root -- is
data, never terminal structure. It is rendered bounded, escaped and delimited, with control and
confusable characters flagged, so a crafted name cannot forge the lines an owner reads before
confirming an irreversible action (ADR-0013 item 2).

CJK ideographs, kana and Hangul are shown as-is (Beta Day 0, 2026-09-29): they cannot imitate ASCII
structure, and an escaped Chinese path cannot be checked by the owner it belongs to. Every other
non-ASCII character -- look-alike letters, fullwidth forms, format and combining marks, unusual
spaces -- is still escaped and flagged.
"""

from __future__ import annotations

import json
import unicodedata

MAX_RENDERED = 500

# Inclusive code-point ranges shown unescaped. Deliberately excludes U+3000 (ideographic space),
# CJK punctuation, fullwidth forms (U+FF00-FFEF) and every combining or format character.
_READABLE = (
    (0x3041, 0x3096),    # Hiragana letters
    (0x30A1, 0x30FA),    # Katakana letters
    (0x30FC, 0x30FE),    # Katakana prolonged sound and iteration marks
    (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0xAC00, 0xD7A3),    # Hangul syllables
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
    (0x20000, 0x2FA1F),  # CJK Unified Ideographs Extensions B-F and supplement
)


def _readable(character: str) -> bool:
    """An assigned CJK letter that is its own NFC form: no blank boxes, no compatibility twins (Review 80 B1)."""
    point = ord(character)
    return (any(low <= point <= high for low, high in _READABLE)
            and unicodedata.category(character) in ("Lo", "Lm")
            and unicodedata.normalize("NFC", character) == character)


def _escaped(character: str) -> str:
    if _readable(character):
        return character
    return json.dumps(character, ensure_ascii=True)[1:-1]


def delimited_untrusted(value: str) -> str:
    """Render an outside-controlled name as bounded escaped data, never terminal structure."""
    bounded = value[:MAX_RENDERED]
    rendered = '"' + "".join(_escaped(character) for character in bounded) + '"'
    flags = []
    if any(ord(character) < 32 or ord(character) == 127 for character in bounded):
        flags.append("control-escaped")
    if any(ord(character) > 127 and not _readable(character) for character in bounded):
        flags.append("non-ascii/confusable-escaped")
    if len(value) > len(bounded):
        flags.append("truncated")
    return rendered + (" [" + ", ".join(flags) + "]" if flags else "")

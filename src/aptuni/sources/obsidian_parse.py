"""Bounded Obsidian note structure: frontmatter subset, wikilinks, tags and headings (ADR-0017).

Everything here reads untrusted private note text and must return only *structure*: which topics
the owner named, which notes this one points at, how the note is shaped. Property values other
than tags and aliases never leave this module, and the body excerpt is taken after the
frontmatter block is removed, so a private property cannot reach canonical identity or the
retrieval index.

The frontmatter grammar is deliberately a narrow subset rather than YAML. A full YAML parser
would add a runtime dependency whose parse surface (anchors, aliases, custom tags, deeply nested
collections) is far larger than the key names and short scalar lists this provider needs.
Anything outside the subset is reported as ``frontmatter_unsupported`` and yields no properties.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MAX_TAGS = 32
MAX_ALIASES = 16
MAX_LINKS = 64
MAX_PROPERTY_KEYS = 32
MAX_TOKEN = 128

BOM = "\ufeff"
_FENCE = "---"
_WIKILINK = re.compile(r"!?\[\[([^\[\]|#^]*)(?:[#^][^\[\]|]*)?(?:\|[^\[\]]*)?\]\]")
_INLINE_TAG = re.compile(r"(?<![\w#/])#([A-Za-zÀ-￿][\wÀ-￿/\-]*)")
_HEADING = re.compile(r"^#{1,6}\s+\S")
_CODE_FENCE = re.compile(r"^\s*(```+|~~~+)")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_SCALAR_KEY = re.compile(r"^([A-Za-z_][\w \-]*):(?:[ \t]+(.*))?$")
_LIST_ITEM = re.compile(r"^[ \t]+-[ \t]+(.+)$")
_UNSUPPORTED_SCALAR = re.compile(r"^[&*|>!]")


@dataclass(frozen=True)
class NoteStructure:
    """Bounded topology of one note; never carries a property value beyond tags and aliases."""

    tags: list[str]
    aliases: list[str]
    outbound_links: list[str]
    property_keys: list[str]
    heading_count: int
    truncated: bool
    notes: tuple[str, ...]


def sanitize_token(value: str, limit: int = MAX_TOKEN) -> str:
    """Render one untrusted token as bounded printable text, never terminal or field structure."""
    normalized = unicodedata.normalize("NFC", value)
    stripped = "".join(" " if unicodedata.category(character) in _REMOVED_CATEGORIES else character
                       for character in normalized)
    collapsed = " ".join(stripped.split())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1].rstrip() + "…"


_REMOVED_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})


def _bounded(values: list[str], limit: int) -> tuple[list[str], bool]:
    """Deduplicate in first-seen order, then cap. Order is input order, so the cap is stable."""
    seen: list[str] = []
    for value in values:
        token = sanitize_token(value)
        if token and token not in seen:
            seen.append(token)
    return seen[:limit], len(seen) > limit


def split_frontmatter(text: str) -> tuple[str | None, str, bool]:
    """Return the frontmatter block (without its fences), the body, and whether the fence is open.

    A fence only counts at the start of the text, which is what Obsidian itself requires. A
    UTF-8 BOM is removed first: without that, a BOM'd note would be classified as having no
    frontmatter and its property block would become excerpt text (Review 55 B1). Only ``---``
    terminates a block; YAML's ``...`` document-end marker does not, because Obsidian does not
    accept it and treating it as a terminator would leave the remaining properties in the body.
    An unterminated fence yields no block and an empty body, so a stray ``---`` fails closed
    instead of exposing an unparsed property block.
    """
    lines = text.removeprefix(BOM).splitlines()
    if not lines or lines[0].rstrip() != _FENCE:
        return None, text.removeprefix(BOM), False
    for index in range(1, len(lines)):
        if lines[index].rstrip() == _FENCE:
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:]), False
    return None, "", True


def body_without_frontmatter(text: str) -> str:
    return split_frontmatter(text)[1]


def decode_note(data: bytes) -> str:
    """One decode boundary for note bytes, so a BOM cannot reach a caller that forgot to strip it."""
    return data.decode("utf-8", errors="replace").removeprefix(BOM)


def parse_frontmatter(block: str) -> tuple[dict[str, list[str]], bool]:
    """Parse the narrow subset. The bool is True when the block is outside the subset."""
    values: dict[str, list[str]] = {}
    pending: str | None = None
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = _LIST_ITEM.match(line)
        if item is not None:
            if pending is None or _UNSUPPORTED_SCALAR.match(item.group(1).strip()):
                return {}, True
            values[pending].append(item.group(1).strip().strip("\"'"))
            continue
        match = _SCALAR_KEY.match(line)
        if match is None:
            return {}, True
        key, scalar = match.group(1).strip(), (match.group(2) or "").strip()
        if key in values:
            return {}, True
        if not scalar:
            values[key] = []
            pending = key
            continue
        pending = None
        if _UNSUPPORTED_SCALAR.match(scalar):
            return {}, True
        if scalar.startswith("[") and scalar.endswith("]"):
            values[key] = [part.strip().strip("\"'") for part in scalar[1:-1].split(",") if part.strip()]
        else:
            values[key] = [scalar.strip("\"'")]
    return values, False


def _body_outside_code(body: str) -> str:
    """Drop fenced blocks and inline code spans; text inside them is not structure."""
    kept: list[str] = []
    fence: str | None = None
    for line in body.splitlines():
        marker = _CODE_FENCE.match(line)
        if fence is not None:
            if marker is not None and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
            continue
        if marker is not None:
            fence = marker.group(1)
            continue
        kept.append(_INLINE_CODE.sub(" ", line))
    return "\n".join(kept)


def parse_note(text: str) -> NoteStructure:
    block, body, unterminated = split_frontmatter(text)
    unsupported = unterminated
    properties: dict[str, list[str]] = {}
    if block is not None:
        properties, unsupported = parse_frontmatter(block)

    outside = _body_outside_code(body)
    raw_tags = [*properties.get("tags", []), *properties.get("tag", []), *_INLINE_TAG.findall(outside)]
    raw_links = [_link_target(match) for match in _WIKILINK.findall(outside)]

    tags, tags_capped = _bounded(raw_tags, MAX_TAGS)
    aliases, aliases_capped = _bounded(
        [*properties.get("aliases", []), *properties.get("alias", [])], MAX_ALIASES,
    )
    links, links_capped = _bounded(raw_links, MAX_LINKS)
    keys, keys_capped = _bounded(sorted(properties), MAX_PROPERTY_KEYS)
    headings = sum(1 for line in outside.splitlines() if _HEADING.match(line))

    return NoteStructure(
        tags=tags, aliases=aliases, outbound_links=links, property_keys=keys,
        heading_count=headings,
        truncated=any((tags_capped, aliases_capped, links_capped, keys_capped)),
        notes=("frontmatter_unsupported",) if unsupported else (),
    )


def _link_target(target: str) -> str:
    """A wikilink points at a note name: drop any folder prefix and the optional `.md` suffix."""
    name = target.strip().rsplit("/", 1)[-1].strip()
    return name[:-3] if name.lower().endswith(".md") else name

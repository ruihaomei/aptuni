"""Safe, structure-preserving OPML parsing (no flattening, no DTD/entities)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from xml.etree import ElementTree

DEFAULT_MAX_NODES = 50_000
DEFAULT_MAX_DEPTH = 64
FORBIDDEN_MARKUP = ("<!doctype", "<!entity")


class OpmlError(ValueError):
    """Rejected or malformed OPML input (fixed code, never echoes content)."""


@dataclass(frozen=True)
class OutlineNode:
    text: str
    attributes: dict[str, str]
    children: tuple[OutlineNode, ...] = field(default=())


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def parse_opml(
    text: str, max_nodes: int = DEFAULT_MAX_NODES, max_depth: int = DEFAULT_MAX_DEPTH
) -> tuple[OutlineNode, ...]:
    lowered = text.lower()
    if any(marker in lowered for marker in FORBIDDEN_MARKUP):
        raise OpmlError("opml_dtd_forbidden")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise OpmlError("opml_malformed") from error
    body = root.find("body") if root.tag == "opml" else None
    if body is None:
        raise OpmlError("opml_body_missing")
    counter = [0]
    return tuple(_convert(child, 1, counter, max_nodes, max_depth) for child in body if child.tag == "outline")


def _convert(
    element: ElementTree.Element, depth: int, counter: list[int], max_nodes: int, max_depth: int
) -> OutlineNode:
    counter[0] += 1
    if counter[0] > max_nodes:
        raise OpmlError("opml_node_limit")
    if depth > max_depth:
        raise OpmlError("opml_depth_limit")
    attributes = {key: value for key, value in element.attrib.items() if key != "text"}
    children = tuple(
        _convert(child, depth + 1, counter, max_nodes, max_depth) for child in element if child.tag == "outline"
    )
    return OutlineNode(normalize_text(element.attrib.get("text", "")), attributes, children)

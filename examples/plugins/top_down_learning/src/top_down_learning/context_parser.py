"""Strict parser for the portable ``aptuni.top-down-learning.context@1`` Markdown (ADR-0026)."""

from __future__ import annotations

import json
from typing import get_args

from top_down_learning.learning_context import (
    EMPTY,
    FRONTMATTER_KEYS,
    LEVEL_HEADINGS,
    MAX_CONTEXT_BYTES,
    POSITION_SEP,
    SCHEMA,
    SECTION_ORDER,
    SEP,
    Basis,
    ConceptNote,
    Delivery,
    Demonstration,
    DynamicState,
    FoundationItem,
    LearningContext,
    PrerequisiteNode,
    StableState,
    invalid_context,
    validate_context,
)


def _frontmatter(lines: list[str]) -> tuple[dict[str, object], int]:
    if not lines or lines[0] != "---":
        raise invalid_context("frontmatter must start the file")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise invalid_context("frontmatter is not closed") from error
    values: dict[str, object] = {}
    for raw in lines[1:end]:
        key, colon, value = raw.partition(": ")
        if not colon or key not in FRONTMATTER_KEYS or key in values:
            raise invalid_context(f"frontmatter key {key!r} is unknown or repeated")
        try:
            values[key] = json.loads(value)
        except json.JSONDecodeError as error:
            raise invalid_context(f"frontmatter value for {key} is not a JSON literal") from error
    if tuple(values) != FRONTMATTER_KEYS:
        raise invalid_context("frontmatter keys are missing or out of order")
    if values["schema"] != SCHEMA:
        raise invalid_context(f"schema must be {SCHEMA}")
    if not isinstance(values["user_verified"], bool):
        raise invalid_context("frontmatter user_verified must be a boolean")
    for key in ("target", "created_at", "updated_at", "preferred_delivery"):
        if not isinstance(values[key], str):
            raise invalid_context(f"frontmatter {key} must be a string")
    if values["verified_digest"] is not None and not isinstance(values["verified_digest"], str):
        raise invalid_context("frontmatter verified_digest must be a string or null")
    if values["preferred_delivery"] not in get_args(Delivery):
        raise invalid_context("frontmatter delivery mode is unknown")
    return values, end + 1


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    bodies: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("#"):
            if line not in SECTION_ORDER or line in bodies:
                raise invalid_context(f"unknown or repeated section {line[:60]!r}")
            current = line
            bodies[current] = []
        elif current is not None:
            bodies[current].append(line)
        elif line.strip():
            raise invalid_context("text before the first section")
    if tuple(bodies) != SECTION_ORDER:
        missing = [heading for heading in SECTION_ORDER if heading not in bodies]
        raise invalid_context(f"section missing or out of order: {missing[0] if missing else 'order'}")
    return bodies


def _body(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    return "" if text == EMPTY else text


def _list(lines: list[str], what: str) -> list[str]:
    text = _body(lines)
    if not text:
        return []
    values = []
    for line in text.split("\n"):
        if not line.startswith("- "):
            raise invalid_context(f"{what} must be a bullet list")
        values.append(line[2:])
    return values


def _fields(value: str, count: int, what: str) -> list[str]:
    parts = value.split(SEP)
    if len(parts) != count:
        raise invalid_context(f"{what} bullet has the wrong shape")
    return parts


def _parse_foundation(sections: dict[str, list[str]]) -> tuple[FoundationItem, ...]:
    foundation: list[FoundationItem] = []
    for heading, level in LEVEL_HEADINGS.items():
        for value in _list(sections[f"## {heading}"], "foundation"):
            concept, basis = _fields(value, 2, "foundation")
            if basis not in get_args(Basis):
                raise invalid_context("foundation basis is unknown")
            foundation.append(FoundationItem(concept, level, basis))  # type: ignore[arg-type]
    return tuple(foundation)


def _parse_depth(lines: list[str]) -> tuple[str, str]:
    values = {"Depth": "", "Deliverable": ""}
    for value in _list(lines, "depth"):
        label, _, rest = value.partition(": ")
        if label not in values:
            raise invalid_context("depth/deliverable bullet has the wrong shape")
        values[label] = rest
    return values["Depth"], values["Deliverable"]


def _parse_map(lines: list[str]) -> tuple[PrerequisiteNode, ...]:
    nodes = []
    for value in _list(lines, "prerequisite map"):
        concept, required_for, status = _fields(value, 3, "prerequisite map")
        if not required_for.startswith("for: "):
            raise invalid_context("prerequisite map bullet has the wrong shape")
        nodes.append(PrerequisiteNode(concept, required_for[5:], status))  # type: ignore[arg-type]
    return tuple(nodes)


def _parse_path(lines: list[str]) -> tuple[str, ...]:
    path = []
    for index, line in enumerate(_body(lines).split("\n") if _body(lines) else [], 1):
        prefix = f"{index}. "
        if not line.startswith(prefix):
            raise invalid_context("learning path must be a numbered list")
        path.append(line[len(prefix):])
    return tuple(path)


def _parse_position(lines: list[str]) -> tuple[str, ...]:
    position: tuple[str, ...] = ()
    for value in _list(lines, "progress"):
        if not value.startswith("Position: "):
            raise invalid_context("progress bullet has the wrong shape")
        position = tuple(value[len("Position: "):].split(POSITION_SEP))
    return position


def parse_context(text: str) -> LearningContext:
    """Strictly parse a portable learning context; raise ``ContextError`` with a clear reason."""
    try:
        size = len(text.encode()) if isinstance(text, str) else MAX_CONTEXT_BYTES + 1
    except UnicodeEncodeError as error:
        raise invalid_context("context is not valid UTF-8 text") from error
    if size > MAX_CONTEXT_BYTES:
        raise invalid_context("context is too large")
    lines = text.replace("\r\n", "\n").split("\n")
    front, start = _frontmatter(lines)
    sections = _split_sections(lines[start:])
    depth, deliverable = _parse_depth(sections["## Intended Depth / Deliverable"])
    delivery = _body(sections["# Delivery Mode"])
    if delivery != front["preferred_delivery"]:
        raise invalid_context("delivery mode section disagrees with frontmatter")
    target = _body(sections["## Target"])
    if target != front["target"]:
        raise invalid_context("target section disagrees with frontmatter")
    context = LearningContext(
        stable=StableState(
            target=target,
            success_criteria=tuple(_list(sections["## Success Criteria"], "success criteria")),
            depth=depth,
            deliverable=deliverable,
            foundation=_parse_foundation(sections),
            preferences=tuple(_list(sections["# Relevant Learning Preferences"], "preferences")),
            constraints=tuple(_list(sections["# Constraints"], "constraints")),
        ),
        dynamic=DynamicState(
            diagnostics=tuple(_list(sections["# Diagnostic Findings"], "diagnostics")),
            prerequisite_map=_parse_map(sections["# Minimal Prerequisite Map"]),
            path=_parse_path(sections["# Recommended Learning Path"]),
            strategy=_body(sections["# Personalized Teaching Strategy"]),
            teaching_contract=_body(sections["# Teaching Contract / Harness"]),
            position=_parse_position(sections["# Current Progress"]),
            demonstrations=tuple(
                Demonstration(*_fields(value, 3, "demonstration"))
                for value in _list(sections["# Demonstrated Understanding"], "demonstrations")
            ),
            misconceptions=tuple(
                ConceptNote(*_fields(value, 2, "misconception"))
                for value in _list(sections["# Misconceptions"], "misconceptions")
            ),
            gaps=tuple(_list(sections["# Open Gaps"], "gaps")),
            next_step=_body(sections["# Next Recommended Step"]),
            cloud_guidance=_body(sections["# Cloud Teaching Guidance"]),
        ),
        created_at=str(front["created_at"]),
        updated_at=str(front["updated_at"]),
        user_verified=bool(front["user_verified"]),
        verified_digest=front["verified_digest"],  # type: ignore[arg-type]
        preferred_delivery=front["preferred_delivery"],  # type: ignore[arg-type]
        last_verification=_body(sections["# Last User Verification"]) or None,
    )
    validate_context(context)
    return context

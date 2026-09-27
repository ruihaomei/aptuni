"""Portable, user-verifiable ``aptuni.top-down-learning.context@1`` artifact (ADR-0026).

The Markdown file is the learner's continuity layer. It must stay readable without Aptuni, so the
format is fixed, strictly parsed and bounded. Stable learner facts are digest-bound to the learner's
verification; dynamic progress may change without re-verification.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, replace
from typing import Literal, get_args

SCHEMA = "aptuni.top-down-learning.context@1"
CONTEXT_FILENAME = "top_down_learning_context.md"
MAX_CONTEXT_BYTES = 65536
MAX_ITEMS = 40
MAX_ITEM_CHARS = 300
MAX_TEXT_CHARS = 4000
MAX_CONCEPT_CHARS = 80
MAX_DEPTH = 5
EMPTY = "_None yet._"
SEP = " — "
POSITION_SEP = " › "

Level = Literal["strong", "familiar", "unknown"]
Basis = Literal["learner-stated", "aptuni-inferred", "diagnostic"]
NodeStatus = Literal["known", "needed", "demonstrated"]
Delivery = Literal["local", "cloud", "undecided"]
LEVEL_HEADINGS: dict[str, Level] = {
    "Strong": "strong", "Familiar / Needs Refresh": "familiar", "Unknown / To Verify": "unknown",
}


class ContextError(ValueError):
    """A portable learning context is malformed, unsafe or used out of order."""


def invalid_context(reason: str) -> ContextError:
    return ContextError(f"top_down_context_invalid: {reason}")


@dataclass(frozen=True)
class FoundationItem:
    concept: str
    level: Level
    basis: Basis


@dataclass(frozen=True)
class PrerequisiteNode:
    concept: str
    required_for: str
    status: NodeStatus


@dataclass(frozen=True)
class Demonstration:
    concept: str
    summary: str
    at: str


@dataclass(frozen=True)
class ConceptNote:
    concept: str
    summary: str


@dataclass(frozen=True)
class StableState:
    target: str
    success_criteria: tuple[str, ...] = ()
    depth: str = ""
    deliverable: str = ""
    foundation: tuple[FoundationItem, ...] = ()
    preferences: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()


@dataclass(frozen=True)
class DynamicState:
    diagnostics: tuple[str, ...] = ()
    prerequisite_map: tuple[PrerequisiteNode, ...] = ()
    path: tuple[str, ...] = ()
    strategy: str = ""
    teaching_contract: str = ""
    position: tuple[str, ...] = ()
    demonstrations: tuple[Demonstration, ...] = ()
    misconceptions: tuple[ConceptNote, ...] = ()
    gaps: tuple[str, ...] = ()
    next_step: str = ""
    cloud_guidance: str = ""


@dataclass(frozen=True)
class LearningContext:
    stable: StableState
    dynamic: DynamicState = field(default_factory=DynamicState)
    created_at: str = ""
    updated_at: str = ""
    user_verified: bool = False
    verified_digest: str | None = None
    preferred_delivery: Delivery = "undecided"
    last_verification: str | None = None


def canonical_foundation(items: tuple[FoundationItem, ...]) -> tuple[FoundationItem, ...]:
    """Group foundation by level (strong, familiar, unknown), keeping order within each group."""
    order = tuple(LEVEL_HEADINGS.values())
    return tuple(sorted(items, key=lambda item: order.index(item.level)))


def stable_digest(stable: StableState) -> str:
    stable = replace(stable, foundation=canonical_foundation(stable.foundation))
    payload = json.dumps(asdict(stable), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def is_verified(context: LearningContext) -> bool:
    return context.user_verified and context.verified_digest == stable_digest(context.stable)


# --- validation -------------------------------------------------------------------------------

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")


def _line(value: str, what: str, limit: int = MAX_ITEM_CHARS) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise invalid_context(f"{what} must be 1-{limit} characters")
    if "\n" in value or _CONTROL.search(value) or value.lstrip().startswith(("#", "---")):
        raise invalid_context(f"{what} must be one plain line")
    if value != value.strip() or value == EMPTY:
        raise invalid_context(f"{what} must be trimmed plain text")
    return value


def _field(value: str, what: str, limit: int = MAX_ITEM_CHARS) -> str:
    """A value rendered inside a separated bullet; it must not contain the separator."""
    value = _line(value, what, limit)
    if SEP in value:
        raise invalid_context(f"{what} must not contain the separator {SEP.strip()!r}")
    return value


def _concept(value: str, what: str = "concept") -> str:
    value = _line(value, what, MAX_CONCEPT_CHARS)
    if SEP.strip() in value or POSITION_SEP.strip() in value:
        raise invalid_context(f"{what} must not contain separators")
    return value


def _text(value: str, what: str) -> str:
    if len(value) > MAX_TEXT_CHARS or _CONTROL.search(value.replace("\n", " ")):
        raise invalid_context(f"{what} must be at most {MAX_TEXT_CHARS} plain characters")
    for line in value.splitlines():
        if line.lstrip().startswith(("#", "---")):
            raise invalid_context(f"{what} must not contain headings")
    if value != value.strip() or value == EMPTY:
        raise invalid_context(f"{what} must be trimmed plain text")
    return value


def _items(values: tuple[str, ...], what: str) -> tuple[str, ...]:
    if len(values) > MAX_ITEMS:
        raise invalid_context(f"{what} has more than {MAX_ITEMS} items")
    return tuple(_line(value, what) for value in values)


def validate_context(context: LearningContext) -> None:
    _check_stable(context.stable)
    _check_dynamic(context.dynamic, context.stable.target)
    if context.preferred_delivery not in get_args(Delivery):
        raise invalid_context("delivery mode is unknown")
    if context.last_verification is not None:
        _line(context.last_verification, "last verification")
    for value, what in ((context.created_at, "created_at"), (context.updated_at, "updated_at")):
        if value:
            _field(value, what, 40)


def _check_stable(stable: StableState) -> None:
    _line(stable.target, "target", 500)
    if POSITION_SEP.strip() in stable.target:
        raise invalid_context("target must not contain the position separator")
    _items(stable.success_criteria, "success criteria")
    _items(stable.preferences, "preferences")
    _items(stable.constraints, "constraints")
    for value, what in ((stable.depth, "depth"), (stable.deliverable, "deliverable")):
        if value:
            _line(value, what)
    if len(stable.foundation) > MAX_ITEMS:
        raise invalid_context(f"foundation has more than {MAX_ITEMS} items")
    if stable.foundation != canonical_foundation(stable.foundation):
        raise invalid_context("foundation must be grouped strong, familiar, unknown")
    if len({item.concept for item in stable.foundation}) != len(stable.foundation):
        raise invalid_context("foundation concepts must be unique")
    for item in stable.foundation:
        _concept(item.concept)
        if item.level not in get_args(Level) or item.basis not in get_args(Basis):
            raise invalid_context("foundation level or basis is unknown")


def _check_dynamic(dynamic: DynamicState, target: str) -> None:
    for sequence, what in (
        (dynamic.prerequisite_map, "prerequisite map"), (dynamic.path, "path"),
        (dynamic.demonstrations, "demonstrations"), (dynamic.misconceptions, "misconceptions"),
    ):
        if len(sequence) > MAX_ITEMS:
            raise invalid_context(f"{what} has more than {MAX_ITEMS} items")
    for node in dynamic.prerequisite_map:
        _concept(node.concept)
        _concept(node.required_for, "required_for")
        if node.status not in get_args(NodeStatus):
            raise invalid_context("prerequisite status is unknown")
    for concept in dynamic.path:
        _concept(concept, "path concept")
    _check_position(dynamic, target)
    _check_items_and_text(dynamic)


def _check_position(dynamic: DynamicState, target: str) -> None:
    if len(dynamic.position) > MAX_DEPTH:
        raise invalid_context(f"position is deeper than {MAX_DEPTH}")
    mapped = {node.concept for node in dynamic.prerequisite_map}
    for concept in dynamic.position[1:]:
        _concept(concept, "position concept")
        if concept not in mapped:
            raise invalid_context("position concepts must be in the prerequisite map")
    if len(set(dynamic.position)) != len(dynamic.position):
        raise invalid_context("position concepts must be unique")
    if dynamic.position and dynamic.position[0] != target:
        raise invalid_context("position must start at the target")


def _check_items_and_text(dynamic: DynamicState) -> None:
    for demo in dynamic.demonstrations:
        _concept(demo.concept)
        _field(demo.summary, "demonstration")
        _field(demo.at, "timestamp", 40)
    for note in dynamic.misconceptions:
        _concept(note.concept)
        _field(note.summary, "misconception")
    _items(dynamic.diagnostics, "diagnostics")
    _items(dynamic.gaps, "gaps")
    for value, what in (
        (dynamic.strategy, "strategy"), (dynamic.teaching_contract, "teaching contract"),
        (dynamic.next_step, "next step"), (dynamic.cloud_guidance, "cloud guidance"),
    ):
        _text(value, what)


# --- rendering --------------------------------------------------------------------------------

def _bullets(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else EMPTY


def _block(value: str) -> str:
    return value if value else EMPTY


def _sections(context: LearningContext) -> list[tuple[str, str | None]]:
    stable, dynamic = context.stable, context.dynamic
    depth = [f"Depth: {stable.depth}"] if stable.depth else []
    depth += [f"Deliverable: {stable.deliverable}"] if stable.deliverable else []
    by_level = {
        heading: [f"{item.concept}{SEP}{item.basis}" for item in stable.foundation if item.level == level]
        for heading, level in LEVEL_HEADINGS.items()
    }
    position = [f"Position: {POSITION_SEP.join(dynamic.position)}"] if dynamic.position else []
    return [
        ("# Learning Target", None),
        ("## Target", stable.target),
        ("## Success Criteria", _bullets(list(stable.success_criteria))),
        ("## Intended Depth / Deliverable", _bullets(depth)),
        ("# Relevant Foundation", None),
        *((f"## {heading}", _bullets(values)) for heading, values in by_level.items()),
        ("# Relevant Learning Preferences", _bullets(list(stable.preferences))),
        ("# Constraints", _bullets(list(stable.constraints))),
        ("# Diagnostic Findings", _bullets(list(dynamic.diagnostics))),
        ("# Minimal Prerequisite Map", _bullets([
            f"{node.concept}{SEP}for: {node.required_for}{SEP}{node.status}" for node in dynamic.prerequisite_map
        ])),
        ("# Recommended Learning Path", "\n".join(
            f"{index}. {concept}" for index, concept in enumerate(dynamic.path, 1)
        ) or EMPTY),
        ("# Delivery Mode", context.preferred_delivery),
        ("# Personalized Teaching Strategy", _block(dynamic.strategy)),
        ("# Teaching Contract / Harness", _block(dynamic.teaching_contract)),
        ("# Current Progress", _bullets(position)),
        ("# Demonstrated Understanding", _bullets([
            f"{demo.concept}{SEP}{demo.summary}{SEP}{demo.at}" for demo in dynamic.demonstrations
        ])),
        ("# Misconceptions", _bullets([f"{note.concept}{SEP}{note.summary}" for note in dynamic.misconceptions])),
        ("# Open Gaps", _bullets(list(dynamic.gaps))),
        ("# Next Recommended Step", _block(dynamic.next_step)),
        ("# Cloud Teaching Guidance", _block(dynamic.cloud_guidance)),
        ("# Last User Verification", _block(context.last_verification or "")),
    ]


SECTION_ORDER = tuple(heading for heading, _ in _sections(LearningContext(StableState("x"))))
FRONTMATTER_KEYS = (
    "schema", "target", "created_at", "updated_at", "user_verified", "verified_digest", "preferred_delivery",
)


def render_context(context: LearningContext) -> str:
    validate_context(context)
    front = {
        "schema": SCHEMA, "target": context.stable.target, "created_at": context.created_at,
        "updated_at": context.updated_at, "user_verified": context.user_verified,
        "verified_digest": context.verified_digest, "preferred_delivery": context.preferred_delivery,
    }
    lines = ["---", *(f"{key}: {json.dumps(front[key], ensure_ascii=False)}" for key in FRONTMATTER_KEYS), "---"]
    for heading, body in _sections(context):
        lines += ["", heading]
        if body is not None:
            lines += ["", body]
    text = "\n".join(lines) + "\n"
    if len(text.encode()) > MAX_CONTEXT_BYTES:
        raise invalid_context("context is too large")
    # The parser imports this module, so import it here; every written file must read back exactly.
    from top_down_learning.context_parser import parse_context  # noqa: PLC0415

    if parse_context(text) != context:
        raise invalid_context("context does not round-trip")
    return text

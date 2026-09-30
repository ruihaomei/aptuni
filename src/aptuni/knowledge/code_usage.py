"""Per-file concept usage levels for GitHub Standard (ADR-0029 item 3).

``applied`` needs the file to import a concept's library *and* construct or call it (plus, where the
registry says so, a training or inference call). An import alone is ``imported``, a manifest entry
is ``declared`` and a README/docs mention is ``mentioned``; only ``applied`` can become the
``applied`` signal. Nothing here keeps any code text.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import PurePosixPath

from aptuni.knowledge.concepts import CONCEPTS, Concept, normalize

__all__ = ["RULES_VERSION", "USAGE_LEVELS", "file_usage", "is_scanned", "strongest_usage"]

#: Bump when the registry or a rule changes, so cached per-blob usage is recomputed (Review 85 N3).
RULES_VERSION = 1

USAGE_LEVELS = ("applied", "imported", "declared", "mentioned")  # strongest first
MANIFEST_NAMES = frozenset({"pyproject.toml", "package.json", "requirements.txt", "cargo.toml", "go.mod",
                            "setup.cfg", "pom.xml", "build.gradle", "environment.yml", "environment.yaml"})
CODE_SUFFIXES = frozenset({".py", ".ipynb", ".js", ".ts", ".jsx", ".tsx"})
DOC_SUFFIXES = frozenset({".md", ".rst", ".txt"})
MAX_SCAN_CHARS = 1_000_000


def strongest_usage(levels: set[str] | list[str] | tuple[str, ...]) -> str | None:
    present = set(levels)
    return next((level for level in USAGE_LEVELS if level in present), None)


@cache
def _import_pattern(root: str) -> re.Pattern[str]:
    name = re.escape(root)
    python = rf"(?:^|[\s\"'])(?:import|from)\s+{name}(?=[\s.,;\"'\\]|$)"
    javascript = rf"(?:require\(\s*|from\s+)[\"']{name}(?:/[^\"']*)?[\"']"
    return re.compile(f"{python}|{javascript}", re.MULTILINE)


@cache
def _package_pattern(package: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_.\-]){re.escape(package)}(?![A-Za-z0-9_\-])", re.IGNORECASE)


@cache
def _compiled(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern) for pattern in patterns)


def _applied(concept: Concept, text: str) -> bool:
    if not any(p.search(text) for p in _compiled(concept.calls)):
        return False
    return not concept.operates or any(p.search(text) for p in _compiled(concept.operates))


def _code_usage(concept: Concept, text: str) -> str | None:
    """A library concept counts an import; a technique sharing a library (random forest) needs a call."""
    if not concept.imports or not any(_import_pattern(root).search(text) for root in concept.imports):
        return None
    if concept.calls and _applied(concept, text):
        return "applied"
    return "imported" if concept.packages else None


def _mentions(concept: Concept, normal: str) -> bool:
    if not concept.text:
        return False
    padded = f" {normal} "
    return any(f" {alias} " in padded for alias in (normalize(a) for a in (concept.label, *concept.aliases)) if alias)


def is_scanned(path: str) -> bool:
    """Only manifests, code and documentation can show concept usage; nothing else is read for it."""
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    return name in MANIFEST_NAMES or suffix in CODE_SUFFIXES or suffix in DOC_SUFFIXES or name.startswith("readme")


def file_usage(path: str, text: str) -> dict[str, str]:
    """Concept id -> usage level for one selected file (manifest, code or documentation)."""
    text = text[:MAX_SCAN_CHARS]
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    found: dict[str, str] = {}
    if name in MANIFEST_NAMES:
        for concept in CONCEPTS:
            if any(_package_pattern(package).search(text) for package in concept.packages):
                found[concept.id] = "declared"
    elif suffix in CODE_SUFFIXES:
        for concept in CONCEPTS:
            level = _code_usage(concept, text)
            if level is not None:
                found[concept.id] = level
    elif suffix in DOC_SUFFIXES or name.startswith("readme"):
        normal = normalize(text)
        for concept in CONCEPTS:
            if _mentions(concept, normal):
                found[concept.id] = "mentioned"
    return found

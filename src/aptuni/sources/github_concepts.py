"""GitHub Standard concept items: per-repository concept usage (ADR-0029 item 3).

Next to its file items, a GitHub Standard snapshot carries one ``github.concept@1`` item per concept
the selected files show: the strongest usage level (``applied`` > ``imported`` > ``declared`` >
``mentioned``), how many files show each level and at most five paths. The per-file levels are cached
in the non-canonical source state by blob id, so an unchanged file is never fetched again for this.
Items are keyed by concept id; partial coverage never proves that a concept disappeared.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from aptuni.knowledge.classify import CONCEPT_SCHEMA
from aptuni.knowledge.code_usage import RULES_VERSION, USAGE_LEVELS, file_usage, is_scanned, strongest_usage
from aptuni.knowledge.concepts import concept_by_id
from aptuni.sources.records import Extension, Operation, Snapshot, SnapshotItem, SourceLocator, canonical_json

__all__ = ["CONCEPT_VERSION", "ConceptScan", "concept_excerpt", "is_concept_item", "scan_concepts"]

CONCEPT_VERSION = 1
MAX_PATHS = 5
FILE_SCHEMA = "github.locator"
CACHE_KEY = "concept_features"


@dataclass(frozen=True)
class ConceptScan:
    items: tuple[SnapshotItem, ...]
    operations: tuple[Operation, ...]
    cache: dict[str, Any]


def is_concept_item(item: SnapshotItem) -> bool:
    return item.locator.extension.schema == CONCEPT_SCHEMA


def _features(files: list[tuple[str, str]], cache: Mapping[str, Any],
              fetch: Callable[[str], bytes]) -> dict[str, Any]:
    """path -> {"blob", "rules", "usage"}; a cached entry is reused only for the same blob and rules."""
    features: dict[str, Any] = {}
    for path, blob in files:
        if not is_scanned(path):
            continue
        cached = cache.get(path)
        if (isinstance(cached, dict) and cached.get("blob") == blob and cached.get("rules") == RULES_VERSION
                and isinstance(cached.get("usage"), dict)):
            features[path] = cached
            continue
        text = fetch(blob).decode("utf-8", errors="replace")
        features[path] = {"blob": blob, "rules": RULES_VERSION, "usage": file_usage(path, text)}
    return features


def _observations(features: Mapping[str, Any], repository_id: int, owner_name: str) -> dict[str, dict[str, Any]]:
    by_concept: dict[str, dict[str, list[str]]] = {}
    for path in sorted(features):
        for concept_id, level in sorted(features[path]["usage"].items()):
            if level in USAGE_LEVELS and concept_by_id(concept_id) is not None:
                by_concept.setdefault(concept_id, {}).setdefault(level, []).append(path)
    observed: dict[str, dict[str, Any]] = {}
    for concept_id, levels in by_concept.items():
        paths = [path for level in USAGE_LEVELS for path in levels.get(level, [])][:MAX_PATHS]
        observed[concept_id] = {
            "concept_id": concept_id, "repository_id": repository_id, "owner_name": owner_name,
            "usage": strongest_usage(list(levels)), "files": {level: len(levels[level]) for level in sorted(levels)},
            "paths": paths,
        }
    return observed


def _content_hash(fields: Mapping[str, Any]) -> str:
    body = {key: fields[key] for key in ("concept_id", "usage", "files", "paths")}
    return "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def scan_concepts(source_id: str, previous: Snapshot | None, files: list[tuple[str, str]], coverage: str,
                  cache: Mapping[str, Any], fetch: Callable[[str], bytes], repository_id: int,
                  owner_name: str) -> ConceptScan:
    """Diff this sync's concept items against the previous snapshot's by concept id."""
    features = _features(files, cache, fetch)
    observed = _observations(features, repository_id, owner_name)
    prior = {item.locator.extension.fields["concept_id"]: item
             for item in (previous.items if previous else ()) if is_concept_item(item)}
    items: list[SnapshotItem] = []
    ops: list[Operation] = []
    for concept_id in sorted(observed):
        fields = observed[concept_id]
        locator = SourceLocator(source_id, "github", f"concept:{concept_id}",
                                Extension(CONCEPT_SCHEMA, CONCEPT_VERSION, fields))
        item = SnapshotItem(locator, _content_hash(fields))
        items.append(item)
        before = prior.get(concept_id)
        if before is None:
            ops.append(Operation.add(locator, item.content_hash))
        elif before.content_hash != item.content_hash:
            ops.append(Operation.modify(before.locator, locator, item.content_hash, reasons=("usage_changed",)))
    for concept_id, before in sorted(prior.items()):
        if concept_id in observed:
            continue
        if coverage == "complete":
            ops.append(Operation.remove(before.locator.subject_id, before.locator, before.content_hash,
                                        reasons=("concept_no_longer_observed",)))
        else:
            items.append(before)  # not observed under partial coverage is not gone
    return ConceptScan(tuple(items), tuple(ops), {CACHE_KEY: features})


def concept_excerpt(fields: Mapping[str, Any]) -> str:
    """A bounded, code-free summary: usage level, file counts per level and a few paths."""
    concept = concept_by_id(str(fields.get("concept_id", "")))
    label = concept.label if concept is not None else str(fields.get("concept_id", ""))
    files = fields.get("files", {})
    counts = ", ".join(f"{level} in {files[level]} file{'s' if files[level] != 1 else ''}"
                       for level in USAGE_LEVELS if isinstance(files, dict) and files.get(level))
    paths = ", ".join(str(path) for path in fields.get("paths", []))
    text = f"{label} in {fields.get('owner_name', 'repository')}: {counts}" + (f" ({paths})" if paths else "")
    return text[:280]

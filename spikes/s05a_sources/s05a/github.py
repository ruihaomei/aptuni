"""Fixture-grade GitHub Standard scan over a Git Trees API-shaped response.

Identity: ``repository_id`` anchors the source (owner/name may change); the
resolved commit makes a snapshot reproducible; ``path`` is the item key and the
blob SHA is content identity only. Standard mode selects a bounded, sticky,
deterministic subset. A truncated tree or an unselected-but-present item means
coverage is partial, which never proves disappearance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from s05a.records import CandidateDelta, Snapshot
from s05a.reconcile import KeyedSpec, Observed, reconcile_keyed

MANIFESTS = frozenset({"pyproject.toml", "package.json", "requirements.txt", "cargo.toml", "go.mod",
                       "setup.cfg", "pom.xml", "build.gradle"})
SOURCE_SUFFIXES = frozenset({".py", ".ts", ".js", ".rs", ".go", ".java", ".ipynb", ".r", ".jl"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DEFAULT_BUDGET = 40


class SourceIdentityError(ValueError):
    """The observed repository is not the configured source (fixed code only)."""


@dataclass(frozen=True)
class GitHubScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]
    repository_id: int
    notes: tuple[str, ...]


def _selection_reason(path: str) -> tuple[int, str]:
    name = PurePosixPath(path).name.lower()
    if name.startswith("readme"):
        return 0, "readme"
    if name in MANIFESTS:
        return 1, "manifest"
    if PurePosixPath(name).suffix in SOURCE_SUFFIXES:
        return 2, "representative_source"
    return 3, "other"


def _validated(data: dict[str, Any]) -> tuple[int, str, str, bool, dict[str, str]]:
    repository_id = data.get("repository_id")
    commit = str(data.get("commit", ""))
    if not isinstance(repository_id, int) or not SHA_RE.match(commit):
        raise SourceIdentityError("github_response_invalid")
    blobs: dict[str, str] = {}
    for entry in data.get("tree", []):
        if entry.get("type") != "blob":
            continue
        sha = str(entry.get("sha", ""))
        if not SHA_RE.match(sha):
            raise SourceIdentityError("github_blob_sha_invalid")
        blobs[str(entry["path"])] = sha
    return repository_id, commit, str(data.get("full_name", "")), bool(data.get("truncated")), blobs


def scan_github(
    data: dict[str, Any],
    source_id: str,
    previous: GitHubScan | None,
    parser: tuple[str, str],
    budget: int = DEFAULT_BUDGET,
) -> GitHubScan:
    repository_id, commit, full_name, truncated, blobs = _validated(data)
    if previous is not None and previous.repository_id != repository_id:
        raise SourceIdentityError("repository_identity_changed")

    previous_reasons = {
        item.locator.extension.fields["path"]: item.locator.extension.fields["selection_reason"]
        for item in (previous.snapshot.items if previous else ())
    }
    sticky = sorted(path for path in previous_reasons if path in blobs)
    # A known item renamed out of its path keeps first claim on a budget slot (review F3).
    vanished_blobs = {
        item.locator.extension.fields["blob"]
        for item in (previous.snapshot.items if previous else ())
        if not item.held and item.locator.extension.fields["path"] not in blobs
    }
    fresh = sorted((path for path in blobs if path not in previous_reasons),
                   key=lambda path: (blobs[path] not in vanished_blobs, _selection_reason(path)[0],
                                     path.count("/"), path))
    selected = (sticky + fresh)[:budget]
    notes = {"tree_truncated"} if truncated else set()
    dropped = set(sticky) - set(selected)
    if dropped:
        notes.add("selection_budget_dropped_known_items")
    coverage = "partial" if truncated or dropped else "complete"

    observed = [
        Observed(path, "gitblob:" + blobs[path], {
            "repository_id": repository_id,
            "commit": commit,
            "blob": blobs[path],
            "owner_name": full_name,
            "mode": "standard",
            "selection_reason": previous_reasons.get(path, _selection_reason(path)[1]),
        })
        for path in selected
    ]
    spec = KeyedSpec(source_id, "github", "github.locator", 1, "path")
    parser_changed = previous is not None and previous.parser != parser
    result = reconcile_keyed(spec, previous.snapshot if previous else None, observed, coverage, parser_changed)
    delta = CandidateDelta.build(
        source_id,
        previous.snapshot.snapshot_id if previous else None,
        result.snapshot.snapshot_id,
        parser,
        result.operations,
    )
    return GitHubScan(result.snapshot, delta, parser, repository_id, tuple(sorted(notes)))

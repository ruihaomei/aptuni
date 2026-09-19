"""Fixture-grade Folder SourceProvider scan (S05A identity only; S05B covers admission)."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from s05a.records import CandidateDelta, Snapshot
from s05a.reconcile import KeyedSpec, Observed, reconcile_keyed

EXCLUDED_DIRS = frozenset({".git", ".hg", ".svn", "__pycache__", "node_modules"})
DEFAULT_MAX_FILES = 10_000


@dataclass(frozen=True)
class FolderScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]
    notes: tuple[str, ...]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _walk(root: Path, max_files: int) -> tuple[list[Observed], str, set[str]]:
    real_root = root.resolve()
    observed: list[Observed] = []
    notes: set[str] = set()
    coverage = "complete"
    for directory, dirnames, filenames in os.walk(real_root, followlinks=False):
        base = Path(directory)
        kept = []
        for name in sorted(dirnames):
            if name in EXCLUDED_DIRS:
                notes.add("excluded_dir_skipped")
            elif (base / name).is_symlink():
                notes.add("symlink_skipped")
            else:
                kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            path = base / name
            if path.is_symlink():
                notes.add("symlink_skipped")
                continue
            if not path.resolve().is_relative_to(real_root):
                notes.add("root_escape_skipped")
                continue
            if len(observed) >= max_files:
                coverage = "partial"
                notes.add("coverage_partial")
                continue
            relative = path.relative_to(real_root).as_posix()
            observed.append(Observed(relative, _hash_file(path)))
    return observed, coverage, notes


def scan_folder(
    root: Path,
    source_id: str,
    previous: FolderScan | None,
    parser: tuple[str, str],
    max_files: int = DEFAULT_MAX_FILES,
) -> FolderScan:
    observed, coverage, notes = _walk(root, max_files)
    spec = KeyedSpec(source_id, "folder", "folder.locator", 1, "relative_path")
    parser_changed = previous is not None and previous.parser != parser
    result = reconcile_keyed(spec, previous.snapshot if previous else None, observed, coverage, parser_changed)
    delta = CandidateDelta.build(
        source_id,
        previous.snapshot.snapshot_id if previous else None,
        result.snapshot.snapshot_id,
        parser,
        result.operations,
    )
    return FolderScan(result.snapshot, delta, parser, tuple(sorted(notes)))

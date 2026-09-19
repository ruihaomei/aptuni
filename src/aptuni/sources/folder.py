"""Folder SourceProvider scan: identity (S05A) plus the M1 admission filters.

Only regular files under the approved root are read. Symlinks, VCS/cache directories, hidden
paths, likely secrets, unsupported formats and oversized files are skipped by default (ADR-0006).
A file-count bound makes coverage ``partial``, which never proves disappearance.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aptuni.sources.reconcile import KeyedSpec, Observed, reconcile_keyed
from aptuni.sources.records import CandidateDelta, Snapshot

EXCLUDED_DIRS = frozenset({".git", ".hg", ".svn", "__pycache__", "node_modules"})
SECRET_PATTERNS = ("*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "credentials*.json",
                   "*secret*", "*token*", ".env*", "*.kdbx")
TEXT_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".csv"})
DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_BYTES = 5 * 1024 * 1024


class PriorScan(Protocol):
    """What a scan needs from the previous one (a live scan or persisted state)."""

    @property
    def snapshot(self) -> Snapshot: ...

    @property
    def parser(self) -> tuple[str, str]: ...

    @property
    def sequence(self) -> int: ...


@dataclass(frozen=True)
class FolderScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]
    notes: tuple[str, ...]

    @property
    def sequence(self) -> int:
        return self.delta.sequence


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def is_secret(name: str) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatch(lowered, pattern) for pattern in SECRET_PATTERNS)


def _admit_file(path: Path, real_root: Path, notes: set[str], max_bytes: int) -> bool:
    name = path.name
    admitted = True
    if path.is_symlink():
        notes.add("symlink_skipped")
        admitted = False
    elif name.startswith("."):
        if is_secret(name):
            notes.add("secret_skipped")
        admitted = False
    elif is_secret(name):
        notes.add("secret_skipped")
        admitted = False
    elif path.suffix.lower() not in TEXT_SUFFIXES:
        notes.add("unsupported_format_skipped")
        admitted = False
    elif not path.resolve().is_relative_to(real_root):
        notes.add("root_escape_skipped")
        admitted = False
    elif path.stat().st_size > max_bytes:
        notes.add("oversized_skipped")
        admitted = False
    return admitted


def _walk(root: Path, max_files: int, max_bytes: int) -> tuple[list[Observed], str, set[str]]:
    real_root = root.resolve()
    observed: list[Observed] = []
    notes: set[str] = set()
    coverage = "complete"
    for directory, dirnames, filenames in os.walk(real_root, followlinks=False):
        base = Path(directory)
        kept = []
        for name in sorted(dirnames):
            if name in EXCLUDED_DIRS or name.startswith("."):
                notes.add("excluded_dir_skipped")
            elif (base / name).is_symlink():
                notes.add("symlink_skipped")
            else:
                kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            path = base / name
            if not _admit_file(path, real_root, notes, max_bytes):
                continue
            if len(observed) >= max_files:
                coverage = "partial"
                notes.add("coverage_partial")
                continue
            observed.append(Observed(path.relative_to(real_root).as_posix(), _hash_file(path)))
    return observed, coverage, notes


def scan_folder(
    root: Path,
    source_id: str,
    previous: PriorScan | None,
    parser: tuple[str, str],
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> FolderScan:
    observed, coverage, notes = _walk(root, max_files, max_bytes)
    spec = KeyedSpec(source_id, "folder", "folder.locator", 1, "relative_path")
    parser_changed = previous is not None and previous.parser != parser
    result = reconcile_keyed(spec, previous.snapshot if previous else None, observed, coverage, parser_changed)
    delta = CandidateDelta.build(
        source_id,
        previous.snapshot.snapshot_id if previous else None,
        result.snapshot.snapshot_id,
        parser,
        result.operations,
        sequence=previous.sequence + 1 if previous else 1,
    )
    return FolderScan(result.snapshot, delta, parser, tuple(sorted(notes)))

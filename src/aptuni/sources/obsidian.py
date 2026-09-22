"""Obsidian vault SourceProvider scan: vault admission plus bounded note topology (ADR-0017).

Identity is the vault-relative POSIX path, exactly as the Folder source, so the existing
content-hash reconciliation keeps a rename a ``move``. What this provider adds over a plain
folder is vault awareness: only a directory holding ``.obsidian/`` is a vault, the vault's own
configuration and trash are excluded before any read, attachments are never opened, and each
admitted note carries bounded wikilink/tag/alias/property-key topology in
``obsidian.locator@1``.
"""

from __future__ import annotations

import errno
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aptuni.sources.folder import EXCLUDED_DIRS, PriorScan, is_secret
from aptuni.sources.obsidian_parse import decode_note, parse_note, sanitize_token
from aptuni.sources.reconcile import KeyedSpec, Observed, reconcile_keyed
from aptuni.sources.records import CandidateDelta, Snapshot

VAULT_MARKER = ".obsidian"
TRASH_DIR = ".trash"
NOTE_SUFFIXES = frozenset({".md"})
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_BYTES = 5 * 1024 * 1024


class VaultUnavailableError(RuntimeError):
    """The vault stopped being a vault during the scan; nothing is reconciled."""


@dataclass(frozen=True)
class ObsidianScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]
    notes: tuple[str, ...]

    @property
    def sequence(self) -> int:
        return self.delta.sequence


def is_vault(root: Path) -> bool:
    """An Obsidian vault is a directory holding a real (non-symlinked) `.obsidian/` directory."""
    marker = root / VAULT_MARKER
    return root.is_dir() and marker.is_dir() and not marker.is_symlink()


def _rejection(path: Path, real_root: Path, max_bytes: int) -> str | None:
    """Why this file is not an admissible note, or None. Order is cheapest and safest first."""
    name = path.name
    if path.is_symlink():
        return "symlink_skipped"
    if name.startswith("."):
        return "secret_skipped" if is_secret(name) else "hidden_skipped"
    if is_secret(name):
        return "secret_skipped"
    if path.suffix.lower() not in NOTE_SUFFIXES:
        return "attachment_skipped"
    if not path.resolve().is_relative_to(real_root):
        return "root_escape_skipped"
    return "oversized_skipped" if path.stat().st_size > max_bytes else None


def _admit(path: Path, real_root: Path, notes: set[str], max_bytes: int) -> bool:
    reason = _rejection(path, real_root, max_bytes)
    if reason is not None:
        notes.add(reason)
    return reason is None


def _keep_dirs(base: Path, dirnames: list[str], top: bool, notes: set[str]) -> list[str]:
    kept = []
    for name in sorted(dirnames):
        if top and name == VAULT_MARKER:
            notes.add("obsidian_config_skipped")
        elif top and name == TRASH_DIR:
            notes.add("trash_skipped")
        elif name in EXCLUDED_DIRS or name.startswith("."):
            notes.add("excluded_dir_skipped")
        elif (base / name).is_symlink():
            notes.add("symlink_skipped")
        else:
            kept.append(name)
    return kept


def _read_note(path: Path, max_bytes: int) -> bytes | None:
    """Read one note without following a symlink at the final component.

    ``_rejection`` already refused symlinks, but that check and this read are separate syscalls.
    ``O_NOFOLLOW`` closes the final-component swap, and the size is re-checked on the open
    descriptor so a note that grew after ``stat`` cannot exceed the bound. A swap of a *parent*
    directory remains possible, exactly as for the Folder source.
    """
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.EMLINK, errno.ENOENT, errno.EACCES):
            return None
        raise
    try:
        data = os.read(descriptor, max_bytes + 1)
        return None if len(data) > max_bytes else data
    finally:
        os.close(descriptor)


def _observe(path: Path, relative: str, notes: set[str], max_bytes: int) -> Observed | None:
    data = _read_note(path, max_bytes)
    if data is None:
        notes.add("unreadable_skipped")
        return None
    content_hash = "sha256:" + hashlib.sha256(data).hexdigest()
    structure = parse_note(decode_note(data))
    notes.update(structure.notes)
    if structure.truncated:
        notes.add("locator_truncated")
    name = relative.rsplit("/", 1)[-1]
    # The note name and folder come from an owner-controlled filename, so they are sanitized like
    # every other untrusted token (Review 55 B2). ``relative_path`` stays raw: it is the identity
    # key, and rewriting it would break reconciliation and the descriptor-relative read.
    fields: dict[str, Any] = {
        "note_name": sanitize_token(name[:-3] if name.lower().endswith(".md") else name),
        "folder_path": sanitize_token(relative.rsplit("/", 1)[0] if "/" in relative else ""),
        "tags": structure.tags,
        "aliases": structure.aliases,
        "outbound_links": structure.outbound_links,
        "property_keys": structure.property_keys,
        "heading_count": structure.heading_count,
        "truncated": structure.truncated,
    }
    return Observed(relative, content_hash, fields)


def _walk(root: Path, max_files: int, max_bytes: int) -> tuple[list[Observed], str, set[str]]:
    real_root = root.resolve()
    observed: list[Observed] = []
    notes: set[str] = set()
    coverage = "complete"
    for directory, dirnames, filenames in os.walk(real_root, followlinks=False):
        base = Path(directory)
        dirnames[:] = _keep_dirs(base, dirnames, base == real_root, notes)
        for name in sorted(filenames):
            path = base / name
            if not _admit(path, real_root, notes, max_bytes):
                continue
            if len(observed) >= max_files:
                coverage = "partial"
                notes.add("coverage_partial")
                continue
            item = _observe(path, path.relative_to(real_root).as_posix(), notes, max_bytes)
            if item is not None:
                observed.append(item)
    if not is_vault(real_root):
        # The vault went away mid-walk (an unmounted sync folder, an evicted iCloud directory).
        # An empty observation under "complete" coverage would retract every note, so fail closed.
        raise VaultUnavailableError("obsidian_vault_unavailable")
    return observed, coverage, notes


def scan_obsidian(
    root: Path,
    source_id: str,
    previous: PriorScan | None,
    parser: tuple[str, str],
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> ObsidianScan:
    observed, coverage, notes = _walk(root, max_files, max_bytes)
    spec = KeyedSpec(source_id, "obsidian", "obsidian.locator", 1, "relative_path")
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
    return ObsidianScan(result.snapshot, delta, parser, tuple(sorted(notes)))

"""Source ingestion: candidate delta -> canonical Evidence (ADR-0006 pipeline).

A sync scans the source against its persisted identity manifest, admits the delta through the
delivery guard, turns source changes into minimized Evidence records (``exposure`` only; a mention
never implies study or mastery), queues ambiguous identity for review, commits atomically, and
only then saves the manifest. Evidence ids are derived from the delta id, so a crash between the
commit and the manifest save replays idempotently.
"""

from __future__ import annotations

import json
import os
import stat
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aptuni.domain.ids import deterministic_id, sha256_bytes
from aptuni.domain.records import (
    Evidence,
    LocatorExtension,
    Provenance,
    RetentionLabel,
    SourceConfig,
)
from aptuni.domain.records import SourceLocator as CanonicalLocator
from aptuni.domain.temporal import utc_now
from aptuni.sources.codec import operation_from_dict, operation_to_dict, snapshot_from_dict, snapshot_to_dict
from aptuni.sources.delivery import DeliveryGuard
from aptuni.sources.folder import DEFAULT_MAX_BYTES, FolderScan, scan_folder
from aptuni.sources.records import Operation, Snapshot
from aptuni.sources.records import SourceLocator as SourceItemLocator

FOLDER_PARSER = ("folder.text", "1")
EXCERPT_CHARS = 280
STATE_VERSION = 1
SOURCE_RETENTION = RetentionLabel(retention_class="source_minimized", purpose="source_evidence",
                                  expires_at=None, full_content=False)


class SourceChangedDuringSync(RuntimeError):
    """A file changed between scan and read; the sync is aborted without writing."""


@dataclass
class SourceState:
    snapshot: Snapshot
    parser: tuple[str, str]
    sequence: int
    delivery: DeliveryGuard
    review: list[dict[str, Any]] = field(default_factory=list)
    notes: tuple[str, ...] = ()


class SourceStateStore:
    """Per-source identity manifest, kept in the Vault next to the canonical records."""

    def __init__(self, vault_root: Path, source_id: str) -> None:
        self.path = vault_root / "sources" / f"{source_id}.json"

    def load(self) -> SourceState | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return SourceState(
            snapshot=snapshot_from_dict(data["snapshot"]), parser=(data["parser"][0], data["parser"][1]),
            sequence=int(data["sequence"]), delivery=DeliveryGuard.from_json(data["delivery"]),
            review=list(data["review"]), notes=tuple(data["notes"]),
        )

    def save(self, state: SourceState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps({
            "version": STATE_VERSION, "snapshot": snapshot_to_dict(state.snapshot), "parser": list(state.parser),
            "sequence": state.sequence, "delivery": state.delivery.to_json(), "review": state.review,
            "notes": list(state.notes),
        }, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
        tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, body)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self.path)
        directory_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


@dataclass(frozen=True)
class SyncReport:
    source_id: str
    counts: dict[str, int]
    review_items: int
    notes: tuple[str, ...]
    evidence_written: int


def _read_approved_file(root: Path, relative: str, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    """Open each path component relative to the approved root without following symlinks."""
    parts = Path(relative).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise SourceChangedDuringSync("source_path_invalid")
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            descriptors.append(current)
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
        descriptors.append(file_fd)
        info = os.fstat(file_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise SourceChangedDuringSync("source_file_type_or_size_changed")
        chunks: list[bytes] = []
        total = 0
        while total <= max_bytes:
            chunk = os.read(file_fd, min(65_536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total > max_bytes:
            raise SourceChangedDuringSync("source_file_grew_during_sync")
        return b"".join(chunks)
    except OSError as error:
        raise SourceChangedDuringSync("source_path_changed_during_sync") from error
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _excerpt(root: Path, relative: str, expected_hash: str | None) -> str:
    data = _read_approved_file(root, relative)
    if expected_hash is not None and sha256_bytes(data) != expected_hash:
        raise SourceChangedDuringSync("source_changed_during_sync")
    text = " ".join(data.decode("utf-8", errors="replace").split())
    return text[:EXCERPT_CHARS]


def _canonical_locator(locator: SourceItemLocator) -> CanonicalLocator:
    extension = LocatorExtension.model_validate({"schema": locator.extension.schema,
                                                 "version": locator.extension.version,
                                                 "fields": dict(locator.extension.fields)})
    return CanonicalLocator(provider=locator.provider, subject_id=locator.subject_id, extension=extension)


class FolderIngest:
    """Turns one folder delta into Evidence records for one configured source."""

    def __init__(self, config: SourceConfig, module: str, policy_epoch: int,
                 current: dict[str, Evidence], existing_ids: set[str]) -> None:
        self.config = config
        self.existing_ids = existing_ids  # replay after a crash: already-committed ids are skipped
        self.root = Path(config.roots[0])
        self.module = module
        self.policy_epoch = policy_epoch
        self.current = current  # source subject id -> current Evidence

    def scan(self, state: SourceState | None) -> FolderScan:
        return scan_folder(self.root, self.config.id, state, FOLDER_PARSER)

    def evidence_for(self, op: Operation, delta_id: str, sequence: int) -> Evidence | None:
        subject = op.subject_id
        if subject is None or deterministic_id("evd", f"{delta_id}:{subject}") in self.existing_ids:
            return None
        previous = self.current.get(subject)
        if op.kind == "remove":
            if previous is None:
                return None
            return self._record(op, delta_id, sequence, previous, retraction=True)
        return self._record(op, delta_id, sequence, previous, retraction=False)

    def _record(self, op: Operation, delta_id: str, sequence: int, previous: Evidence | None,
                *, retraction: bool) -> Evidence:
        locator = op.before if retraction else op.after
        assert locator is not None  # guaranteed by the Operation shape invariants
        relative = str(locator.extension.fields["relative_path"])
        if retraction:
            assert previous is not None
            excerpt, content_hash, change_kind = previous.excerpt, previous.content_hash, "retraction"
        else:
            excerpt = _excerpt(self.root, relative, op.content_hash)
            content_hash = str(op.content_hash)
            change_kind = "assert" if previous is None else (
                "correction" if op.kind == "move" or "parser_upgrade" in op.reasons else "world_change")
        now = utc_now()
        return Evidence(
            record_type="evidence", id=deterministic_id("evd", f"{delta_id}:{locator.subject_id}"),
            schema_version=1, recorded_at=now, valid_from=None, valid_until=None,
            module=self.module,
            provenance=Provenance(source_id=self.config.id, episode=f"sync-{sequence}",
                                  locator=_canonical_locator(locator)),
            trust="untrusted_source", retention=SOURCE_RETENTION, policy_epoch=self.policy_epoch, confidence=None,
            review_status="auto_derived", supersedes=(previous.id,) if previous else (),
            change_kind=change_kind,
            subject=relative, signals=() if retraction else ("exposure",), excerpt=excerpt,
            content_hash=content_hash, observed_at=now,
        )


def summarize(ops: list[Operation]) -> dict[str, int]:
    return dict(Counter(op.kind for op in ops))


def review_entries(ops: list[Operation]) -> list[dict[str, Any]]:
    return [operation_to_dict(op) for op in ops if op.review_state == "needs_review"]


def review_operations(state: SourceState | None) -> list[Operation]:
    return [operation_from_dict(item) for item in (state.review if state else [])]

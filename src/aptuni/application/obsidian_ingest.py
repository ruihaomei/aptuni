"""Obsidian ingestion: vault deltas -> minimized topology Evidence (ADR-0017).

The Evidence excerpt is taken from the note body *after* the frontmatter block is removed, so a
private property value cannot reach the exposed excerpt or the retrieval projection. The bounded
wikilink/tag/alias/property-key topology already lives in ``obsidian.locator@1`` and is not
repeated in the excerpt.
"""

from __future__ import annotations

from pathlib import Path

from aptuni.application.ingest import (
    EXCERPT_CHARS,
    SOURCE_RETENTION,
    SourceChangedDuringSync,
    SourceState,
    _canonical_locator,
    _read_approved_file,
)
from aptuni.domain.ids import deterministic_id, sha256_bytes
from aptuni.domain.records import Evidence, Provenance, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.sources.obsidian import ObsidianScan, scan_obsidian
from aptuni.sources.obsidian_parse import body_without_frontmatter, decode_note
from aptuni.sources.records import Operation

OBSIDIAN_PARSER = ("obsidian.vault", "1")


def _body_excerpt(root: Path, relative: str, expected_hash: str | None) -> str:
    data = _read_approved_file(root, relative)
    if expected_hash is not None and sha256_bytes(data) != expected_hash:
        raise SourceChangedDuringSync("source_changed_during_sync")
    body = body_without_frontmatter(decode_note(data))
    return " ".join(body.split())[:EXCERPT_CHARS]


class ObsidianIngest:
    """Turns one Obsidian vault delta into Evidence records for one configured source."""

    def __init__(self, config: SourceConfig, module: str, policy_epoch: int,
                 current: dict[str, Evidence], existing_ids: set[str]) -> None:
        self.config = config
        self.existing_ids = existing_ids  # replay after a crash: already-committed ids are skipped
        self.root = Path(config.roots[0])
        self.module = module
        self.policy_epoch = policy_epoch
        self.current = current  # source subject id -> current Evidence

    def scan(self, state: SourceState | None) -> ObsidianScan:
        return scan_obsidian(self.root, self.config.id, state, OBSIDIAN_PARSER)

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
            excerpt = _body_excerpt(self.root, relative, op.content_hash)
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
            trust="untrusted_source", retention=SOURCE_RETENTION, policy_epoch=self.policy_epoch,
            confidence=None, review_status="auto_derived", supersedes=(previous.id,) if previous else (),
            change_kind=change_kind,
            subject=relative, signals=() if retraction else ("exposure",), excerpt=excerpt,
            content_hash=content_hash, observed_at=now,
        )

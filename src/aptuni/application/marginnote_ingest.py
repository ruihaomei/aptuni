"""MarginNote 4 ingestion: native-ID concept deltas -> minimized knowledge Evidence (ADR-0015).

Evidence carries a bounded label path (``subject``) and a structured ≤280-character summary of
coverage, depth, source and time (``excerpt``). No excerpt bodies or comments are stored. The
``studied`` signal is emitted only when the user's authority policy for this source lists
``knowledge.studied``; otherwise a card is ``exposure`` evidence like any other source.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aptuni.application.ingest import SOURCE_RETENTION, SourceState, _canonical_locator
from aptuni.domain.ids import deterministic_id
from aptuni.domain.records import Evidence, Provenance, Signal, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.sources.marginnote4 import MarginNoteScan, build_digest, read_snapshot, scan_marginnote
from aptuni.sources.records import CandidateDelta, Operation

STUDIED_DIMENSION = "knowledge.studied"
ALL_NOTEBOOKS = "*"


class MarginNoteSpecError(ValueError):
    """The stored MarginNote source configuration is malformed."""


@dataclass(frozen=True)
class MarginNoteSourceSpec:
    store: Path
    notebooks: frozenset[str] | None  # None = every notebook, including ones created later

    def roots(self) -> tuple[str, ...]:
        selected = (ALL_NOTEBOOKS,) if self.notebooks is None else tuple(sorted(self.notebooks))
        return (str(self.store), *(f"notebook:{n}" for n in selected))

    @classmethod
    def from_roots(cls, roots: tuple[str, ...]) -> MarginNoteSourceSpec:
        if len(roots) < 2 or not all(r.startswith("notebook:") and len(r) > 9 for r in roots[1:]):
            raise MarginNoteSpecError("marginnote_source_config_invalid")
        selected = frozenset(r[9:] for r in roots[1:])
        if ALL_NOTEBOOKS in selected and len(selected) > 1:
            raise MarginNoteSpecError("marginnote_source_config_invalid")
        return cls(Path(roots[0]), None if selected == {ALL_NOTEBOOKS} else selected)


class MarginNoteIngest:
    """Turns one MarginNote concept delta into Evidence records for one configured source."""

    def __init__(self, config: SourceConfig, module: str, policy_epoch: int,
                 current: dict[str, Evidence], existing_ids: set[str]) -> None:
        self.config = config
        self.spec = MarginNoteSourceSpec.from_roots(config.roots)
        self.module = module
        self.policy_epoch = policy_epoch
        self.current = current
        self.existing_ids = existing_ids
        studied = module == "knowledge" and STUDIED_DIMENSION in config.authority.primary_for
        self.signals: tuple[Signal, ...] = ("studied",) if studied else ("exposure",)
        self._scan: MarginNoteScan | None = None

    def scan(self, state: SourceState | None) -> MarginNoteScan:
        snapshot = read_snapshot(self.spec.store, self.spec.notebooks)
        missing = frozenset() if self.spec.notebooks is None else self.spec.notebooks - set(snapshot.notebooks)
        previous = None
        if state is not None:
            prior = CandidateDelta.build(self.config.id, state.snapshot.snapshot_id, state.snapshot.snapshot_id,
                                         state.parser, (), sequence=state.sequence)
            previous = MarginNoteScan(state.snapshot, prior, state.parser, {})
        self._scan = scan_marginnote(build_digest(snapshot), self.config.id, previous, frozenset(missing))
        return self._scan

    def evidence_for(self, op: Operation, delta_id: str, sequence: int) -> Evidence | None:
        subject = op.subject_id
        if subject is None or deterministic_id("evd", f"{delta_id}:{subject}") in self.existing_ids:
            return None
        previous = self.current.get(subject)
        if op.kind == "remove":
            return None if previous is None else self._record(op, delta_id, sequence, previous, retraction=True)
        return self._record(op, delta_id, sequence, previous, retraction=False)

    def _record(self, op: Operation, delta_id: str, sequence: int, previous: Evidence | None,
                *, retraction: bool) -> Evidence:
        locator = op.before if retraction else op.after
        assert locator is not None and self._scan is not None
        if retraction:
            assert previous is not None
            text, label, content_hash, kind = previous.excerpt, previous.subject, previous.content_hash, "retraction"
        else:
            rendered = self._scan.rendered[locator.subject_id]
            text, label, content_hash = rendered.summary, rendered.subject, str(op.content_hash)
            kind = "assert" if previous is None else ("correction" if op.kind == "move" else "world_change")
        now = utc_now()
        return Evidence(
            record_type="evidence", id=deterministic_id("evd", f"{delta_id}:{locator.subject_id}"),
            schema_version=1, recorded_at=now, valid_from=None, valid_until=None, module=self.module,
            provenance=Provenance(source_id=self.config.id, episode=f"sync-{sequence}",
                                  locator=_canonical_locator(locator)),
            trust="untrusted_source", retention=SOURCE_RETENTION, policy_epoch=self.policy_epoch, confidence=None,
            review_status="auto_derived", supersedes=(previous.id,) if previous else (), change_kind=kind,
            subject=label, signals=() if retraction else self.signals,
            excerpt=text, content_hash=content_hash, observed_at=now,
        )

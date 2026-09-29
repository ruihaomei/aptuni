"""ADR-0028 at User #1 scale (Review 82 B5): Evidence→Profile stays linear at ~25k Evidence.

Measured on an Apple-silicon laptop at 25k: initial promoting sync ~5 s, backfill derivation and
`profile refresh` ~2 s each, no-op sync and `doctor` ~2-3 s, traced derivation peak ~130 MB. The
bounds below are several times those costs, so a regression to O(N²) (~9 min extrapolated from the
review's 2k/4k probe) fails loudly while ordinary machine variance does not.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.policy.evidence_profile import derive_evidence_profile
from marginnote_fixture import Card, build_store

SCALE = 25_000
SYNC_SECONDS = 60.0
BACKFILL_SECONDS = 30.0
DERIVE_PEAK_BYTES = 256 * 1024 * 1024


def _cards(count: int) -> dict[int, Card]:
    cards = {1: Card(title="Study map", children=list(range(2, count + 1)))}
    cards.update({key: Card(title=f"Topic {key}") for key in range(2, count + 1)})
    return cards


def _timed(action):  # type: ignore[no-untyped-def]
    started = time.perf_counter()
    value = action()
    return value, time.perf_counter() - started


def test_25k_evidence_backfill_noop_sync_and_derivation_stay_within_the_envelope(tmp_path: Path) -> None:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", _cards(SCALE))
    source = service.add_marginnote_source(
        store, ("NB-A",), ("knowledge",), "study-notes", primary_for=("knowledge.studied",),
    )
    service.set_review_policy(auto_promotion_enabled=False)
    report, _ = _timed(lambda: service.sync(source.id))
    assert report.evidence_written == SCALE and report.profile_written == 0
    service.set_review_policy(auto_promotion_enabled=True)

    seq, records = service.snapshot()
    tracemalloc.start()
    try:
        derived, derive_seconds = _timed(
            lambda: derive_evidence_profile(records.current_evidence(), records, {source.id: source},
                                            purged=frozenset()))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert len(derived) == 2 * SCALE
    assert derive_seconds < BACKFILL_SECONDS and peak < DERIVE_PEAK_BYTES
    assert service.snapshot()[0] == seq, "derivation alone writes nothing"

    promoted, refresh_seconds = _timed(service.refresh_profile)
    assert len(promoted) == SCALE and refresh_seconds < BACKFILL_SECONDS

    noop, noop_seconds = _timed(lambda: service.sync(source.id))
    assert noop.evidence_written == 0 and noop.profile_written == 0
    assert noop_seconds < SYNC_SECONDS
    doctor, doctor_seconds = _timed(service.doctor)
    assert doctor.ok and doctor_seconds < SYNC_SECONDS


def test_25k_initial_sync_promotes_in_one_linear_commit(tmp_path: Path) -> None:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", _cards(SCALE))
    source = service.add_marginnote_source(
        store, ("NB-A",), ("knowledge",), "study-notes", primary_for=("knowledge.studied",),
    )

    report, seconds = _timed(lambda: service.sync(source.id))

    assert report.evidence_written == SCALE and report.profile_written == SCALE
    assert seconds < SYNC_SECONDS

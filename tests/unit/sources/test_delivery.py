"""Delivery ordering for candidate deltas (S05A review rounds 1-2, promoted to production)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aptuni.sources.contract import CandidateDelta, ContractError, Extension, Operation, SourceLocator
from aptuni.sources.delivery import DeliveryError, DeliveryGuard
from aptuni.sources.folder import FolderScan, scan_folder

PARSER = ("folder.text", "1")


class Folder:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, name: str, text: str) -> None:
        (self.root / name).write_text(text, encoding="utf-8")

    def scan(self, previous: FolderScan | None = None) -> FolderScan:
        return scan_folder(self.root, "src-folder", previous, PARSER)


@pytest.fixture()
def folder() -> Folder:
    temp = tempfile.TemporaryDirectory()
    yield Folder(Path(temp.name))  # type: ignore[misc]
    temp.cleanup()


def test_content_flip_flop_deliveries_are_distinct_and_applied(folder: Folder) -> None:
    folder.write("a.md", "A")
    s1 = folder.scan()
    folder.write("a.md", "B")
    s2 = folder.scan(s1)
    folder.write("a.md", "A")
    s3 = folder.scan(s2)
    folder.write("a.md", "B")
    s4 = folder.scan(s3)
    guard = DeliveryGuard()
    for scan in (s1, s2, s3, s4):
        assert guard.admit(scan.delta) == "apply"
        guard.record(scan.delta)
    assert s2.delta.delta_id != s4.delta.delta_id


def test_late_redelivery_is_a_duplicate(folder: Folder) -> None:
    folder.write("a.md", "A")
    s1 = folder.scan()
    folder.write("a.md", "B")
    s2 = folder.scan(s1)
    guard = DeliveryGuard()
    for scan in (s1, s2):
        guard.admit(scan.delta)
        guard.record(scan.delta)
    assert guard.admit(s1.delta) == "duplicate"


def test_gap_and_stale_base_are_rejected(folder: Folder) -> None:
    folder.write("a.md", "A")
    s1 = folder.scan()
    folder.write("a.md", "B")
    s2 = folder.scan(s1)
    guard = DeliveryGuard()
    with pytest.raises(DeliveryError):
        guard.admit(s2.delta)  # base is s1's snapshot, but nothing was applied yet
    forged = CandidateDelta.build("src-folder", None, s1.delta.new_snapshot, PARSER, s1.delta.operations, sequence=3)
    with pytest.raises(DeliveryError):
        guard.admit(forged)


def test_mutated_delta_fails_integrity(folder: Folder) -> None:
    folder.write("a.md", "A")
    delta = folder.scan().delta
    delta.operations[0].after.extension.fields["relative_path"] = "../../etc/passwd"  # type: ignore[index,union-attr]
    with pytest.raises(DeliveryError):
        DeliveryGuard().admit(delta)


def test_gate_routes_unknown_versions_to_review_and_rejects_invalid() -> None:
    future = SourceLocator("s", "folder", "d1", Extension("folder.locator", 9, {"relative_path": "a"}))
    delta = CandidateDelta.build("s", None, "n1", PARSER, (Operation.add(future, "h"),))
    gated = DeliveryGuard().gate(delta)
    assert gated[0].review_state == "needs_review"
    bad = SourceLocator("s", "folder", "d2", Extension("folder.locator", 1, {"relative_path": "a", "x": 1}))
    with pytest.raises(ContractError):
        DeliveryGuard().gate(CandidateDelta.build("s", None, "n1", PARSER, (Operation.add(bad, "h"),)))


def test_state_round_trips_through_json(folder: Folder) -> None:
    folder.write("a.md", "A")
    s1 = folder.scan()
    guard = DeliveryGuard()
    guard.admit(s1.delta)
    guard.record(s1.delta)
    again = DeliveryGuard.from_json(guard.to_json())
    assert again.admit(s1.delta) == "duplicate"

"""Common envelope invariants, extension versioning and canonical round-trip."""

from __future__ import annotations

import unittest

from s05a.contract import (
    CandidateDelta,
    ContractError,
    Extension,
    Operation,
    Snapshot,
    SnapshotItem,
    SourceLocator,
    delta_from_json,
    delta_to_json,
    default_registry,
)


def folder_locator(subject: str, path: str) -> SourceLocator:
    return SourceLocator(
        source_id="src-folder",
        provider="folder",
        subject_id=subject,
        extension=Extension("folder.locator", 1, {"relative_path": path}),
    )


def sample_delta() -> CandidateDelta:
    before = folder_locator("doc-1", "a.md")
    after = folder_locator("doc-1", "b.md")
    return CandidateDelta.build(
        source_id="src-folder",
        base_snapshot="snap-1",
        new_snapshot="snap-2",
        parser=("folder.markdown", "1"),
        operations=(
            Operation.move("doc-1", before, after, "sha256:aa", reasons=("exact_hash_unique",)),
        ),
    )


class OperationInvariantTests(unittest.TestCase):
    def test_move_requires_subject_before_and_after(self) -> None:
        with self.assertRaises(ContractError):
            Operation(kind="move", subject_id="doc-1", before=None, after=folder_locator("doc-1", "b"))

    def test_add_cannot_have_before(self) -> None:
        loc = folder_locator("doc-1", "a.md")
        with self.assertRaises(ContractError):
            Operation(kind="add", subject_id="doc-1", before=loc, after=loc)

    def test_remove_is_only_a_tombstone_proposal(self) -> None:
        op = Operation.remove("doc-1", folder_locator("doc-1", "a.md"), "sha256:aa")
        self.assertEqual("tombstone_proposal", op.effect)

    def test_ambiguous_has_no_subject_and_needs_review(self) -> None:
        op = Operation.ambiguous(
            folder_locator("new-1", "c.md"), candidates=("doc-1", "doc-2"), reasons=("duplicate_hash",)
        )
        self.assertIsNone(op.subject_id)
        self.assertEqual("needs_review", op.review_state)
        with self.assertRaises(ContractError):
            Operation.ambiguous(folder_locator("n", "c.md"), candidates=("doc-1",), reasons=("x",))

    def test_locator_subject_must_match_operation_subject(self) -> None:
        with self.assertRaises(ContractError):
            Operation.move("doc-1", folder_locator("doc-9", "a"), folder_locator("doc-1", "b"), "h")

    def test_confidence_is_bounded(self) -> None:
        with self.assertRaises(ContractError):
            Operation.add(folder_locator("doc-1", "a.md"), "sha256:aa", confidence=1.5)


class SnapshotTests(unittest.TestCase):
    def test_partial_snapshot_cannot_support_removal(self) -> None:
        loc = folder_locator("doc-1", "a.md")
        base = Snapshot("snap-1", "src-folder", "complete", (SnapshotItem(loc, "sha256:aa"),))
        partial = Snapshot("snap-2", "src-folder", "partial", ())
        self.assertFalse(partial.supports_removal())
        self.assertTrue(base.supports_removal())

    def test_duplicate_subject_in_snapshot_is_rejected(self) -> None:
        loc = folder_locator("doc-1", "a.md")
        with self.assertRaises(ContractError):
            Snapshot("s", "src-folder", "complete", (SnapshotItem(loc, "h1"), SnapshotItem(loc, "h2")))


class DeltaTests(unittest.TestCase):
    def test_delta_id_is_deterministic_for_identical_content(self) -> None:
        self.assertEqual(sample_delta().delta_id, sample_delta().delta_id)

    def test_delta_id_changes_when_parser_version_changes(self) -> None:
        other = CandidateDelta.build(
            source_id="src-folder",
            base_snapshot="snap-1",
            new_snapshot="snap-2",
            parser=("folder.markdown", "2"),
            operations=sample_delta().operations,
        )
        self.assertNotEqual(sample_delta().delta_id, other.delta_id)

    def test_json_round_trip_is_lossless(self) -> None:
        delta = sample_delta()
        text = delta_to_json(delta)
        self.assertEqual(delta, delta_from_json(text))
        self.assertEqual(text, delta_to_json(delta_from_json(text)))

    def test_tampered_delta_id_is_rejected(self) -> None:
        text = delta_to_json(sample_delta()).replace(sample_delta().delta_id, "0" * 64)
        with self.assertRaises(ContractError):
            delta_from_json(text)

    def test_operations_must_belong_to_delta_source(self) -> None:
        foreign = SourceLocator("src-other", "folder", "d", Extension("folder.locator", 1, {"relative_path": "x"}))
        with self.assertRaises(ContractError):
            CandidateDelta.build("src-folder", "a", "b", ("p", "1"), (Operation.add(foreign, "h"),))


class ExtensionRegistryTests(unittest.TestCase):
    def test_three_provider_families_validate_through_one_common_contract(self) -> None:
        registry = default_registry()
        registry.validate(Extension("folder.locator", 1, {"relative_path": "notes/a.md"}))
        registry.validate(
            Extension(
                "marginnote.locator",
                1,
                {"canonical_node_id": "n1", "ancestor_path": ["Root", "Stats"], "vendor_node_id": None},
            )
        )
        registry.validate(
            Extension(
                "github.locator",
                1,
                {"repository_id": 42, "commit": "c" * 40, "path": "src/a.py", "blob": "b" * 40},
            )
        )

    def test_missing_required_extension_field_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            default_registry().validate(Extension("github.locator", 1, {"repository_id": 42}))

    def test_unknown_version_round_trips_but_forces_review(self) -> None:
        future = Extension("folder.locator", 9, {"relative_path": "a.md", "inode_hint": 7})
        registry = default_registry()
        self.assertFalse(registry.understands(future))
        loc = SourceLocator("src-folder", "folder", "doc-1", future)
        op = registry.gate(Operation.add(loc, "h"))
        self.assertEqual("needs_review", op.review_state)
        self.assertIn("extension_version_unknown", op.reasons)
        delta = CandidateDelta.build("src-folder", "a", "b", ("p", "1"), (op,))
        self.assertEqual(delta, delta_from_json(delta_to_json(delta)))

    def test_extension_provider_must_match_locator_provider(self) -> None:
        with self.assertRaises(ContractError):
            SourceLocator("s", "github", "d", Extension("folder.locator", 1, {"relative_path": "a"}))


if __name__ == "__main__":
    unittest.main()

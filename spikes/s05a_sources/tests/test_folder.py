"""Folder identity: skip, edit, exact rename, rename+edit, duplicates, delete, parser upgrade."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from s05a.contract import default_registry, delta_to_json
from s05a.folder import FolderScan, scan_folder

PARSER = ("folder.text", "1")


class FolderFixture:
    def __init__(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def move(self, old: str, new: str) -> None:
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        os.replace(self.root / old, self.root / new)

    def remove(self, relative: str) -> None:
        (self.root / relative).unlink()

    def scan(self, previous: FolderScan | None = None, parser: tuple[str, str] = PARSER, **kw: object) -> FolderScan:
        return scan_folder(self.root, "src-folder", previous, parser, **kw)  # type: ignore[arg-type]

    def close(self) -> None:
        self._temp.cleanup()


def kinds(scan: FolderScan) -> list[str]:
    return sorted(op.kind for op in scan.delta.operations)


class FolderIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = FolderFixture()
        self.fx.write("notes/a.md", "alpha")
        self.fx.write("notes/b.md", "beta")
        self.first = self.fx.scan()

    def tearDown(self) -> None:
        self.fx.close()

    def subject(self, path: str, scan: FolderScan | None = None) -> str:
        scan = scan or self.first
        for item in scan.snapshot.items:
            if item.locator.extension.fields["relative_path"] == path:
                return item.locator.subject_id
        raise AssertionError(path)

    def test_first_import_adds_every_file(self) -> None:
        self.assertEqual(["add", "add"], kinds(self.first))
        self.assertIsNone(self.first.delta.base_snapshot)

    def test_unchanged_rescan_is_empty_and_stable(self) -> None:
        second = self.fx.scan(self.first)
        self.assertEqual([], kinds(second))
        self.assertEqual(self.first.snapshot, second.snapshot)

    def test_identical_replay_produces_identical_delta(self) -> None:
        self.fx.write("notes/a.md", "alpha v2")
        one, two = self.fx.scan(self.first), self.fx.scan(self.first)
        self.assertEqual(delta_to_json(one.delta), delta_to_json(two.delta))

    def test_edit_keeps_identity_as_modify(self) -> None:
        self.fx.write("notes/a.md", "alpha v2")
        second = self.fx.scan(self.first)
        [op] = second.delta.operations
        self.assertEqual(("modify", self.subject("notes/a.md")), (op.kind, op.subject_id))

    def test_exact_rename_keeps_identity_as_move(self) -> None:
        self.fx.move("notes/a.md", "archive/a-renamed.md")
        second = self.fx.scan(self.first)
        [op] = second.delta.operations
        self.assertEqual("move", op.kind)
        self.assertEqual(self.subject("notes/a.md"), op.subject_id)
        self.assertEqual("archive/a-renamed.md", op.after.extension.fields["relative_path"])  # type: ignore[union-attr]
        self.assertIn("exact_hash_unique", op.reasons)

    def test_rename_plus_edit_is_not_silently_linked(self) -> None:
        self.fx.move("notes/a.md", "notes/c.md")
        self.fx.write("notes/c.md", "alpha edited")
        second = self.fx.scan(self.first)
        self.assertEqual(["add", "remove"], kinds(second))
        added = next(op for op in second.delta.operations if op.kind == "add")
        self.assertNotEqual(self.subject("notes/a.md"), added.subject_id)

    def test_duplicate_hash_rename_is_ambiguous_and_reviewable(self) -> None:
        self.fx.write("notes/b.md", "alpha")  # b now duplicates a's bytes
        base = self.fx.scan(self.first)
        self.fx.move("notes/a.md", "x/a.md")
        self.fx.move("notes/b.md", "x/b.md")
        second = self.fx.scan(base)
        ambiguous = [op for op in second.delta.operations if op.kind == "ambiguous"]
        self.assertEqual(2, len(ambiguous))
        for op in ambiguous:
            self.assertEqual("needs_review", op.review_state)
            self.assertEqual({self.subject("notes/a.md"), self.subject("notes/b.md")}, set(op.candidates))
        # Unresolved old subjects are not tombstoned while their fate is under review.
        self.assertNotIn("remove", kinds(second))

    def test_delete_is_a_tombstone_proposal(self) -> None:
        self.fx.remove("notes/b.md")
        [op] = self.fx.scan(self.first).delta.operations
        self.assertEqual(("remove", "tombstone_proposal"), (op.kind, op.effect))

    def test_partial_scan_never_proposes_removal(self) -> None:
        self.fx.remove("notes/b.md")
        second = self.fx.scan(self.first, max_files=0)
        self.assertEqual("partial", second.snapshot.coverage)
        self.assertNotIn("remove", kinds(second))
        self.assertIn("coverage_partial", second.notes)

    def test_parser_upgrade_reparses_unchanged_bytes(self) -> None:
        second = self.fx.scan(self.first, parser=("folder.text", "2"))
        self.assertEqual(["modify", "modify"], kinds(second))
        self.assertTrue(all("parser_upgrade" in op.reasons for op in second.delta.operations))
        self.assertEqual(self.first.snapshot.items, second.snapshot.items)

    def test_symlinks_and_vcs_internals_are_not_read(self) -> None:
        self.fx.write(".git/config", "secret")
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "x.md").write_text("outside", encoding="utf-8")
        os.symlink(Path(outside.name) / "x.md", self.fx.root / "notes/link.md")
        second = self.fx.scan(self.first)
        self.assertEqual([], kinds(second))
        self.assertIn("symlink_skipped", second.notes)

    def test_every_locator_passes_the_registry(self) -> None:
        registry = default_registry()
        for op in self.first.delta.operations:
            self.assertIs(op, registry.gate(op))


if __name__ == "__main__":
    unittest.main()

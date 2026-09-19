"""Regressions for S05A review round 1 (F1-F8). Each test reproduces a reviewer finding."""

from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path
from typing import Any

from aptuni.sources.contract import CandidateDelta, ContractError, Extension, Operation, SourceLocator, canonical_json
from aptuni.sources.folder import FolderScan, scan_folder
from aptuni.sources.github import scan_github
from aptuni.sources.opml import scan_opml

FOLDER_PARSER = ("folder.text", "1")


def gh(files: dict[str, str], truncated: bool = False) -> dict[str, Any]:
    return {"repository_id": 7, "full_name": "o/r", "commit": "1" * 40, "truncated": truncated,
            "tree": [{"path": p, "type": "blob", "sha": s, "size": 1} for p, s in files.items()]}


def opml(body: str) -> str:
    return f'<?xml version="1.0"?><opml version="2.0"><head/><body>{body}</body></opml>'


class TempFolder:
    def __init__(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)

    def write(self, relative: str, text: str) -> None:
        (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
        (self.root / relative).write_text(text, encoding="utf-8")

    def scan(self, previous: FolderScan | None = None, **kw: Any) -> FolderScan:
        return scan_folder(self.root, "src-folder", previous, FOLDER_PARSER, **kw)

    def cleanup(self) -> None:
        self._temp.cleanup()


class RecordInvariantTests(unittest.TestCase):  # F7
    def loc(self, subject: str = "d") -> SourceLocator:
        return SourceLocator("s", "folder", subject, Extension("folder.locator", 1, {"relative_path": "a"}))

    def test_candidates_only_on_ambiguous(self) -> None:
        with self.assertRaises(ContractError):
            Operation.add(self.loc(), "h", candidates=("x", "y"))

    def test_bool_is_not_a_version(self) -> None:
        with self.assertRaises(ContractError):
            Extension("folder.locator", True, {"relative_path": "a"})

    def test_nan_is_not_canonical(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json({"x": float("nan")})

    def test_one_operation_per_subject_per_delta(self) -> None:
        ops = (Operation.remove("d", self.loc(), "h"), Operation.modify(self.loc(), self.loc(), "h2"))
        with self.assertRaises(ContractError):
            CandidateDelta.build("s", "a", "b", ("p", "1"), ops)


class PartialCoverageTests(unittest.TestCase):  # F2, F8
    def test_partial_folder_scan_never_moves_an_unobserved_identity(self) -> None:
        fx = TempFolder()
        self.addCleanup(fx.cleanup)
        fx.write("b/x.md", "unique")
        first = fx.scan()
        original = first.snapshot.items[0].locator.subject_id
        fx.write("a/copy.md", "unique")
        partial = fx.scan(first, max_files=1)
        self.assertEqual(["ambiguous"], [op.kind for op in partial.delta.operations])
        held = [i for i in partial.snapshot.items if i.locator.subject_id == original]
        self.assertEqual([True], [i.held for i in held])
        complete = fx.scan(partial)
        self.assertNotIn("remove", [op.kind for op in complete.delta.operations])
        restored = {i.locator.extension.fields["relative_path"]: (i.locator.subject_id, i.held)
                    for i in complete.snapshot.items}
        self.assertEqual((original, False), restored["b/x.md"])  # same key + bytes re-observed

    def test_truncated_github_tree_never_moves_an_unlisted_identity(self) -> None:
        first = scan_github(gh({"src/x.py": "c" * 40}), "g", None, ("github.standard", "1"))
        second = scan_github(gh({"docs/x_copy.py": "c" * 40}, truncated=True), "g", first, ("github.standard", "1"))
        self.assertEqual(["ambiguous"], [op.kind for op in second.delta.operations])

    def test_opml_branch_copy_is_not_a_silent_move(self) -> None:
        full = opml('<outline text="R"><outline text="A"><outline text="Unique fact"/></outline>'
                    '<outline text="B"/></outline>')
        first = scan_opml(full, "m", None, ("marginnote.opml", "1"))
        branch = opml('<outline text="B"><outline text="Unique fact"/></outline>')
        second = scan_opml(branch, "m", first, ("marginnote.opml", "1"), export_scope="branch")
        kinds = sorted(op.kind for op in second.delta.operations)
        self.assertNotIn("move", kinds)
        self.assertIn("ambiguous", kinds)

    def test_held_ambiguity_candidates_survive_complete_rescans(self) -> None:
        fx = TempFolder()
        self.addCleanup(fx.cleanup)
        fx.write("a.md", "same")
        fx.write("b.md", "same")
        first = fx.scan()
        (fx.root / "a.md").rename(fx.root / "c.md")
        (fx.root / "b.md").rename(fx.root / "d.md")
        second = fx.scan(first)
        third = fx.scan(second)
        self.assertEqual([], [op.kind for op in third.delta.operations])
        held = {i.locator.subject_id for i in third.snapshot.items if i.held}
        self.assertEqual({i.locator.subject_id for i in first.snapshot.items}, held)

    def test_opml_review_reserved_node_is_held_not_tombstoned(self) -> None:
        base = opml('<outline text="R"><outline text="Bayes"/><outline text="Cox"/></outline>')
        first = scan_opml(base, "m", None, ("marginnote.opml", "1"))
        bayes = next(i.locator.subject_id for i in first.snapshot.items
                     if i.locator.extension.fields["ancestor_path"][-1] == "Bayes")
        second = scan_opml(base.replace("Bayes", "Bayesian"), "m", first, ("marginnote.opml", "1"))
        third = scan_opml(base.replace("Bayes", "Bayesian"), "m", second, ("marginnote.opml", "1"))
        self.assertEqual([], [op.kind for op in third.delta.operations])
        self.assertIn(bayes, {i.locator.subject_id for i in third.snapshot.items if i.held})


class GitHubStickyRenameTests(unittest.TestCase):  # F3
    def test_sticky_item_renamed_outside_budget_is_a_move_not_a_tombstone(self) -> None:
        files = {f"src/mod_{i:04d}.py": f"{i:040d}" for i in range(10)}
        first = scan_github(gh(files), "g", None, ("github.standard", "1"), budget=3)
        renamed = dict(files)
        renamed["src/zzz_renamed.py"] = renamed.pop("src/mod_0000.py")
        second = scan_github(gh(renamed), "g", first, ("github.standard", "1"), budget=3)
        self.assertEqual(["move"], [op.kind for op in second.delta.operations])


class OpmlWeakSignatureTests(unittest.TestCase):  # F5
    def test_single_generic_child_does_not_link_unrelated_parents(self) -> None:
        first = scan_opml(opml('<outline text="R"><outline text="Paper A"><outline text="Summary"/></outline>'
                               "</outline>"), "m", None, ("marginnote.opml", "1"))
        second = scan_opml(opml('<outline text="R"><outline text="Paper B"><outline text="Summary"/></outline>'
                                "</outline>"), "m", first, ("marginnote.opml", "1"))
        self.assertNotIn("modify", [op.kind for op in second.delta.operations])


class ImmutabilityDocTests(unittest.TestCase):
    def test_records_are_frozen_dataclasses(self) -> None:
        loc = SourceLocator("s", "folder", "d", Extension("folder.locator", 1, {"relative_path": "a"}))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            loc.subject_id = "other"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()

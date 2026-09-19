"""Regressions for S05A review round 2 (F1, F2, F3, F7)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from s05a.contract import CandidateDelta, Extension, Operation, SourceLocator, default_registry
from s05a.folder import FolderScan, scan_folder
from s05a.github import scan_github
from s05a.ledger import Ledger, LedgerError

PARSER = ("folder.text", "1")


class Folder:
    def __init__(self, case: unittest.TestCase) -> None:
        temp = tempfile.TemporaryDirectory()
        case.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, relative: str, text: str) -> None:
        (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
        (self.root / relative).write_text(text, encoding="utf-8")

    def scan(self, previous: FolderScan | None = None, **kw: Any) -> FolderScan:
        return scan_folder(self.root, "src-folder", previous, PARSER, **kw)


class DeliveryIdentityTests(unittest.TestCase):  # F1
    def test_sequence_makes_repeated_content_transitions_distinct_deliveries(self) -> None:
        fx = Folder(self)
        fx.write("a.md", "A")
        s1 = fx.scan()
        fx.write("a.md", "B")
        s2 = fx.scan(s1)
        fx.write("a.md", "A")
        s3 = fx.scan(s2)
        fx.write("a.md", "B")
        s4 = fx.scan(s3)
        self.assertEqual((1, 2, 3, 4), tuple(s.delta.sequence for s in (s1, s2, s3, s4)))
        self.assertNotEqual(s2.delta.delta_id, s4.delta.delta_id)

    def test_late_redelivery_after_content_cycle_is_a_duplicate_not_reapplied(self) -> None:
        fx = Folder(self)
        fx.write("a.md", "A")
        s1 = fx.scan()
        fx.write("a.md", "B")
        s2 = fx.scan(s1)
        fx.write("a.md", "A")
        s3 = fx.scan(s2)
        ledger = Ledger()
        for delta in (s1.delta, s2.delta, s3.delta):
            ledger.apply(delta)
        head = ledger.heads["src-folder"]
        self.assertEqual("duplicate", ledger.apply(s2.delta))
        self.assertEqual(head, ledger.heads["src-folder"])
        fx.write("a.md", "C")
        self.assertEqual("applied", ledger.apply(fx.scan(s3).delta))

    def test_sequence_gap_is_rejected(self) -> None:
        fx = Folder(self)
        fx.write("a.md", "A")
        s1 = fx.scan()
        fx.write("a.md", "B")
        s2 = fx.scan(s1)
        ledger = Ledger()
        ledger.apply(s1.delta)
        forged = CandidateDelta.build("src-folder", s2.delta.base_snapshot, s2.delta.new_snapshot,
                                      s2.delta.parser, s2.delta.operations, sequence=5)
        with self.assertRaises(LedgerError):
            ledger.apply(forged)

    def test_identical_replay_still_yields_identical_delta(self) -> None:
        fx = Folder(self)
        fx.write("a.md", "A")
        s1 = fx.scan()
        fx.write("a.md", "B")
        self.assertEqual(fx.scan(s1).delta, fx.scan(s1).delta)


class HeldItemEditTests(unittest.TestCase):  # F2
    def test_held_item_edited_while_unobserved_is_a_reviewable_modify_of_its_identity(self) -> None:
        fx = Folder(self)
        fx.write("b/x.md", "unique")
        first = fx.scan()
        original = first.snapshot.items[0].locator.subject_id
        fx.write("a/copy.md", "unique")
        partial = fx.scan(first, max_files=1)
        fx.write("b/x.md", "unique, edited")
        complete = fx.scan(partial)
        ops = [op for op in complete.delta.operations
               if (op.after or op.before).extension.fields["relative_path"] == "b/x.md"]  # type: ignore[union-attr]
        self.assertEqual([("modify", original, "needs_review")],
                         [(op.kind, op.subject_id, op.review_state) for op in ops])
        self.assertIn("held_item_changed", ops[0].reasons)
        at_key = [i for i in complete.snapshot.items if i.locator.extension.fields["relative_path"] == "b/x.md"]
        self.assertEqual([(original, False)], [(i.locator.subject_id, i.held) for i in at_key])


class GitHubPriorityTests(unittest.TestCase):  # F3
    def test_common_vanished_blob_does_not_flood_the_budget(self) -> None:
        empty = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
        base = {"README.md": "a" * 40, "pkg/__init__.py": empty}
        tree = lambda files: {"repository_id": 7, "full_name": "o/r", "commit": "1" * 40, "truncated": False,  # noqa: E731
                              "tree": [{"path": p, "type": "blob", "sha": s, "size": 0} for p, s in files.items()]}
        first = scan_github(tree(base), "g", None, ("github.standard", "1"), budget=4)
        files = {"README.md": "a" * 40, "pyproject.toml": "b" * 40}
        files.update({f"m{i:02d}/__init__.py": empty for i in range(20)})
        second = scan_github(tree(files), "g", first, ("github.standard", "1"), budget=4)
        selected = {i.locator.extension.fields["path"] for i in second.snapshot.items if not i.held}
        self.assertIn("pyproject.toml", selected)


class EnvelopeVersionTests(unittest.TestCase):  # round 3 note 3
    def test_envelope_without_sequence_is_a_contract_error(self) -> None:
        import json

        from s05a.contract import ContractError, delta_from_json, delta_to_json

        delta = CandidateDelta.build("s", None, "a", ("p", "1"), ())
        data = json.loads(delta_to_json(delta))
        self.assertEqual(2, data["envelope_version"])
        del data["sequence"]
        with self.assertRaises(ContractError):
            delta_from_json(json.dumps(data))


class GateTests(unittest.TestCase):  # F7
    def test_understood_locator_is_validated_even_when_the_other_is_unknown(self) -> None:
        old = SourceLocator("s", "folder", "d", Extension("folder.locator", 9, {"relative_path": "a"}))
        bad = SourceLocator("s", "folder", "d", Extension("folder.locator", 1, {"relative_path": "a", "x": 1}))
        with self.assertRaises(ValueError):
            default_registry().gate(Operation.modify(old, bad, "h"))


if __name__ == "__main__":
    unittest.main()

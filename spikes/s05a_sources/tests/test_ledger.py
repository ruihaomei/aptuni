"""Delta application: idempotent replay, stale-base rejection, no fact deletion from source loss."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from s05a.folder import scan_folder
from s05a.github import scan_github
from s05a.ledger import Ledger, LedgerError
from s05a.opml import scan_opml

OPML = ('<?xml version="1.0"?><opml version="2.0"><head/><body>'
        '<outline text="Stats"><outline text="Cox model"/><outline text="Bayes"/></outline></body></opml>')


def github_tree(files: dict[str, str]) -> dict[str, object]:
    return {"repository_id": 7, "full_name": "o/r", "commit": "1" * 40, "truncated": False,
            "tree": [{"path": p, "type": "blob", "sha": s, "size": 1} for p, s in files.items()]}


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "cv.md").write_text("Analyst at ACME", encoding="utf-8")
        (self.root / "old.md").write_text("old note", encoding="utf-8")
        self.folder1 = scan_folder(self.root, "src-folder", None, ("folder.text", "1"))
        self.opml1 = scan_opml(OPML, "src-mn", None, ("marginnote.opml", "1"))
        self.gh1 = scan_github(github_tree({"README.md": "a" * 40}), "src-gh", None, ("github.standard", "1"))
        self.ledger = Ledger()
        for delta in (self.folder1.delta, self.opml1.delta, self.gh1.delta):
            self.ledger.apply(delta)
        cv = next(i.locator.subject_id for i in self.folder1.snapshot.items
                  if i.locator.extension.fields["relative_path"] == "cv.md")
        old = next(i.locator.subject_id for i in self.folder1.snapshot.items
                   if i.locator.extension.fields["relative_path"] == "old.md")
        self.cv_subject, self.old_subject = cv, old
        self.ledger.add_fact("fact-role", "experience.role = Analyst", evidence=(("src-folder", cv),))
        self.ledger.add_fact("fact-note", "interest = old topic", evidence=(("src-folder", old),))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_replaying_an_applied_delta_is_a_noop(self) -> None:
        before = self.ledger.state_digest()
        self.assertEqual("duplicate", self.ledger.apply(self.folder1.delta))
        self.assertEqual(before, self.ledger.state_digest())

    def test_full_sequence_replay_reproduces_the_same_state(self) -> None:
        (self.root / "old.md").unlink()
        folder2 = scan_folder(self.root, "src-folder", self.folder1, ("folder.text", "1"))
        self.ledger.apply(folder2.delta)
        other = Ledger()
        for delta in (self.folder1.delta, self.opml1.delta, self.gh1.delta):
            other.apply(delta)
        other.add_fact("fact-role", "experience.role = Analyst", evidence=(("src-folder", self.cv_subject),))
        other.add_fact("fact-note", "interest = old topic", evidence=(("src-folder", self.old_subject),))
        other.apply(folder2.delta)
        other.apply(folder2.delta)  # duplicate delivery
        self.assertEqual(self.ledger.state_digest(), other.state_digest())

    def test_source_loss_withdraws_evidence_but_never_deletes_facts(self) -> None:
        (self.root / "old.md").unlink()
        folder2 = scan_folder(self.root, "src-folder", self.folder1, ("folder.text", "1"))
        self.ledger.apply(folder2.delta)
        fact = self.ledger.facts["fact-note"]
        self.assertEqual("needs_reevaluation", fact.status)
        self.assertEqual({("src-folder", self.old_subject)}, set(fact.withdrawn_evidence))
        self.assertIn(("src-folder", self.old_subject), self.ledger.tombstones)
        self.assertEqual("active", self.ledger.facts["fact-role"].status)

    def test_stale_base_snapshot_is_rejected(self) -> None:
        (self.root / "cv.md").write_text("Senior Analyst", encoding="utf-8")
        folder2 = scan_folder(self.root, "src-folder", self.folder1, ("folder.text", "1"))
        self.ledger.apply(folder2.delta)
        (self.root / "cv.md").write_text("Lead Analyst", encoding="utf-8")
        stale = scan_folder(self.root, "src-folder", self.folder1, ("folder.text", "1"))
        with self.assertRaises(LedgerError):
            self.ledger.apply(stale.delta)

    def test_ambiguous_operations_enter_the_review_queue(self) -> None:
        opml2 = scan_opml(OPML.replace("Bayes", "Bayesian inference"), "src-mn", self.opml1,
                          ("marginnote.opml", "1"))
        self.ledger.apply(opml2.delta)
        self.assertEqual(1, len(self.ledger.review_queue))
        self.assertEqual("same_position_text_changed", self.ledger.review_queue[0].reasons[0])

    def test_modify_marks_dependent_facts_for_reevaluation_without_rewriting(self) -> None:
        (self.root / "cv.md").write_text("Senior Analyst at ACME", encoding="utf-8")
        folder2 = scan_folder(self.root, "src-folder", self.folder1, ("folder.text", "1"))
        self.ledger.apply(folder2.delta)
        fact = self.ledger.facts["fact-role"]
        self.assertEqual(("needs_reevaluation", "experience.role = Analyst"), (fact.status, fact.statement))


if __name__ == "__main__":
    unittest.main()

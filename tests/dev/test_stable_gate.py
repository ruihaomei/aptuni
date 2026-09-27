from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.stable_gate import (
    _worktree_clean,
    AUTOMATED_CHECKS,
    EXACT_UX_PASS,
    FAIL,
    INSUFFICIENT,
    OWNER_ACTION,
    PASS,
    evaluate,
    main,
)

COMMIT = "a" * 40


def green_evidence() -> dict[str, object]:
    automated = {
        category: {check: True for check in checks}
        for category, checks in AUTOMATED_CHECKS.items()
        if category not in {"G", "H"}
    }
    automated["G"] = {
        "scored_trials": 30,
        "returned_records": 100,
        "useful_records": 80,
        "noise_records": 20,
        "exposure_violations": 0,
    }
    automated["H"] = {
        "dogfood_days": 14,
        "final_7_day_p0_p1_blockers": 0,
        "privacy_data_integrity_blockers": 0,
    }
    return {
        "schema_version": 1,
        "candidate": {"commit": COMMIT, "version": "0.2.0b1"},
        "automated": automated,
        "ux_gate": {"statement": None, "commit": None},
        "clean_room_audit": {"passed": None, "commit": None},
        "stable_publication": {"authorized": False, "commit": None},
    }


class StableGateTests(unittest.TestCase):
    def test_empty_evidence_fails_automated_and_preserves_real_world_states(self) -> None:
        report = evaluate({"schema_version": 1}, current_commit=COMMIT)
        self.assertEqual(report["automated_stable_gate"]["status"], FAIL)
        self.assertEqual(report["gates"]["G"]["status"], INSUFFICIENT)
        self.assertEqual(report["gates"]["H"]["status"], INSUFFICIENT)
        self.assertEqual(set(report["gates"]) & set(AUTOMATED_CHECKS), set(AUTOMATED_CHECKS))

    def test_threshold_boundaries_pass_but_missing_sample_does_not(self) -> None:
        evidence = green_evidence()
        report = evaluate(evidence, current_commit=COMMIT)
        self.assertEqual(report["gates"]["G"]["status"], PASS)
        evidence["automated"]["G"]["scored_trials"] = 29  # type: ignore[index]
        report = evaluate(evidence, current_commit=COMMIT)
        self.assertEqual(report["gates"]["G"]["status"], INSUFFICIENT)

    def test_quality_failures_are_fail_not_insufficient(self) -> None:
        for field, value in (
            ("useful_records", 79),
            ("noise_records", 21),
            ("exposure_violations", 1),
        ):
            with self.subTest(field=field):
                evidence = green_evidence()
                evidence["automated"]["G"][field] = value  # type: ignore[index]
                self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["G"]["status"], FAIL)

        partial = green_evidence()
        partial["automated"]["G"] = {"exposure_violations": 1}  # type: ignore[index]
        self.assertEqual(evaluate(partial, current_commit=COMMIT)["gates"]["G"]["status"], FAIL)

        partial["automated"]["H"] = {"privacy_data_integrity_blockers": 1}  # type: ignore[index]
        self.assertEqual(evaluate(partial, current_commit=COMMIT)["gates"]["H"]["status"], FAIL)

    def test_ux_requires_exact_phrase_and_candidate_commit(self) -> None:
        evidence = green_evidence()
        evidence["ux_gate"] = {"statement": "looks fine", "commit": COMMIT}
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["UX"]["status"], OWNER_ACTION)
        evidence["ux_gate"] = {"statement": EXACT_UX_PASS, "commit": "b" * 40}
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["UX"]["status"], OWNER_ACTION)
        evidence["ux_gate"] = {"statement": EXACT_UX_PASS, "commit": COMMIT}
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["UX"]["status"], PASS)

    def test_missing_false_and_non_boolean_automated_checks_fail_closed(self) -> None:
        for value in (None, False, "true"):
            with self.subTest(value=value):
                evidence = green_evidence()
                if value is None:
                    del evidence["automated"]["A"]["fresh_environment_install"]  # type: ignore[index]
                else:
                    evidence["automated"]["A"]["fresh_environment_install"] = value  # type: ignore[index]
                self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["A"]["status"], FAIL)

    def test_green_automated_gate_still_requires_owner_and_audit_sequence(self) -> None:
        evidence = green_evidence()
        report = evaluate(evidence, current_commit=COMMIT)
        self.assertEqual(report["automated_stable_gate"]["status"], PASS)
        self.assertEqual(report["release_readiness"]["status"], OWNER_ACTION)

        evidence["ux_gate"] = {"statement": EXACT_UX_PASS, "commit": COMMIT}
        report = evaluate(evidence, current_commit=COMMIT)
        audit_request = report["clean_room_audit_request_digest"]
        self.assertTrue(audit_request)
        evidence["clean_room_audit"] = {
            "passed": True, "commit": COMMIT, "prerequisite_digest": audit_request,
        }
        report = evaluate(evidence, current_commit=COMMIT)
        self.assertEqual(report["gates"]["CLEAN_ROOM_AUDIT"]["status"], PASS)
        self.assertEqual(report["release_readiness"]["status"], OWNER_ACTION)

        evidence["stable_publication"] = {
            "authorized": True,
            "commit": COMMIT,
            "request_digest": report["stable_publication_request_digest"],
        }
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["release_readiness"]["status"], PASS)

    def test_audit_and_publication_cannot_be_pre_authorized_before_prerequisites(self) -> None:
        evidence = green_evidence()
        evidence["automated"]["A"]["fresh_environment_install"] = False  # type: ignore[index]
        evidence["ux_gate"] = {"statement": EXACT_UX_PASS, "commit": COMMIT}
        evidence["clean_room_audit"] = {
            "passed": True, "commit": COMMIT, "prerequisite_digest": "sha256:" + "0" * 64,
        }
        evidence["stable_publication"] = {
            "authorized": True, "commit": COMMIT, "request_digest": "sha256:" + "0" * 64,
        }
        report = evaluate(evidence, current_commit=COMMIT)
        self.assertEqual(report["gates"]["CLEAN_ROOM_AUDIT"]["status"], FAIL)
        self.assertNotEqual(report["gates"]["STABLE_PUBLICATION"]["status"], PASS)
        self.assertIsNone(report["clean_room_audit_request_digest"])
        self.assertIsNone(report["stable_publication_request_digest"])

    def test_stale_candidate_evidence_fails(self) -> None:
        evidence = green_evidence()
        report = evaluate(evidence, current_commit="b" * 40)
        self.assertEqual(report["automated_stable_gate"]["status"], FAIL)
        self.assertFalse(report["candidate"]["commit_matches"])

    def test_invalid_current_commit_never_matches_missing_evidence_commit(self) -> None:
        evidence = green_evidence()
        evidence["candidate"] = {"commit": None, "version": "0.2.0b1"}
        report = evaluate(evidence, current_commit="not-a-commit")
        self.assertFalse(report["candidate"]["commit_matches"])
        self.assertEqual(report["automated_stable_gate"]["status"], FAIL)

    def test_dirty_worktree_cannot_pass_automated_gate(self) -> None:
        report = evaluate(green_evidence(), current_commit=COMMIT, worktree_clean=False)
        self.assertEqual(report["automated_stable_gate"]["status"], FAIL)
        self.assertFalse(report["candidate"]["worktree_clean"])
        self.assertIn("uncommitted", " ".join(report["automated_stable_gate"]["reasons"]))

    def test_undersized_sample_is_insufficient_even_with_low_precision(self) -> None:
        evidence = green_evidence()
        evidence["automated"]["G"] = {  # type: ignore[index]
            "scored_trials": 0, "returned_records": 0, "useful_records": 0,
            "noise_records": 0, "exposure_violations": 0,
        }
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["G"]["status"], INSUFFICIENT)
        evidence["automated"]["G"].update(  # type: ignore[index]
            {"scored_trials": 5, "returned_records": 10, "useful_records": 1, "noise_records": 9},
        )
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["G"]["status"], INSUFFICIENT)
        evidence["automated"]["G"]["noise_records"] = 3  # type: ignore[index]
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["G"]["status"], FAIL)

    def test_missing_audit_after_ux_is_owner_action_but_failed_audit_is_fail(self) -> None:
        evidence = green_evidence()
        evidence["ux_gate"] = {"statement": EXACT_UX_PASS, "commit": COMMIT}
        report = evaluate(evidence, current_commit=COMMIT)
        self.assertEqual(report["gates"]["CLEAN_ROOM_AUDIT"]["status"], OWNER_ACTION)
        self.assertEqual(report["release_readiness"]["status"], OWNER_ACTION)
        evidence["clean_room_audit"] = {
            "passed": False, "commit": COMMIT, "prerequisite_digest": report["clean_room_audit_request_digest"],
        }
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["CLEAN_ROOM_AUDIT"]["status"], FAIL)
        evidence["clean_room_audit"] = {"passed": True, "commit": COMMIT, "prerequisite_digest": "sha256:0"}
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["CLEAN_ROOM_AUDIT"]["status"], FAIL)

    def test_ux_cannot_pass_against_an_invalid_current_commit(self) -> None:
        evidence = green_evidence()
        evidence["ux_gate"] = {"statement": EXACT_UX_PASS, "commit": "x"}
        self.assertEqual(evaluate(evidence, current_commit="x")["gates"]["UX"]["status"], OWNER_ACTION)

    def test_non_bool_worktree_flag_is_treated_as_dirty(self) -> None:
        report = evaluate(green_evidence(), current_commit=COMMIT, worktree_clean="no")  # type: ignore[arg-type]
        self.assertEqual(report["automated_stable_gate"]["status"], FAIL)

    def test_longitudinal_boundaries(self) -> None:
        evidence = green_evidence()
        evidence["automated"]["H"]["dogfood_days"] = 13  # type: ignore[index]
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["H"]["status"], INSUFFICIENT)
        evidence["automated"]["H"] = {"final_7_day_p0_p1_blockers": 1}  # type: ignore[index]
        self.assertEqual(evaluate(evidence, current_commit=COMMIT)["gates"]["H"]["status"], FAIL)

    def test_worktree_rules_tolerate_only_an_untracked_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "src.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "src.py"], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "c"],
                cwd=root, check=True,
            )
            self.assertTrue(_worktree_clean(root, root / "report.json"))
            (root / "report.json").write_text("{}", encoding="utf-8")
            self.assertTrue(_worktree_clean(root, root / "report.json"))
            (root / "report.json").unlink()
            (root / "src.py").write_text("x = 22\n", encoding="utf-8")
            self.assertFalse(_worktree_clean(root, root / "src.py"))
            self.assertFalse(_worktree_clean(root, Path(temporary).parent / "elsewhere.json"))

    def test_cli_rejects_non_integer_schema_and_deep_nesting_with_exit_two(self) -> None:
        root = Path(__file__).parents[2]
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "evidence.json"
            for text in ('{"schema_version": true}', '{"schema_version": 1.0}', "[" * 100000 + "]" * 100000):
                with self.subTest(text=text[:24]):
                    evidence_path.write_text(text, encoding="utf-8")
                    self.assertEqual(main(["--root", str(root), "--evidence", str(evidence_path)]), 2)

    def test_report_artifacts_are_git_ignored(self) -> None:
        root = Path(__file__).parents[2]
        ignored = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("artifacts/", ignored)

    def test_invalid_candidate_metadata_is_not_echoed(self) -> None:
        evidence = green_evidence()
        evidence["candidate"] = {
            "commit": "private owner query",
            "version": "private Profile text",
        }
        report = evaluate(evidence, current_commit=COMMIT)
        self.assertIsNone(report["candidate"]["commit"])
        self.assertIsNone(report["candidate"]["version"])
        self.assertNotIn("private", json.dumps(report))
        self.assertEqual(report["automated_stable_gate"]["status"], FAIL)

    def test_cli_output_is_deterministic_atomic_and_does_not_echo_unknown_evidence(self) -> None:
        root = Path(__file__).parents[2]
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "evidence.json"
            output_path = Path(temporary) / "report.json"
            evidence_path.write_text(json.dumps({
                "schema_version": 1,
                "private_query": "never copy this owner text",
            }), encoding="utf-8")
            self.assertEqual(main(["--root", str(root), "--evidence", str(evidence_path),
                                   "--output", str(output_path)]), 1)
            first = output_path.read_bytes()
            self.assertNotIn(b"never copy this owner text", first)
            self.assertEqual(main(["--root", str(root), "--evidence", str(evidence_path),
                                   "--output", str(output_path)]), 1)
            self.assertEqual(output_path.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()

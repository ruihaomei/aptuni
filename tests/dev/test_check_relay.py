from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[2] / "tools" / "check_relay.py"
SPEC = importlib.util.spec_from_file_location("check_relay", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
check_relay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_relay)


def _write_review_repo(
    root: Path,
    reports: dict[str, str],
    streams: dict[str, dict[str, object]],
    state_summary: str,
    handoff_summary: str | None = None,
) -> None:
    """Create a minimal repository with review reports, manifest, STATE and HANDOFF."""
    reviews = root / "docs" / "dev" / "reviews"
    reviews.mkdir(parents=True)
    for name, text in reports.items():
        (reviews / name).write_text(text, encoding="utf-8")
    (reviews / "STATUS.json").write_text(
        json.dumps({"version": 2, "streams": streams}), encoding="utf-8"
    )
    summary_line = f"Review status manifest: {state_summary}\n"
    handoff_line = f"Review status manifest: {handoff_summary or state_summary}\n"
    (root / "docs" / "dev" / "STATE.md").write_text(summary_line, encoding="utf-8")
    (root / "docs" / "dev" / "HANDOFF.md").write_text(handoff_line, encoding="utf-8")


def _review(current: str, verdict: str, supersedes: list[str] | None = None) -> dict[str, object]:
    return {"kind": "review", "current": current, "verdict": verdict, "supersedes": supersedes or []}


class ReviewLineageTests(unittest.TestCase):
    def test_latest_block_is_reported_as_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "**Verdict:** **APPROVE**\n", "02-r.md": "**Verdict:** **BLOCK**\n"},
                {"sec": _review("02-r.md", "BLOCK", ["01-r.md"])},
                "sec=BLOCK",
            )
            self.assertEqual([], check_relay.check_review_state(root))

    def test_manifest_verdict_must_match_parsed_report_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "**Verdict:** **BLOCK**\n"},
                {"exe": _review("01-r.md", "APPROVE")},
                "exe=APPROVE",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("does not match" in e for e in errors), errors)

    def test_report_without_anchored_verdict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "Prose says APPROVE and BLOCK but has no verdict line.\n"},
                {"exe": _review("01-r.md", "APPROVE")},
                "exe=APPROVE",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("no final verdict" in e for e in errors), errors)

    def test_conflicting_verdict_lines_fail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "**Verdict:** **APPROVE**\n\n**Verdict:** **BLOCK**\n"},
                {"exe": _review("01-r.md", "BLOCK")},
                "exe=BLOCK",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("conflicting verdicts" in e for e in errors), errors)

    def test_non_blocking_notes_is_not_parsed_as_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "- **Verdict:** **APPROVE WITH NON-BLOCKING NOTES**\n"},
                {"arch": _review("01-r.md", "APPROVE_WITH_NON_BLOCKING_NOTES")},
                "arch=APPROVE_WITH_NON_BLOCKING_NOTES",
            )
            self.assertEqual([], check_relay.check_review_state(root))

    def test_review_stream_rejects_drill_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "**Verdict:** **PASS**\n"},
                {"exe": _review("01-r.md", "PASS")},
                "exe=PASS",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("not allowed for kind review" in e for e in errors), errors)

    def test_required_drill_without_report_is_pending_and_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {},
                {"relay-claude-code": {"kind": "drill", "current": None, "verdict": "PENDING"}},
                "relay-claude-code=PENDING",
            )
            self.assertEqual([], check_relay.check_review_state(root))
            self.assertTrue(check_relay.review_gate_open(root))

    def test_drill_marked_pass_without_report_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {},
                {"relay-codex": {"kind": "drill", "current": "05-drill.md", "verdict": "PASS"}},
                "relay-codex=PASS",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("current report missing" in e for e in errors), errors)

    def test_current_must_be_newest_in_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "**Verdict:** **APPROVE**\n", "02-r.md": "**Verdict:** **BLOCK**\n"},
                {"sec": _review("01-r.md", "APPROVE", ["02-r.md"])},
                "sec=APPROVE",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("not the newest" in e for e in errors), errors)

    def test_remediation_must_respond_to_manifest_report_and_carry_no_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {
                    "01-r.md": "**Verdict:** **BLOCK**\n",
                    "01-x-remediation.md": "**Verdict:** **APPROVE**\n",
                },
                {"sec": _review("01-r.md", "BLOCK")},
                "sec=BLOCK",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("Responds to" in e for e in errors), errors)
            self.assertTrue(any("must not contain a verdict" in e for e in errors), errors)

    def test_remediation_prose_mentioning_responds_to_is_not_a_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {
                    "01-r.md": "**Verdict:** **BLOCK**\n",
                    "01-x-remediation.md": (
                        "- **Responds to:** `01-r.md`\n\n"
                        "Files must declare `Responds to:` a manifest report and `other`.\n"
                    ),
                },
                {"sec": _review("01-r.md", "BLOCK")},
                "sec=BLOCK",
            )
            self.assertEqual([], check_relay.check_review_state(root))

    def test_handoff_summary_must_match_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "**Verdict:** **APPROVE**\n"},
                {"sec": _review("01-r.md", "APPROVE")},
                "sec=APPROVE",
                handoff_summary="sec=BLOCK",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("HANDOFF.md" in e for e in errors), errors)

    def test_state_must_have_exactly_one_summary_line(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {"01-r.md": "**Verdict:** **APPROVE**\n"},
                {"sec": _review("01-r.md", "APPROVE")},
                "sec=APPROVE",
            )
            state = root / "docs" / "dev" / "STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8") + "Review status manifest: sec=BLOCK\n",
                encoding="utf-8",
            )
            errors = check_relay.check_review_state(root)
            self.assertTrue(any("exactly one" in e for e in errors), errors)


class RelayCheckTests(unittest.TestCase):
    def test_adr_index_rejects_missing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            decisions = root / "docs" / "dev" / "DECISIONS"
            decisions.mkdir(parents=True)
            (decisions / "README.md").write_text("# Index\n", encoding="utf-8")
            (decisions / "ADR-0001-example.md").write_text("# ADR\n", encoding="utf-8")

            errors = check_relay.check_adr_index(root)

            self.assertEqual(1, len(errors))
            self.assertIn("ADR-0001-example.md", errors[0])

    def test_markdown_links_rejects_missing_relative_target(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "docs").mkdir()
            (root / "docs" / "a.md").write_text("[missing](b.md)\n", encoding="utf-8")

            errors = check_relay.check_markdown_links(root)

            self.assertEqual(1, len(errors))
            self.assertIn("b.md", errors[0])

    def test_state_requires_validation_and_relay_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = root / "docs" / "dev" / "STATE.md"
            state.parent.mkdir(parents=True)
            state.write_text("# Project State\n", encoding="utf-8")

            errors = check_relay.check_state(root)

            self.assertGreaterEqual(len(errors), 4)

    def test_state_validation_does_not_require_git_diff_check(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = root / "docs" / "dev" / "STATE.md"
            state.parent.mkdir(parents=True)
            state.write_text(
                "**Updated:** x\n**Current gate:** x\n**Production code:** x\n"
                "## Next highest-priority task\n## Latest validation state\n"
                "- `tools/check_relay.py` workspace-text check\n- Markdown link\n- ADR-index\n",
                encoding="utf-8",
            )

            self.assertEqual([], check_relay.check_state(root))

    def test_review_lineage_uses_latest_verdict_not_historical_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_review_repo(
                root,
                {
                    "01-review.md": "**Verdict:** **BLOCK**\n",
                    "02-rereview.md": "**Verdict:** **APPROVE**\n",
                },
                {"example": _review("02-rereview.md", "APPROVE", ["01-review.md"])},
                "example=APPROVE",
            )

            errors = check_relay.check_review_state(root)

            self.assertEqual([], errors)
            self.assertFalse(check_relay.review_gate_open(root))

    def test_workspace_text_rejects_trailing_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "bad.md").write_text("bad  \n", encoding="utf-8")

            errors = check_relay.check_workspace_text(root)

            self.assertEqual(1, len(errors))
            self.assertIn("trailing whitespace", errors[0])

    def test_workspace_text_skips_host_local_agent_logs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            logs = root / "spikes" / "x" / ".claude" / "logs"
            logs.mkdir(parents=True)
            (logs / "session.md").write_text("host log\n\n", encoding="utf-8")
            (root / "spikes" / "x" / "logs.md").write_text("bad\n\n", encoding="utf-8")

            errors = check_relay.check_workspace_text(root)

            self.assertEqual(1, len(errors))
            self.assertIn("logs.md", errors[0])


if __name__ == "__main__":
    unittest.main()

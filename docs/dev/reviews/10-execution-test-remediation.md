# Third Execution and Test Remediation

- **Date:** 2026-09-18
- **Responds to:** `10-execution-test-third-rereview.md`
- **Status:** non-blocking notes addressed; checker changes covered by tests

| Finding | Remediation |
|---|---|
| NF1 substring verdicts | `tools/check_relay.py` parses anchored `**Verdict:**`/`**Cold-relay verdict:**` lines; a current report needs ≥1 and all must agree (report 11 legitimately repeats an identical verdict, so "exactly one" was relaxed to "one distinct value"; conflicts fail). Manifest verdict must equal the parsed verdict. Verdict sets are per kind: review = APPROVE / APPROVE_WITH_NON_BLOCKING_NOTES / BLOCK; drill = PASS / FAIL / PENDING. Tests: latest BLOCK, mismatch, missing, conflicting, NON-BLOCKING ≠ BLOCK, drill verdict on review stream. |
| NF2 drill evidence | Manifest v2 splits `relay-codex` and `relay-claude-code` drill streams; PENDING drills are allowed only without reports and keep `review_gate_open()` true; a PASS drill without its report fails. Tests added. |
| NF3 ordering / remediation / HANDOFF | `current` must have the highest numeric prefix in its lineage; remediation files must declare `Responds to:` a manifest report and contain no verdict line; STATE and HANDOFF must each contain exactly one `Review status manifest:` line equal to the resolved summary. Tests added. |
| NF4 stale validation | STATE no longer must cite `git diff --check`; the required marker is the checker's `workspace-text` check. STATE/HANDOFF counts refreshed from an actual run. |
| NF5 S01 baseline | Pinned interpreter `/opt/homebrew/bin/python3.13` (verified 3.13.3 / SQLite 3.53.2); APFS data volume `/System/Volumes/Data` named; `statfs` + local-flag + sync-root denylist detection with injected negative probes; Linux/ext4 admission owned by M1.1 Slice 3 in ROADMAP. |
| NF6 evaluation ambiguity | EVALUATION_PLAN defines judged unit, pinned 32-unit overhead, empty-output rule, two-judge + adjudication with ties = irrelevant, and a checksummed worked example due in the M1.3 plan. Onboarding rows are tagged success / refusal / cancellation / recovery (B = success + refusal). |
| NF7 prior host version | Single rule: S04 records current and preceding stable version per host before journeys; a missing preceding version is release-blocking unless waived in KNOWN_ISSUES with source/reason/reviewer. Codex CLI is not on PATH on the Gate 0 host; its version is recorded during S04. |
| NF8 registration | Reports 09/10/11 registered in STATUS.json v2; AGENTS.md documents the registration step. |

Test-first evidence: the 14 new/updated tests failed against the previous checker
(`FAILED (failures=14)`) before implementation, then passed (`Ran 18 tests … OK`).

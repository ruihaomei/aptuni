# Second Execution and Test Remediation

- **Date:** 2026-09-18
- **Responds to:** `08-execution-test-rereview.md`
- **Status:** planning/tooling changes complete; second focused re-review pending

| Finding | Remediation |
|---|---|
| B1/H5 historical BLOCK handling | Added `reviews/STATUS.json` with current report/verdict/supersedes per architecture, security, execution, and relay stream. Relay checker validates manifest/report parity, all reports assigned to lineage, and exact STATE summary. Unit test proves historical BLOCK superseded by current APPROVE does not block. |
| B2 S01 matrix loop | `COMPATIBILITY.md` fixes Gate 0 baseline to macOS 26.2/APFS; S01 proves only that baseline and fails closed on unknown/network/synced filesystems. M1.1 later admits exact Ubuntu LTS/ext4 before Linux support. |
| H7 untracked whitespace | Relay checker now scans all relevant workspace text for trailing whitespace, final newline, and extra EOF blank, independent of Git tracking. A failing unit test was added first; five relay tests pass. |
| H8 setup safe-refusal loophole | `EVALUATION_PLAN.md` separates eligible setup success from expected safe-refusal correctness; both must be 100%, and refusal cannot count as success. |
| H9 context-noise units | Evaluation defines numerator/denominator in ADR-0005 conservative response units: irrelevant UTF-8 payload bytes plus allocated overhead divided by total returned units. |
| M6 prior host skip | Compatibility requires current plus preceding supported stable host version; inability remains a release-blocking gap or explicitly unsupported, never a silent skip. |

Cold Codex relay is PASS. Cold Claude Code relay remains required evidence before ADR-0008 acceptance;
this remediation does not claim it has run.

# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Gate 0. The independent plan-review gate is cleared: architecture, execution and security are each
APPROVE WITH NON-BLOCKING NOTES (notes addressed), and both cold relay drills passed. No production
code exists. S01, S02, and S03 passed. S04 has a passing local layer but its required real-host
matrix is blocked/incomplete; S05A remains before production scaffolding.

## Read first

1. `STATE.md`, `reviews/STATUS.json`, `KNOWN_ISSUES.md`
2. `DECISIONS/ADR-0013-honest-host-trust-boundary.md`, `THREAT_MODEL.md`
3. `plans/00-phase-0-spikes.md`, `SPIKES.md`, `COMPATIBILITY.md`

## Next action

Continue `spikes/S04-mcp.md` remaining blockers. The disposable environment is
`/tmp/pcc-s04-20260919` with MCP SDK 2.2.0. Codex 0.155.0/0.154.0 read paths and protected-write
canaries pass. A Foundation probe found a viable APFS `fileContentIdentifier` clone-family signal.
Claude authentication passes, but the account limit blocks both required versions before
inference/MCP. Rerun 2.1.267/2.1.266 after reset; complete every ADR-0013 host confinement/status
probe, turn KI-019 into a pinned/adversarially tested bridge, and fill the `COMPATIBILITY.md` cells. Do
not move to S05A while S04 is blocking.

## This pass changed

- S01 PASS (46 tests); findings F1–F3 → KI-016. S02 PASS (12 tests, offline); bytecode gap → KI-017.
- S03 PASS (23 tests): frozen synthetic bilingual evidence selected deterministic 2–4-character CJK
  lexemes; holdout passed, while broad short-query noise and real-data generalization remain KI-018.
- S04 WIP: local STDIO/policy/status harness 31 tests PASS; Codex 0.155.0/0.154.0 read paths and
  protected-write canaries PASS (plus 0.153.4 annotation/candidate observations); Claude
  2.1.267/2.1.266 BLOCKED_USAGE_LIMIT before any MCP call.
- Security stream approved (report 14) after ADR-0013 simplification; its notes addressed in
  remediation 14 (approve service reachable only from the CLI; Codex escalation disclosed).
- Maintainer decision (2026-09-18): honest host trust boundary + host confinement → ADR-0013; broker
  claims replaced everywhere; ADR-0013 then amended for re-reviews 12/13: terminal-only approval, evidence-only status
  (`not_in_effect` / `unverified`), required-key table in COMPATIBILITY, detection before every
  policy decision.
- Relay checker: anchored verdict parsing, per-kind verdicts, pending drills, lineage ordering,
  remediation declarations, single STATE/HANDOFF summary line (19 tests).
- Execution notes NF1–NF8 and Claude drill defects D1–D9 addressed (remediations 10 and 11).

## Known constraints

- `Prompt_PRD.txt` and the raw design-history file are maintainer-private/duplicate inputs and are
  gitignored; `docs/product/PRD.md` is canonical.
- Research Memory must not be initialized without explicit maintainer confirmation.
- Bare `python3` on the Gate 0 host is Anaconda 3.12.4; use `python3.13`.
- Commits are local only (maintainer authorized the first checkpoint on 2026-09-18); never push.

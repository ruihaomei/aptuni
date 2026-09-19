# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Gate 0. The plan-review gate is cleared and no production code exists. S01, S02 and S03 passed.
S04 focused review round 2 blocked on canary attribution (`spikes/S04-host-canary-review.md`). All
findings are remediated, and both hosts are rerun with the isolated design. Round 3 is pending.
S05A stays blocked.

## Read first

1. `STATE.md`, `reviews/STATUS.json`, `KNOWN_ISSUES.md`
2. `DECISIONS/ADR-0013-honest-host-trust-boundary.md`, `THREAT_MODEL.md`
3. `plans/00-phase-0-spikes.md`, `SPIKES.md`, `COMPATIBILITY.md`

## Next action

Run focused review round 3 (independent agent) over `spikes/S04-host-canary-review.md`, the runner,
`results/host-canary-matrix.json` and `COMPATIBILITY.md`. If it accepts, mark S04 PASS and start S05A.
The Codex isolated rerun passed: its control blocked everything, and the project layer alone produced
all three escapes.

## This pass changed

- S01 PASS (46 tests); findings F1–F3 → KI-016. S02 PASS (12 tests, offline); bytecode gap → KI-017.
- S03 PASS (23 tests): frozen synthetic bilingual evidence selected deterministic 2–4-character CJK
  lexemes; holdout passed, while broad short-query noise and real-data generalization remain KI-018.
- S04 relay (Claude, 2026-09-19): recorded the round-2 BLOCK and rebuilt the runner (pure `assess`/
  `run_ok`, and timeout/malformed/quota classified as `host_blocked_external`). The Claude A/B rerun
  passed with outer project-hook proof. The relay checker now skips gitignored `.claude/logs` (20
  tests). Local harness: 54 tests PASS with 5 host-capability skips. Earlier notes: Codex
  0.155.0/0.154.0 and Claude 2.1.267/2.1.266 read paths return `HOST_OK 61`; all block baseline
  write/TCP/AF_UNIX. Project merge is proven in both hosts; trusted Codex project full access yields
  independently observed unsafe effects. Native clone mapping fails closed on the host capability.
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
- Commits before `890dbec` stored an interpreter path containing the local user name in
  `spikes/s01_vault/results/S01-result.json` (now sanitized at source). Rewrite or squash history
  before any first public push.
- Commits are local only (maintainer authorized the first checkpoint on 2026-09-18); never push.

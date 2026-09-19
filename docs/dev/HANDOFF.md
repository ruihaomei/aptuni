# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Gate 0. All decision-changing spikes have passed: S01, S02, S03, S04 (focused review round 3) and
**S05A** (focused review round 3; `spikes/S05A-sources.md`). No production code exists. Gate 0 still
needs its exit checklist.

## Read first

1. `STATE.md`, `reviews/STATUS.json`, `KNOWN_ISSUES.md`
2. `DECISIONS/ADR-0013-honest-host-trust-boundary.md`, `THREAT_MODEL.md`
3. `plans/00-phase-0-spikes.md`, `SPIKES.md`, `COMPATIBILITY.md`

## Next action

Run the plan 00 exit checklist:
1. A batched independent evidence review of S01–S03.
2. The fixture-safety and dependency-leak checks.
3. ADR `Proposed` → `Accepted` for spike-confirmed decisions, folding the S05A contract refinements
   into ADR-0006.

Then start Milestone 1.1 Slice 1. Before M1.4 ships an adapter, the deferred ADR-0013 real-host
probes in plan 00 §5 step 4 must pass for each host version.

## This pass changed

- S01 PASS (46 tests); findings F1–F3 → KI-016. S02 PASS (12 tests, offline); bytecode gap → KI-017.
- S03 PASS (23 tests): frozen synthetic bilingual evidence selected deterministic 2–4-character CJK
  lexemes; holdout passed, while broad short-query noise and real-data generalization remain KI-018.
- S05A (Claude, 2026-09-19): stdlib contract spike, 95 tests. Reviews rounds 1–2 BLOCK and were
  fixed test-first: ledger ordering and delivery `sequence`, partial-coverage moves, held items,
  GitHub sticky rename. Round 3 approved.
- S04 relay (Claude, 2026-09-19): recorded the round-2 BLOCK and rebuilt the runner (pure `assess`/
  `run_ok`, and timeout/malformed/quota classified as `host_blocked_external`). Claude and Codex
  isolated A/B reruns passed. Round 3 accepted S04; its notes are applied (58 tests, per-run
  evidence committed, plans/ADR/ROADMAP carry the deferrals). The relay checker now skips gitignored `.claude/logs` (20
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

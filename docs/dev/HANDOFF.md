# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Gate 0. The independent plan-review gate is cleared: architecture, execution and security are each
APPROVE WITH NON-BLOCKING NOTES (notes addressed), and both cold relay drills passed. No production
code exists. Spikes S01–S05A have not run.

## Read first

1. `STATE.md`, `reviews/STATUS.json`, `KNOWN_ISSUES.md`
2. `DECISIONS/ADR-0013-honest-host-trust-boundary.md`, `THREAT_MODEL.md`
3. `plans/00-phase-0-spikes.md`, `SPIKES.md`, `COMPATIBILITY.md`

## Next action

Run S01 with the pinned interpreter; record `docs/dev/spikes/S01-vault.md` (measured facts separate
from interpretation; non-zero exit on failed acceptance). Then S02–S04 and S05A. Spike results decide
ADR acceptance or revision.

## This pass changed

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
- No initial commit yet; checkpoint only when the maintainer authorizes it.

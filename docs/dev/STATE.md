# Project State

**Updated:** 2026-09-19
**Current gate:** Gate 0 — planning and proof
**Production code:** not started; the independent plan-review gate is cleared, but production code
stays blocked until the decision-changing spikes S01–S04/S05A have accepted results.

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Implemented durable artifacts

- Canonical PRD v2.1 and depersonalized design rationale.
- Eight upstream research notes, research synthesis, thirteen proposed ADRs (ADR-0013 records the
  maintainer-chosen honest host trust boundary), MVP dependency graph, threat model, roadmap, spike
  catalog, evaluation/compatibility plans, and three execution plans.
- Cross-host harness (AGENTS.md, CLAUDE.md, docs/dev) and a tested relay checker with review-lineage
  manifest v2 (`reviews/STATUS.json`).
- Cold relay drills: Codex PASS (report 05), Claude Code PASS (report 11).

## In progress

- All review streams are clear (architecture 07, execution 10, security 14 — each approved with
  non-blocking notes, all notes addressed in remediations 07/10/14; relay drills 05 and 11 PASS).
- Gate 0 spikes: **S01 PASS** (`spikes/S01-vault.md`; F1–F3 → KI-016), **S02 PASS**
  (`spikes/S02-plugins.md`; bytecode gap F1 → KI-017), and **S03 PASS**
  (`spikes/S03-fts.md`; `cjk_lexemes` selected; generalization/noise limit → KI-018). S04 and S05A
  pending. ADRs stay `Proposed` until spike results confirm or revise them; spike conclusions still
  need an independent evidence review (plan 00 exit checklist).
- S04 is **IN PROGRESS**: deterministic local layer 13/13 PASS; installed Codex 0.153.4 partial host
  PASS; Claude Code 2.1.87 BLOCKED_EXTERNAL before MCP invocation. Current/preceding stable host
  journeys and ADR-0013 confinement/status cases remain blocking (KI-005/KI-014).

## Awaiting maintainer decisions

- Research Memory (`PROJECT_KNOWLEDGE.md`) initialization — offered, unanswered.
- Apache-2.0 license (ADR-0009) — release gate, not a spike blocker.
- Public brand/package name — release gate; development uses `personal_context_core`.

## Next highest-priority task

Continue S04 from `spikes/S04-mcp.md`: obtain runnable current/preceding host binaries, resolve the
Claude HTTP 400 blocker, then finish ADR-0013 per-host confinement/status probes. Do not start S05A
or accept ADR-0005 until the S04 blocking matrix clears.

## Latest validation state

- `python3.13 -m unittest tests/dev/test_check_relay.py`: Ran 19 tests in 0.016s OK
- `python3.13 tools/check_relay.py`: relay check passed (includes the workspace-text check, which
  covers untracked files for trailing whitespace/final newline).
- `git diff --check`: exit 0 against S03 checkpoint `ba7f91c` (tracked files only).
- S01: `spikes/s01_vault/run_s01.py` in a pinned-3.13.3 venv → 46 tests OK, exit 0.
- S02: `spikes/s02_plugins/run_s02.py` (offline) → 12 tests OK, exit 0.
- S03: `spikes/s03_fts/run_s03.py verify` on Python 3.13.3 / SQLite 3.53.2 → 23 tests OK;
  frozen evidence verified; selected `cjk_lexemes` clears development, 25k-scale, and holdout gates.
- S04 local: `/tmp/pcc-s04-20260919/bin/python run_s04.py` → 13 tests OK on MCP SDK 2.2.0;
  real-host evidence remains incomplete and S04 is not PASS.
- Markdown link and ADR-index checks run inside `tools/check_relay.py`: 75 Markdown files,
  13 ADRs, all indexed; 8 research notes.
- No production tests exist because production scaffolding is intentionally gated.

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
  (`spikes/S03-fts.md`; `cjk_lexemes` selected; generalization/noise limit → KI-018). S05A
  pending. ADRs stay `Proposed` until spike results confirm or revise them; spike conclusions still
  need an independent evidence review (plan 00 exit checklist).
- **S04 PASS** (`spikes/S04-mcp.md`; focused review round 3 `spikes/S04-round3-review.md`
  approved with non-blocking notes, all dispositioned). All four required host versions return
  `HOST_OK 61`. Baseline write/TCP/AF_UNIX canaries are blocked (`unverified`, never `confined`).
  Claude project-layer merge is proven by an outer-observed hook; no escape was observed and the cause
  is not attributed. An isolated Codex A/B proves that a trusted project `.codex/config.toml` alone
  yields full access (`not_in_effect`). The remaining real-host ADR-0013 probes are release-blocking
  M1.4/S12 gates. The native clone bridge fails closed (KI-014/KI-019).

## Awaiting maintainer decisions

- Research Memory (`PROJECT_KNOWLEDGE.md`) initialization — offered, unanswered.
- Apache-2.0 license (ADR-0009) — release gate, not a spike blocker.
- Public brand/package name — release gate; development uses `personal_context_core`.

## Next highest-priority task

Run S05A (common source-identity contract) per `plans/00-phase-0-spikes.md` §6. Use sanitized
Folder/MarginNote/GitHub fixtures to prove the SourceLocator/Snapshot/CandidateDelta/SourceConfig
boundary, idempotency, ambiguity, authority conflicts, truncation and source disappearance. Record
the result in `spikes/S05A-sources.md`, then run the plan 00 exit checklist before Gate 0 closes.

## Latest validation state

- `python3.13 -m unittest tests/dev/test_check_relay.py`: Ran 20 tests OK
- `python3.13 tools/check_relay.py`: relay check passed (includes the workspace-text check, which
  covers untracked files for trailing whitespace/final newline).
- `git diff --check`: exit 0 (tracked files only).
- S01: `spikes/s01_vault/run_s01.py` in a pinned-3.13.3 venv → 46 tests OK, exit 0.
- S02: `spikes/s02_plugins/run_s02.py` (offline) → 12 tests OK, exit 0.
- S03: `spikes/s03_fts/run_s03.py verify` on Python 3.13.3 / SQLite 3.53.2 → 23 tests OK;
  frozen evidence verified; selected `cjk_lexemes` clears development, 25k-scale, and holdout gates.
- S04 local: `/tmp/pcc-s04-20260919/bin/python run_s04.py` → 58 tests OK, 5 skips because the host
  APFS volume does not advertise full-clone mapping, on MCP SDK 2.2.0. The Claude remediated A/B
  rerun on the final runner and the six-run isolated Codex A/B passed (exit 0, inner = outer);
  per-run evidence in `results/host-canary-runs/`.
- Markdown link and ADR-index checks run inside `tools/check_relay.py`: 75 Markdown files,
  13 ADRs, all indexed; 8 research notes.
- No production tests exist because production scaffolding is intentionally gated.

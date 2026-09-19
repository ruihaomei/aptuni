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
- S04 is **IN PROGRESS**: focused review round 2 (`spikes/S04-host-canary-review.md`) blocked on
  canary attribution. The Claude relay remediated the runner (fail on mismatch/timeout/quota, outer
  hook proof, isolated `CODEX_HOME`) and reran Claude. The deterministic layer passes 54 tests with
  5 capability skips. Required Claude Code 2.1.267/2.1.266 and Codex 0.155.0/0.154.0 read paths
  all return `HOST_OK 61`. Baseline protected write/TCP/AF_UNIX canaries are blocked in all four
  versions. Claude project settings merge (an outer-observed project SessionStart hook with a session
  id) but cannot override the higher-priority CLI profile. In the isolated Codex A/B, the trusted
  no-`.codex` control blocks everything, while the project `.codex/config.toml` alone produces
  write/TCP/AF_UNIX escapes (`not_in_effect`) in both versions. The native
  full-clone bridge fails closed as `unverified` on this APFS volume (KI-014/KI-019).

## Awaiting maintainer decisions

- Research Memory (`PROJECT_KNOWLEDGE.md`) initialization — offered, unanswered.
- Apache-2.0 license (ADR-0009) — release gate, not a spike blocker.
- Public brand/package name — release gate; development uses `personal_context_core`.

## Next highest-priority task

Run focused
review round 3 over `spikes/S04-host-canary-review.md`, the runner, the matrix and `COMPATIBILITY.md`,
including the proposed Slice 1/7 assignment of the remaining file-tool/Apple Event/package cases.
Do not start S05A or accept ADR-0005 until S04 is independently accepted.

## Latest validation state

- `python3.13 -m unittest tests/dev/test_check_relay.py`: Ran 20 tests OK
- `python3.13 tools/check_relay.py`: relay check passed (includes the workspace-text check, which
  covers untracked files for trailing whitespace/final newline).
- `git diff --check`: exit 0 against S04 WIP checkpoint `0a33958` (tracked files only).
- S01: `spikes/s01_vault/run_s01.py` in a pinned-3.13.3 venv → 46 tests OK, exit 0.
- S02: `spikes/s02_plugins/run_s02.py` (offline) → 12 tests OK, exit 0.
- S03: `spikes/s03_fts/run_s03.py verify` on Python 3.13.3 / SQLite 3.53.2 → 23 tests OK;
  frozen evidence verified; selected `cjk_lexemes` clears development, 25k-scale, and holdout gates.
- S04 local: `/tmp/pcc-s04-20260919/bin/python run_s04.py` → 54 tests OK, 5 skips because the host
  APFS volume does not advertise full-clone mapping, on MCP SDK 2.2.0. The Claude remediated A/B
  rerun and the six-run isolated Codex A/B passed (exit 0, inner = outer).
- Markdown link and ADR-index checks run inside `tools/check_relay.py`: 75 Markdown files,
  13 ADRs, all indexed; 8 research notes.
- No production tests exist because production scaffolding is intentionally gated.

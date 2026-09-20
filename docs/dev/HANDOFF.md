# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-github-source=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Milestone 1. Runnable: Vault/CLI core; Folder, GitHub and direct local MarginNote 4 sources; builtin
interaction memory with quarantined MCP proposals; bilingual SQLite/FTS; bounded Context API; MCP
STDIO; Claude/Codex adapters; owner-readable Profile export; the Plugin Advisor; and the privacy
inventory/purge slice with atomic chain-preserving restore. Re-review 32 closed the privacy stream
**APPROVE WITH NON-BLOCKING NOTES** after three BLOCK rounds. Nothing is pushed.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Implement the guided-setup apply step (plan 02 steps 1, 4, 5): freeze `SetupPlan`, bind one terminal
confirmation to the advisor answers and catalog version, apply only shipped components, then run
doctor and a smoke task; cancellation must leave no Vault, grant or bundle. Four `BACKLOG.md` items
are already owned by that slice (Review 20 N8–N11). Details and the remaining M1 exit gates are in
STATE "Next highest-priority task". Keep all MarginNote access read-only; never commit note text.

### What just landed

The privacy inventory/purge slice at `2440e6e` (`aptuni privacy status | purge preview |
confirm | cancel`) plus
atomic journaled `Vault.restore_from` and HEAD format 2 (`chain_base`, ADR-0001 amendment; format 1
migrates on open). Reviews 29–31 all returned BLOCK; every finding was remediated test-first and 32
approved it. Non-blocking notes from 31 and 32 are in `BACKLOG.md` — the two worth doing early are
Review 32 N3 (an unreadable intent still wedges writes with no in-product remedy) and N6 (a wedged
action id is not discoverable from any surface).

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.

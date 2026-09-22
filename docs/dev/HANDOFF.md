# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-ci-supply-chain=APPROVE_WITH_NON_BLOCKING_NOTES; m1-evaluation-harness=APPROVE; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-owner-backup-restore=APPROVE; m1-post-contract-skills=APPROVE; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-real-host-s12=APPROVE; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; m2-mem0-admission=APPROVE_WITH_NON_BLOCKING_NOTES; m2-mem0-projection-adapter=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; release=APPROVE; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Milestone 2. Runnable: Vault/CLI core; Folder, GitHub and direct local MarginNote 4 sources; builtin
interaction memory with quarantined MCP proposals; bilingual SQLite/FTS; bounded Context API; MCP
STDIO; Claude/Codex adapters; owner-readable Profile export; the Plugin Advisor; privacy
inventory/purge with atomic chain-preserving restore; digest-bound guided setup through doctor and
smoke; verified owner backup/restore; hosted CI/supply-chain gates; the accepted versioned
production evaluation harness; four executable post-contract agent skills; and the exact frozen
Claude/Codex real-host S12 journeys. Milestone 1 is complete. Aptuni 0.1.0 is public on PyPI and as a
GitHub Release from exact commit `33ea08a`; tag workflow 35619712980 and release-commit CI
35572245440 are green. Review 50 independently approved the final public result. S10 has now
conditionally admitted Mem0 2.0.20 only as a disposable `infer=False` projection; Review 52
approved the boundary with non-blocking notes. The rebuild-only production preview is now runnable
and Review 53 approved it with non-blocking notes.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Open the hybrid-retrieval slice from the M2 roadmap. Start with an accepted bounded TDD plan and
frozen evaluation additions; keep SQLite/FTS as the deterministic fallback and canonical hydrator,
keep all scores derived, and preserve policy rechecks before exposure. Do not mutate the 0.1.0 tag
or artifacts; a concrete public defect requires a patch release.

`docs/dev/plans/07-m1-exit-matrix.md` audits every remaining M1 exit clause and orders Slices 14–18.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

The Mem0 projection preview adds `aptuni memory provider status|rebuild|delete`. It projects only
current accepted canonical memories, always uses `infer=False`, validates exact public enumeration,
and publishes fresh generations atomically. The optional runtime is exactly Mem0 2.0.20 plus Ollama
0.6.2; only numeric loopback is accepted, redirects/proxies are disabled, and models are never
pulled. Privacy purge removes the whole root and shares a lock with rebuild. Full gate: 479 passed,
3 optional skips and 47 subtests; the isolated runtime passes all 23 focused tests. Review 53 is
**APPROVE WITH NON-BLOCKING NOTES**.

S10 (`84a3a8e`) isolated Mem0 2.0.20 with a hash-locked runtime and a bounded synthetic fixture. Exact restart
and fresh-root rebuild passed with `infer=False`, guarded execution observed no non-loopback network
attempts, and canonical fixture bytes stayed unchanged. The adverse paths are now binding product
constraints: inference retained raw messages, and record deletion retained marker bytes in
Qdrant/history, so the adapter must reject inference and use whole-store rebuild deletion. The
focused suite passes 15/15; full repository pytest (459 tests plus 47 subtests), Ruff and strict
mypy are clean. Review 52 is **APPROVE WITH NON-BLOCKING NOTES**.

Slice 17's daily-task and focused matrices pass on Claude Code 2.1.267/2.1.266 and Codex
0.155.0/0.154.0. Exact resolved versions and the external built-wheel runtime are enforced. Claude
did not emit focused file-tool calls, so no denial is claimed; both Apple Event attempts produced no
outer effect and status remains `unverified`. Full local gate: 459 tests plus 47 subtests, ruff,
strict mypy, relay and 34 developer checks clean. Review 48 is **APPROVE**.

The pushed checkpoint passed hosted macOS, Ubuntu (including ext4 durability) and build/supply-chain
jobs. A 2026-09-21 read-only audit found no `aptuni` package on PyPI or npm, found only
`ruihaomei/aptuni` as an exact-name GitHub repository, and confirmed private vulnerability reporting
is enabled. No registry or repository setting was changed.

The exact 0.1.0 release commit is `33ea08a54a0a26a1dcfa74c419121afebe31f4c0`, tagged `v0.1.0`.
The OIDC release workflow passed and published byte-identical artifacts to PyPI; the GitHub Release
adds the same wheel/sdist and `SHA256SUMS`. A fresh PyPI-only Python 3.13 install passed CLI,
synthetic Vault/context/setup and MCP safety smokes. Legal files, public links, package metadata,
secret/private-data scans and the zero-finding hosted vulnerability audit passed. Review 50 is
**APPROVE**. See `docs/dev/releases/0.1.0.md` for exact URLs, run IDs and hashes.

## Known constraints

- The maintainer authorized the final 0.1.0 release-record checkpoint and push. Future publication
  or tag changes require fresh authorization. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.

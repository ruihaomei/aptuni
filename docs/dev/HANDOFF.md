# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-ci-supply-chain=APPROVE_WITH_NON_BLOCKING_NOTES; m1-evaluation-harness=APPROVE; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-owner-backup-restore=APPROVE; m1-post-contract-skills=APPROVE; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-real-host-s12=APPROVE; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; m2-automatic-promotion=APPROVE_WITH_NON_BLOCKING_NOTES; m2-github-deep=APPROVE_WITH_NON_BLOCKING_NOTES; m2-hybrid-retrieval=APPROVE_WITH_NON_BLOCKING_NOTES; m2-mem0-admission=APPROVE_WITH_NON_BLOCKING_NOTES; m2-mem0-projection-adapter=APPROVE_WITH_NON_BLOCKING_NOTES; m2-obsidian-source=APPROVE_WITH_NON_BLOCKING_NOTES; m2-profile-promotion=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; release=APPROVE; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

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
approved the boundary with non-blocking notes. The rebuild-only production preview is runnable and
Review 53 approved it with non-blocking notes. The opt-in hybrid retrieval preview is now runnable
and Review 54 approved it with non-blocking notes and no blocking findings. The Obsidian vault
source is runnable; Review 55 blocked on three findings, all remediated test-first, and then
approved with non-blocking notes. Automatic promotion slices A–D are runnable. Slice D is
checkpointed at `6d936f3`; Review 57 initially blocked its direct-only structural proof, then
approved the transitive remediation with non-blocking notes. GitHub Deep is runnable at `f994446`;
Review 58 approved the final exact-actor, bounded authored-activity source with non-blocking notes.
Automatic Profile promotion is runnable under accepted ADR-0020; Review 59 approved its exact,
owner-pinned Memory→Fact lifecycle after all incremental/full-validation blockers were remediated.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Continue the maintainer-prioritized run with the smallest durable longitudinal setup/evaluation for
promotion, retrieval, correction, review, noise, provenance and personalization. After that local
checkpoint, continue directly to the separate `interface.obsidian` plugin/UI MVP. Private real-data
steps may require maintainer participation; never persist that content in repository artifacts. Do
not reopen ADR-0019 or expand Deep without a new decision.

Two Review 55 lessons carry forward to any provider work: write injection tests with **real**
control bytes — the literal text of an escape sequence asserts nothing and left a whole mutation
class undetected — and route every outside-controlled token through `sanitize_token` where it is
stored or `delimited_untrusted` where it is rendered. Do not mutate the 0.1.0 tag or artifacts; a
concrete public defect requires a patch release.

`docs/dev/plans/07-m1-exit-matrix.md` audits every remaining M1 exit clause and orders Slices 14–18.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

Automatic Profile promotion (ADR-0020, Review 59) closes the canonical `Memory → stable Fact`
lifecycle without semantic guessing. Only a current owner-pinned Memory with exact owner-declared
CLI support, both module permissions, no unresolved contradiction and no historical promoted Fact
qualifies. Pinning writes one policy event and one exact lineage-linked Fact atomically;
`aptuni profile refresh` handles older pins, and `aptuni profile review list|accept|reject` provides
retrospective review. Rejection preserves history and can never silently recreate the claim.
Context marks pending promoted Facts. Incremental canonical validation binds the copied claim and
one transition event, including correction and duplicate-event cases. Full gate: 642 passed, 3
optional skips, 47 subtests; Ruff, strict mypy, relay, supply-chain and frozen evaluation green.
Review 59 final verdict: **APPROVE WITH NON-BLOCKING NOTES**.

GitHub Deep (`f994446`) is an additive `github_deep` source created with `aptuni source add-github
... --deep-actor LOGIN`. It keeps GitHub Standard unchanged and records minimized Evidence only for
exact linked-login authored commits, opened pull requests and submitted reviews inside the approved
repository. ADR-0019 and `github.activity@1` bind the public contract. Deep never reads or retains
blobs, diffs, bodies, comments, emails, issue/discussion threads, file lifecycle or cross-repository
activity. Commits/PR search stop at five 100-item pages; reviews stop at 100 candidate PRs, two pages
per PR, 100 requests and 500 admitted items; every response is capped at 2,000,000 bytes. Exhausted
or changing search bounds make the whole snapshot partial, while malformed identity, rate limits
and overruns fail without durable change. Review 58 first blocked three contract/test gaps; exact
positive repository IDs are now enforced at API, scan and locator intake, the undeclared field was
removed, and below/at-cap regressions prove prior Evidence cannot be withdrawn. Full gate: 627
passed, 3 optional skips, 47 subtests; Ruff, strict mypy, relay, supply-chain and frozen evaluation
green. Final verdict: **APPROVE WITH NON-BLOCKING NOTES**.

Automatic promotion Slice D (`6d936f3`) adds the read-only `aptuni_get_memory_review` MCP tool.
The exact `memory.review.read` scope is disclosed in new adapter plans; old grants fail closed.
The bounded feed filters pending memories through current exposure and granted modules, derives the
reminder over that filtered set, enforces host/model egress, and discards a response after a
concurrent canonical change. The ADR-0013 item 1 regression keeps a direct MCP handler allowlist
and traverses the read-service call graph across all application mixins, rejecting promotion,
owner-decision and commit sinks. Review 57's initial BLOCK found the first direct-only proof was not
transitive; the remediation passed 61 focused tests and the final review is **APPROVE WITH
NON-BLOCKING NOTES**. Full gate: 600 passed, 3 optional skips, 47 subtests; Ruff, strict mypy,
relay, supply-chain checks and frozen evaluation are green.

Automatic promotion (ADR-0018, slices A–C, `123ebdd`). An observation the owner makes through the CLI becomes
an active memory in the same commit rather than waiting in a queue; it is marked
`auto_promoted_pending_review`, derived from the ledger rather than stored, and reviewed afterwards
with `aptuni memory review list|accept|edit|reject|pin`. Host proposals, sensitive modules and
anything contradicting a record still standing keep the ADR-0013 confirmation. Reminders appear in
`status`, `doctor` and `aptuni memory review reminders`, never as a prompt.

Slice A landed first on its own and was deliberately behaviour-preserving: "revoked" had meant
"any review event targeting a memory", which was only ever correct because a revocation was the
one event that could target one. `accept` and `pin` break that, and the new test shows an `accept`
event removing a memory from `memories()`, the Mem0 rebuild and the hybrid lane while `exposable()`
and export kept it.

Review 56 BLOCKed on six findings, all remediated test-first: a superseded memory left in the
Profile export, non-idempotent decisions once a memory was pinned, a reminder marker that could
crash the command or silence reminders forever, the reminder missing from `status`/`doctor`, no
`review_state` in the Context API, and `edit` ignoring `ingest_enabled`. The two highest-risk
claims held under direct attack: nothing can be promoted that the ADR says must be confirmed, and
MCP cannot promote. Full gate: 598 passed, 3 optional skips, 47 subtests.

The Obsidian vault source (`342de4e`) adds `aptuni source add-obsidian` and runs through the ordinary sync
pipeline. Only a directory holding a real `.obsidian/` counts as a vault; `.obsidian/`, `.trash/`
and every attachment are excluded before any read. Identity is the vault-relative path reconciled
by the existing `reconcile_keyed`, so a rename stays a `move`. `obsidian.locator@1` carries bounded
topology — note name, folder, wikilink targets, tags, aliases, frontmatter property *names* — while
property *values* are dropped and the excerpt is taken after the frontmatter block is removed. The
frontmatter grammar is a clean-room subset with no YAML dependency. A vault that stops being a
vault mid-scan fails closed. ADR-0017 is accepted; `source.obsidian` is now `builtin`.

Review 55 BLOCKed on three findings, all remediated test-first with mutation-verified regressions:
a UTF-8 BOM (and a `...` line) defeated frontmatter minimization and put property values into the
indexed excerpt — live on the maintainer's own vault, 64 BOM notes holding 101 property values; the
injection tests were vacuous while `note_name`, `folder_path` and the CLI evidence row were
unsanitized, so a crafted filename forged an evidence row with a live ANSI escape; and the plugin
manifest denied reading note bodies while storing an indexed 280-character body excerpt. Fixing the
second hardened the `aptuni evidence` row for the Folder and GitHub providers too, which is a
user-visible rendering change recorded under `### Changed` in the CHANGELOG. Full gate: 542 passed,
3 optional skips, 47 subtests. Review 55 is **APPROVE WITH NON-BLOCKING NOTES**.

The opt-in hybrid retrieval preview (`37f21fe`) adds `aptuni search --hybrid`. It fuses SQLite/FTS ranks with
semantic ranks from the selected Mem0 generation by deterministic reciprocal-rank fusion; provider
scores are diagnostic only and cannot reorder anything. The semantic lane returns canonical Memory
IDs only, is filtered to accepted non-revoked memories in permitted modules, and is hydrated solely
from the final stable canonical snapshot after a repeated exposure check. Absent, stale, invalid or
cleanup-required provider state raises a bounded remediation error rather than falling back
silently. Default search, the Context API and MCP are untouched. `tools/run_evals.py` is at
evaluator version 2 with an additive checksum-bound fusion fixture; the frozen S03 corpus and its
thresholds/holdout are unchanged. ADR-0004 and ADR-0003 carry 2026-09-22 amendments;
`retrieval.hybrid` is now `preview`. Two honest preview limits are documented: the semantic lane has
no relevance floor (KI-021) and `score` is comparable only within one invocation. Full gate: 501
passed, 3 optional skips, 47 subtests; the isolated hash-locked runtime passes 55, including a real
Mem0 2.0.20 rebuild-then-search. Review 54 is **APPROVE WITH NON-BLOCKING NOTES**.

The Mem0 projection preview (`e2a06e5`) adds `aptuni memory provider status|rebuild|delete`. It projects only
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

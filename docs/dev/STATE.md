# Project State

**Updated:** 2026-09-20
**Current gate:** Milestone 1 — Portable Personal Context Core (Gate 0 closed 2026-09-19, review 15)
**Production code:** in progress. The `aptuni` package lives in `src/aptuni/`; the Vault/CLI core,
Folder, GitHub and MarginNote 4 sources, builtin interaction memory, bilingual SQLite/FTS projection,
bounded Context API, permissioned MCP STDIO server, Claude/Codex adapters, Profile export, and the
read-only Plugin Advisor are runnable. The repository has bilingual READMEs and community files for
open-sourcing (not yet pushed or published).

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Product identity

- Public name **Aptuni** ("Context, attuned to you"). Brand: `docs/brand/`; assets: `assets/brand/`.
- License Apache-2.0 (`LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`). ADR-0009 is accepted.
- Pre-public git history was rewritten on 2026-09-19 to remove a local username path. Every object
  was scanned and none contains it.

## Implemented durable artifacts

- Canonical PRD v2.1, design rationale, ADR-0001–0013 (all **Accepted** 2026-09-19 with dated
  amendments), roadmap, threat model, compatibility and evaluation plans.
- Gate 0 spikes S01–S05A all PASS with independent reviews (S04 and S05A focused round 3; S01–S03
  in the batched exit review 15).
- Thin research memory: `PROJECT_KNOWLEDGE.md` → `docs/research/`.
- Relay harness: `AGENTS.md` (execution policy: steady, fast vertical slices), `CLAUDE.md`,
  `tools/check_relay.py`.

## Implemented (Milestone 1)

- **Slice 1 — Vault core and CLI (runnable).** `aptuni init | status | remember | facts | correct |
  retract | module list/set | doctor`. The canonical records use the S05A locator; the Vault is
  crash-safe (S01 protocol, recover on open, incremental validation, segment cache); the module
  policy fails closed with independent ingest/expose switches. Review 16 found two blockers and
  eight important notes; remediation 16 fixed them test-first. Independent focused re-review 19
  (Claude subagent, 2026-09-19) verified F1–F5 and F8–F11 and closed the stream **APPROVE WITH
  NON-BLOCKING NOTES**; its notes N1–N5 are in `BACKLOG.md` (N1, a torn-ledger-then-purge case, is
  scheduled first).
- **Slice 2 — Folder Source (runnable).** `aptuni source add-folder/list`, `aptuni sync`, `aptuni
  evidence`, and `aptuni review list`. The S05A contract is promoted into production; sync emits
  minimized exposure Evidence, handles edits/moves/removals conservatively, holds ambiguous identity
  for review, excludes common secrets/hidden/VCS/binary content, and replays idempotently after a
  crash between canonical commit and source-state save.
- **Slice 3 — SQLite/FTS retrieval (runnable).** `aptuni search` and `aptuni index
  status/rebuild/delete`. The disposable state-directory projection uses S03's deterministic
  `unicode61` plus 2–4-character CJK lexemes, automatically repairs missing/stale/corrupt state,
  serializes atomic rebuilds, never lets an older Vault sequence replace a newer index, and hydrates
  IDs only after a final stable exposure-policy check.
- **Slice 4 — Bounded Context API (runnable).** `aptuni identity` returns conservative L0 from
  permitted user-declared identity facts; `aptuni context` returns deterministic L1–L3 and opt-in
  minimized L4 Evidence. Every response reports canonical IDs, layers, provenance/taint, policy
  epoch, Vault sequence, exact used/remaining response units, and truncation. The service discards
  and retries responses if policy changes during retrieval or during final budget packing. This
  slice is `owner_cli` only; MCP host/model egress is not implicitly authorized.
- **Slice 5 — Bounded MCP STDIO (runnable, `d4cc1fb`).** `aptuni-mcp` exposes content-free health,
  bounded L0 identity, and explicit-module L1–L4 context tools over application services. Personal
  reads require a process-bound principal, exact read scopes, allowed modules, and either
  core-admitted `proven_local` execution or `host_model_egress`. Principal/authority are absent from
  tool inputs, no approve/write tool exists, and the production entry point defaults to content-free
  denial. MCP Python SDK 2.2.0 is locked; the process denies Internet/TCP sockets.
- **Slice 6 — Claude/Codex adapter bundles (runnable, `f7fb727`).** `aptuni adapter plan/apply`
  creates a full informed-egress preview, asks for terminal `APPLY`, then writes a mode-0600 exact-ID
  grant and deterministic Aptuni-owned bundle. Both hosts register grant-bound STDIO MCP; Claude's
  bundle adds a bounded SessionStart L0 command. Cancellation creates no grant/bundle and repeat
  apply is idempotent. Host class remains `remote_unknown`; config/tool/env labels cannot elevate it.
- **Slice 7 — GitHub Standard Source (runnable, `0190cf6`).** `aptuni source add-github` stores an
  exact official/enterprise origin plus optional ref and environment credential reference; `aptuni
  sync` resolves a commit, traverses bounded trees, selects deterministic text/code scope, verifies
  Git blob identity, and emits minimized Evidence through the common snapshot/delta pipeline.
  Secret/hidden/cache/VCS paths are excluded before fetch. Exact-origin redirects, response/blob
  sizes, rate limits, truncation fallback, crash/ref-advance replay, and concurrent syncs fail closed.
  Independent Review 18 is `APPROVE`.
- **Slice 8 — Plugin catalog, Recipes, i18n and Plugin Advisor (runnable, `e3dbd2e`).** ADR-0014:
  one TOML manifest per plugin/recipe with honest maturity (only `builtin` is selectable); `aptuni
  advise` (PRD §50 questions, language first, or options/`--json`), `aptuni plugin list`, `aptuni
  recipe list|show`; English and Simplified Chinese catalogs with parity tests. Read-only; the plan
  digest is language independent. Review 20 BLOCK (local-only overclaim) → remediation → Review 21
  APPROVE WITH NON-BLOCKING NOTES.
- **Slice 9 — MarginNote 4 direct local source (runnable).** `aptuni source discover-marginnote |
  add-marginnote`, then normal `aptuni sync`: explicit discovery is separate from ingestion consent;
  the Core Data SQLite store is opened read-only behind a timed macOS TCC probe and a fail-closed
  schema fingerprint. Native note/notebook IDs drive incremental identity. `marginnote.locator@2`
  stores identity/topology only; bounded concept digests preserve learning path, depth and boundary
  without note bodies. Real dogfood: 1,896 notebooks, 82,997 notes → 26,417 concepts, 7.9 s initial
  full-library sync and deterministic no-op re-sync. Review 24 BLOCK → remediation → focused review
  25 **APPROVE WITH NON-BLOCKING NOTES**; ADR-0015 is accepted and KI-004/KI-020 are closed for the
  flagship native-ID path.
- **Slice 10 — Builtin interaction-memory lifecycle (runnable).** `aptuni observe`, `aptuni memory
  pending|list|accept|reject|forget`, plus opt-in MCP `aptuni_propose_memory`. Host proposals are
  scope/module bounded, content-filtered, principal/payload-idempotent and always quarantined. Only an
  expiring digest/nonce confirmation path creates or revokes a Memory; the ReviewEvent atomically
  records nonce consumption. Review 26's four blockers were remediated test-first; focused re-review
  28 is **APPROVE WITH NON-BLOCKING NOTES**.
- **Slice 11 — Owner-readable Profile export (runnable).** `aptuni export PATH [--json]` creates a
  private Markdown/YAML current-view copy outside the canonical Vault. It includes hidden modules
  with a warning, excludes pending/rejected/revoked and every `full_content` record, escapes tainted
  Markdown, uses mode 0700/0600 and same-parent atomic publication, and explicitly says it is not a
  restorable backup. Review 27 **APPROVE WITH NON-BLOCKING NOTES**.
- **Slice 12 — Privacy inventory and purge (runnable, `0b0eabf`+`2440e6e`).** `aptuni privacy status` lists every
  managed copy class and names the ones Aptuni cannot delete — exports, original sources and host
  provider transcripts — with retention, backup inclusion and deletion control per copy, and never
  any record content. `aptuni privacy purge preview | confirm | cancel` performs an exact,
  digest-bound, expiring, nonce-confirmed deletion: canonical records go with deletion-ledger
  digests, source replay state and adapter grants/bundles/pending plans in the frozen set are
  removed, the retrieval projection is always invalidated, and the receipt reports per copy what
  actually happened with structured provider/destination/data-class fields for external copies.
  A committed intent freezes the scope, so every canonical writer fails closed until the action is
  terminal or cancelled; an unsatisfiable scope becomes `incomplete_retryable`, never an escaping
  error. `Vault.restore_from` stages the replacement and a durable journal that `recover()` replays,
  so restore is atomic, chain-preserving and never destroys replay state first. HEAD moves to
  format 2 with a recorded `chain_base` (ADR-0001 amendment) and format 1 migrates on open, keeping
  a legacy purged Vault verifiable and its backups restorable. Reviews 29, 30 and 31 each returned
  BLOCK (B1–B7, R1–R3, F1–F2); every finding was remediated test-first and focused re-review 32 is
  **APPROVE WITH NON-BLOCKING NOTES**. Backlog items Review 15 F2, Review 16 F6/F7 and Review 19 N3
  are closed by this slice.
- **Slice 13 — Digest-bound guided setup (runnable; checkpoint pending).** `aptuni setup plan`
  freezes the advisor answers, full catalog version, exact Folder/GitHub/MarginNote source
  configuration, selected modules, host egress disclosure and every adapter bundle file without
  creating the Vault, source, grant or bundle. `aptuni setup apply ACTION_ID` revalidates that
  recommendation, repeats the complete advisor and effect preview, accepts terminal `APPLY`, and
  journals each application-service effect through doctor and a bounded smoke task. Failure stops
  later effects; retries repair partial adapter bundles without duplicating or stealing ownership of
  grants; completed actions are idempotent; cancel revokes only grants this action created and names
  the Vault/source data it deliberately keeps. `local_only` creates no host egress. Review 33 BLOCK
  findings B1–B6 and follow-up crash/ownership counterexamples were remediated test-first; focused
  Review 34 is **APPROVE** with no remaining findings.
- **Retrieval fallback (`82ad8ee`).** All-terms FTS first, then stopword-filtered bm25 any-term
  matches above a relative floor, so task-shaped queries find context (ADR-0004 amendment).
- **Vault hardening (`ec4ebbe`).** Torn deletion-ledger tail repaired before append (Review 19 N1);
  unsafe-state failures end in a fixed CLI message, `APTUNI_DEBUG=1` re-raises (N2).
- **Open-source readiness (`048556b`).** README/README.zh-CN (verified quickstart), CONTRIBUTING,
  SECURITY, CODE_OF_CONDUCT, CHANGELOG, CITATION.cff, `.github/CODEOWNERS`.

## In progress

- Slice 13 is validated and awaiting its local checkpoint commit; nothing is pushed.

## Awaiting maintainer decisions

- None. Product/repository name **Aptuni** and `@ruihaomei` as CODEOWNER are confirmed. Private
  vulnerability reporting and GitHub/PyPI collision checks remain public-release checklist items,
  not current engineering blockers. Brand vector masters/social assets remain non-blocking.

## Next highest-priority task

1. **Close and order the remaining M1 exit matrix.** Produce an accepted TDD plan that maps each
   still-open M1.1/M1.3/M1.4/M1.5 binary exit gate to current evidence or one bounded implementation
   slice. The known gaps are backup/restore/migration drills, the versioned evaluation harness, S12
   real-host probes, clean artifact/SBOM/license/security gates, and four post-contract skills.
2. Execute the first dependency-ready vertical slice from that plan; do not infer public-release
   authorization or claim Linux support before its exact runner evidence exists.

## Latest validation state

- `.tools/bin/uv run pytest`: 393 passed, 47 subtests passed; `ruff check .` and strict `mypy src`:
  clean (2026-09-20 guided-setup gate).
- Guided-setup focused suite: 51 passed. Review 34 reproduced a mid-bundle crash and verified that
  retry restores the complete Codex bundle, preserves grant ownership and shows the full
  recommendation plus exact effect plan before `APPLY`.
- Privacy purge dogfood: `init → remember → search → privacy status → purge preview → confirm`
  deleted the target Fact, removed the projection, and a raw byte scan of the *rebuilt* SQLite
  confirmed the purged text is absent while the surviving Fact is still searchable; `doctor` passed.
  A source root containing an ESC sequence and a newline renders in `privacy status` as one bounded,
  escaped, flagged token and cannot forge a row.
- Clean-wheel `aptuni advise --json` and `aptuni recipe list --lang zh-CN`: pass (22 TOML data files ship).
- README quickstart (`init → remember → add-folder → sync → context --evidence`) run end to end.
- `python3.13 tools/check_relay.py`: pass (Markdown link, ADR-index and workspace-text checks).
- `python3.13 -m unittest tests/dev/test_check_relay.py`: 20 tests OK.
- `/opt/homebrew/bin/python3.13 spikes/s03_fts/run_s03.py verify`: recorded bilingual retrieval evidence reproduced.
- `.tools/bin/uv build` plus clean-wheel `init → remember → search → index status`: pass; 6 installed packages compatible.
- Clean-wheel `identity → bilingual context` smoke: L0 and L1–L3 layers, budget accounting, canonical IDs, and owner-only audience all verified.
- Clean-wheel `aptuni-mcp` smoke: SDK STDIO EOF shutdown and content-free default start pass; the
  Internet/TCP socket canary fails closed with `aptuni_mcp_network_denied`; dependency check passes.
- Clean-wheel adapter smoke: `plan → terminal apply → grant-bound aptuni-mcp` passes; generated
  Claude bundle and private grant are present; dependency check passes.
- Live GitHub dogfood (`ruihaomei/ctffr-app`): repository ID `1352604752`; initial configured sync
  admitted 38 bounded text/code items, repeat sync was a no-op, historical commits reproduced a real
  removal, hidden-path policy withdrew one previously admitted item, and `doctor` passed. The sample
  has no real rename commit, so rename remains fixture-covered rather than live-observed.
- Spike evidence: S01 46, S02 12, S03 23, S04 58 (+5 skips), S05A 95 tests. Commands are in each
  spike README.

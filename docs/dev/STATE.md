# Project State

**Updated:** 2026-09-19
**Current gate:** Milestone 1 — Portable Personal Context Core (Gate 0 closed 2026-09-19, review 15)
**Production code:** in progress. The `aptuni` package lives in `src/aptuni/`; the Vault/CLI core,
Folder and GitHub sources, bilingual SQLite/FTS projection, bounded Context API, fail-closed MCP
STDIO server, Claude/Codex adapters, and the read-only Plugin Advisor are runnable. The repository
has bilingual READMEs and community files for open-sourcing (not yet pushed or published).

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-github-source=APPROVE; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

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
- **Retrieval fallback (`82ad8ee`).** All-terms FTS first, then stopword-filtered bm25 any-term
  matches above a relative floor, so task-shaped queries find context (ADR-0004 amendment).
- **Vault hardening (`ec4ebbe`).** Torn deletion-ledger tail repaired before append (Review 19 N1);
  unsafe-state failures end in a fixed CLI message, `APTUNI_DEBUG=1` re-raises (N2).
- **Open-source readiness (`048556b`).** README/README.zh-CN (verified quickstart), CONTRIBUTING,
  SECURITY, CODE_OF_CONDUCT, CHANGELOG, CITATION.cff, `.github/CODEOWNERS`.

## In progress

- MarginNote S05B. `spikes/s05b_marginnote/` replays the production OPML reconciler over the
  maintainer's real MarginNote 4 backup history (incremental snapshots reconstructed by overlay):
  108 notebooks, 298 transitions, 131,902 nodes, **0 links across different content**. Refinements
  R1 (same-slot identical siblings) and R3 (weak structural match → review) cut review items 61%
  (25,534 → 10,048); R2 was rejected by Review 22. KI-020 stays open: review burden (≈34/sync in the
  harness, partly artifacts) and the real exporter's OPML shape are unresolved.

## Awaiting maintainer decisions

- **MarginNote OPML export:** one full-notebook OPML export and one focus-branch export of the
  same notebook, placed anywhere local; tell the agent the paths. Required to close KI-020.
- **Before publishing:** choose the public GitHub repository name, enable GitHub private
  vulnerability reporting (SECURITY.md relies on it), confirm `@ruihaomei` in `.github/CODEOWNERS`,
  and re-check `aptuni` name availability (BACKLOG).
- Brand vector masters and social assets remain non-blocking (see `docs/brand/README.md`).

## Next highest-priority task

1. **MarginNote locator minimization (ADR-0006 amendment + review).** The S05A locator stores each
   node's full `ancestor_path` text and unknown attributes in source state and Evidence provenance,
   which reproduces the mind map (full-content retention). Define `marginnote.locator@2`: keep
   structural fields (`parent_node_id`, `children_signature`, `sibling_index`), replace ancestor
   text with hashes or a bounded path, allowlist attributes. Then build `aptuni source
   add-marginnote PATH.opml` + sync in a new `application/marginnote_ingest.py` (reuse
   `_read_approved_file`, bounded size; skip empty-text nodes; `exposure` by default, `studied` only
   when the source's authority policy lists `knowledge.studied`). Keep `source.marginnote` at
   `preview` until KI-020 closes with a real export replay.
2. Guided-setup apply step (plan 02 steps 1, 4, 5): `SetupPlan` bound to the advise digest, one
   terminal confirmation, install, doctor, smoke.

## Latest validation state

- `.tools/bin/uv run pytest`: 268 passed, 47 subtests passed; `ruff check .` and `mypy` (strict): clean.
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

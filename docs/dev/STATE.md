# Project State

**Updated:** 2026-09-25
**Current gate:** Milestone 3 real dogfooding — all three activation paths verified end to end; the
first longitudinal trial drove an Evidence-rank fix and an Evidence-mode evaluator (Review 66); the
second fixed silent Notion session refresh (Review 67)
**Production code:** in progress. The `aptuni` package lives in `src/aptuni/`; the Vault/CLI core,
Folder, GitHub Standard/Deep, MarginNote 4, Obsidian and official-MCP Notion sources, builtin
interaction memory, bilingual SQLite/FTS projection, bounded Context API, permissioned MCP STDIO
server, Claude/Codex adapters, Profile export, the read-only Plugin Advisor, longitudinal
evaluation, the Obsidian owner interface and the versioned public developer SDK are runnable. The public repository is
`https://github.com/ruihaomei/aptuni`; `main` tracks `origin/main`.

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-ci-supply-chain=APPROVE_WITH_NON_BLOCKING_NOTES; m1-evaluation-harness=APPROVE; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-owner-backup-restore=APPROVE; m1-post-contract-skills=APPROVE; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-real-host-s12=APPROVE; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; m2-automatic-promotion=APPROVE_WITH_NON_BLOCKING_NOTES; m2-github-deep=APPROVE_WITH_NON_BLOCKING_NOTES; m2-hybrid-retrieval=APPROVE_WITH_NON_BLOCKING_NOTES; m2-longitudinal-dogfooding=APPROVE; m2-mem0-admission=APPROVE_WITH_NON_BLOCKING_NOTES; m2-mem0-projection-adapter=APPROVE_WITH_NON_BLOCKING_NOTES; m2-notion-source=APPROVE_WITH_NON_BLOCKING_NOTES; m2-obsidian-interface=APPROVE; m2-obsidian-source=APPROVE_WITH_NON_BLOCKING_NOTES; m2-profile-promotion=APPROVE_WITH_NON_BLOCKING_NOTES; m3-context-evidence-rank=APPROVE_WITH_NON_BLOCKING_NOTES; m3-notion-activation-delta=APPROVE_WITH_NON_BLOCKING_NOTES; m3-notion-credential-hardening=APPROVE_WITH_NON_BLOCKING_NOTES; m3-notion-token-expiry=APPROVE_WITH_NON_BLOCKING_NOTES; m3-owner-labelled-evaluation=APPROVE_WITH_NON_BLOCKING_NOTES; m3-public-api-plugin-platform=APPROVE; m3-real-activation=APPROVE; relay-claude-code=PASS; relay-codex=PASS; release=APPROVE; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

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

## Real owner activation and dogfooding (2026-09-24/25)

- The canonical Vault lives in the owner work root's private `.aptuni/` namespace with private
  directory/file modes; direct initialization of the non-empty work root failed before mutation, and
  unrelated Obsidian/work content was neither reorganized nor overwritten. `status` and `doctor`
  pass. The enabled Obsidian plugin uses the repository virtual-environment executable, shows
  Profile, Memory, Evidence, Recent Changes and Pending Reviews, and visibly confirmed one
  deterministic canonical accept action.
- The official Notion MCP source syncs one private, non-sensitive fixture page as its sole exact
  root through Aptuni's own Keychain OAuth session, with stable provenance and a no-op re-sync. That
  OAuth client is deliberately separate from any host agent's Notion connector; no connector
  credential was copied or bypassed, and the owner authorized Aptuni once with `connect-notion`.
  Activation fixes (`pvs` URL hint, native Keychain calls, `<content>` envelope, unverified
  completeness → `partial`) are checkpointed at `1ae1d8f` (Reviews 64 and 65).
- **First longitudinal trial (content-free).** An Evidence-answerable query in default Context
  returned 2/2 unrelated Profile/Memory records. Root causes: default Context is L3-only by
  ADR-0005 and the evaluator could not request L4; with Evidence requested, an L3-before-L4 sort
  displaced and budget-truncated better-ranked Evidence; the residual L3 noise is the specified
  ADR-0004 fallback (KI-018). Fixed at `1d93ff8`: rank-preserving Context ordering and `evaluate
  trial --evidence` with schema v3 (Review 66). Live after-state on the same query: Profile/Memory-only
  mode 0/2 useful (unchanged, by contract); with-Evidence mode 1/1 useful, 0 noise; 0 exposure
  violations. Those labels were agent-assigned on the synthetic fixture, so all three trials were
  later removed with `evaluate discard`; the live dataset now holds only owner-labelled trials (none
  yet) plus two content-free snapshots.
- **Second dogfood issue.** A day after authorization, sync demanded a browser re-authorization and
  printed an SDK traceback: MCP SDK 2.2.0 forgets token expiry across processes and answers the
  resulting 401 with a full authorization instead of the refresh grant. Aptuni now persists the
  absolute expiry in the same Keychain item and restores it; the live sync refreshed silently and
  was a no-op, and OAuth failures now print the bounded Aptuni message (`327dbf4`). Review 67 approves with
  non-blocking notes (applied or recorded in `BACKLOG.md`).

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
- **Slice 13 — Digest-bound guided setup (runnable, `db7a5d9`).** `aptuni setup plan`
  freezes the advisor answers, full catalog version, exact Folder/GitHub/MarginNote source
  configuration, selected modules, host egress disclosure and every adapter bundle file without
  creating the Vault, source, grant or bundle. `aptuni setup apply ACTION_ID` revalidates that
  recommendation, repeats the complete advisor and effect preview, accepts terminal `APPLY`, and
  journals each application-service effect through doctor and a bounded smoke task. Failure stops
  later effects; retries repair partial adapter bundles without duplicating or stealing ownership of
  grants; completed actions are idempotent; cancel revokes only grants this action created and names
  the Vault/source data it deliberately keeps. `local_only` creates no host egress. Review 33 BLOCK
  findings B1–B6 and follow-up crash/ownership counterexamples were remediated test-first; focused
  Review 34 is **APPROVE** with no remaining findings. Every confirmed step renders numbered
  1..n in both locales.
- **Slice 14 — Owner backup and restore (runnable, `7500d67`).** `aptuni backup create |
  verify | list | restore` writes a private, manifest-verified canonical copy and restores only after
  an expiring digest-bound preview. The deletion ledger and in-flight restore journal live in the
  Vault, so a purge cannot be undone by an older backup, another machine, a wiped state directory,
  or any crash point. Legacy ledger/journal state migrates on open. Reviews 35–38 found and drove
  regressions for torn ledgers, confirmation honesty/binding, refused restores, empty generations,
  destination safety and cross-state atomicity; Review 39 independently closed the stream
  **APPROVE**.
- **Slice 15 — CI and supply-chain gates (hosted closure, `ad661fc` + `c86e861`).** A least-privilege,
  immutable-action-pinned workflow runs the locked full gate on macOS 15 and Ubuntu 24.04, then
  emits hash-locked runtime requirements, CycloneDX 1.5, pip-audit JSON, byte-identical offline
  wheel/sdist builds and clean-wheel smokes. Dependency notices follow the extra-aware
  cross-platform lock closure; build/audit tools are exact lock members; high-confidence tracked
  credential shapes and artifact legal files fail locally and in CI. Linux resolves the deepest
  `/proc/self/mountinfo` entry and admits only ext4. Hosted run 35520369299 at `c86e861` passed on
  macOS 15 and Ubuntu 24.04, including strict typing, repository contracts and the explicit ext4
  durability gate (91 tests plus 11 subtests); the supply-chain job also passed. Review 40's local
  blockers were remediated; Review 41 is **APPROVE WITH NON-BLOCKING NOTES**.
- **Slice 16 — Versioned evaluation harness (`390aaf6`).** `tools/run_evals.py` verifies every
  checksummed S03 input, scores the production SQLite retriever on separate dev/regression-holdout
  splits, reproduces the frozen context-noise arithmetic, and writes an atomic manifest containing
  commit/runtime/schema/lock/SBOM/input hashes, thresholds and ranked outputs without private
  profile content. CI retains the manifest even when a threshold fails. The first production run
  records dev recall@5 0.992, MRR 1.0 and FPR 0.0; holdout recall/MRR 1.0 and FPR 0.0. The gate
  narrowed any-term fallback to queries whose task-language removal changes the terms. Reviews
  42–43 drove evidence-retention and mutation-test fixes; Review 44 is **APPROVE**.
- **Slice 17 — Real-host S12 journeys.** Exact frozen Claude Code 2.1.267/2.1.266 and Codex
  0.155.0/0.154.0 non-persistent sessions completed the synthetic handoff and exact ungranted-module
  denial. Focused Claude sessions loaded exact absolute file rules; the model emitted no file calls,
  so no denial is claimed, while both exact Apple Event attempts produced no outer effect. The
  runner enforces resolved versions and an external built-wheel runtime, and persists only sanitized
  classifications. Review 48 is **APPROVE**; status remains honestly `unverified`.
- **Slice 18 — Post-contract skills (`884aabc`).** Repository-local `add-source-provider`,
  `run-evals`, `audit-licenses`, and `release` skills encode the stabilized source, evaluation and
  supply/release contracts. Four fixture smokes execute the real bounded commands; release builds
  twice and verifies byte-identical legal-file-complete artifacts. Release remains a local dry-run
  and explicitly cannot publish, tag, push, use credentials or infer maintainer approval. Review 45
  caught implicit `uv run` synchronization; the instructions and fixtures now use `--no-sync` from
  a prepared locked environment, and Review 46 is **APPROVE**.
- **Retrieval fallback (`82ad8ee`).** All-terms FTS first, then stopword-filtered bm25 any-term
  matches above a relative floor, so task-shaped queries find context (ADR-0004 amendment).
- **Vault hardening (`ec4ebbe`).** Torn deletion-ledger tail repaired before append (Review 19 N1);
  unsafe-state failures end in a fixed CLI message, `APTUNI_DEBUG=1` re-raises (N2).
- **Open-source readiness (`048556b`).** README/README.zh-CN (verified quickstart), CONTRIBUTING,
  SECURITY, CODE_OF_CONDUCT, CHANGELOG, CITATION.cff, `.github/CODEOWNERS`.
- **First public release (`v0.1.0`, `33ea08a`).** PyPI and the GitHub Release carry the exact
  reproducible wheel/sdist; tag workflow 35619712980 and release-commit CI 35572245440 passed. A
  fresh PyPI-only install completed CLI, setup/context and MCP safety smokes. Review 50 independently
  inspected the public result and returned **APPROVE**. Exact URLs, hashes and evidence are in
  `docs/dev/releases/0.1.0.md`.

## Implemented (Milestone 2)

- **S10 — Mem0 2.0.20 admission (`84a3a8e`).** The isolated hash-locked harness admits only a disposable local
  projection populated with accepted canonical records and `infer=False`. Mem0-owned inference is
  rejected because it retains raw input in history. Record-level `Memory.delete()` leaves bytes in
  Qdrant/history, so privacy deletion requires closing and removing the entire managed provider root
  and rebuilding active records from the Vault. Restart, fresh-root rebuild, exact projection
  equality, canonical-byte isolation, managed-root purge and guarded network paths passed. The
  focused suite passes 15/15 in the isolated runtime; Review 52 is **APPROVE WITH NON-BLOCKING
  NOTES**.
- **Mem0 projection adapter preview (`e2a06e5`).** `aptuni memory provider status|rebuild|delete` materializes
  current accepted canonical memories into an exact fresh Mem0 generation with `infer=False`, then
  atomically selects it. Mem0 2.0.20 and Ollama 0.6.2 are optional exact pins; the client accepts
  numeric loopback only, ignores environment proxies, refuses redirects and never pulls a model.
  Privacy purge and explicit delete remove the whole managed root, and rebuild is serialized with
  purge to prevent resurrection. Malformed enumeration and every tested pre/post-publication
  failure fail closed or surface `cleanup_required`. Review 53 is **APPROVE WITH NON-BLOCKING
  NOTES**.
- **Opt-in hybrid retrieval preview (runnable, `37f21fe`).** `aptuni search --hybrid` fuses the builtin
  SQLite/FTS ranks with semantic ranks from the selected Mem0 generation using deterministic
  reciprocal-rank fusion. Only rank positions are used; provider scores are diagnostic and cannot
  reorder anything. The semantic lane returns canonical Memory IDs only, is limited to accepted
  non-revoked memories in permitted modules, and is hydrated exclusively from the final stable
  canonical snapshot after a repeated exposure check. A missing, stale, invalid or
  cleanup-required projection is a bounded remediation error, never a silent lexical fallback.
  Default `aptuni search`, the Context API and MCP are unchanged. `tools/run_evals.py` moves to
  evaluator version 2 and scores an additive checksum-bound fusion fixture with its own dev/holdout
  splits; the frozen S03 lexical corpus, judgments, thresholds and holdout are untouched. ADR-0004
  and ADR-0003 carry 2026-09-22 amendments and `retrieval.hybrid` moves from `planned` to
  `preview`. Review 54 is **APPROVE WITH NON-BLOCKING NOTES** with no blocking findings; notes N1
  (no semantic relevance floor, now KI-021), N2, N3, N4, N6, N7, N8, N9 and N10 were applied in the
  checkpoint and N5 (test fidelity) is in `BACKLOG.md`.

- **Obsidian vault source (runnable, `342de4e`).** `aptuni source add-obsidian PATH --module M` plus the
  ordinary `sync`/`evidence`/`review`/`search` pipeline. Only a directory holding a real
  `.obsidian/` is a vault; a plain folder is refused and pointed at `add-folder`. The vault's own
  `.obsidian/` and `.trash/` are excluded by name at the root, and only regular non-symlinked
  `*.md` files are opened — attachments are counted, never parsed. Identity is the vault-relative
  path reconciled by the existing `reconcile_keyed`, so a rename is a `move`. `obsidian.locator@1`
  carries bounded topology: note name, folder, wikilink targets, tags, aliases, frontmatter
  property *names*, heading count. Property *values* are dropped: the Evidence excerpt is taken
  after the frontmatter block is removed, so they reach neither the locator, the excerpt, nor the
  search index. The frontmatter grammar is a clean-room subset with no YAML dependency; anything
  outside it admits the note and reports `frontmatter_unsupported`. A vault that stops being a
  vault mid-scan fails closed instead of retracting every note. ADR-0017 is accepted and
  `source.obsidian` moves from `planned` to `builtin`. Review 55 returned **BLOCK** on three
  findings — a UTF-8 BOM and a `...` line defeated frontmatter minimization and put property
  values into the indexed excerpt; the injection tests were vacuous while `note_name`,
  `folder_path` and the CLI evidence row were unsanitized, so a crafted filename forged an
  evidence row; and the plugin manifest denied reading note bodies while storing an indexed
  280-character body excerpt. All three were remediated test-first with mutation-verified
  regressions, and the final verdict is **APPROVE WITH NON-BLOCKING NOTES**.
- **Automatic promotion and retrospective review, slices A–D (runnable, `123ebdd` + `6d936f3`).** An observation the owner
  makes through the CLI now becomes an active memory in the same commit instead of waiting for a
  confirmation. It is marked `auto_promoted_pending_review` — derived from the ledger, not stored —
  and reviewed afterwards with `aptuni memory review list|accept|edit|reject|pin`. Host proposals,
  sensitive modules (`identity`, `relationships`, `behavior`) and anything contradicting a record
  still standing keep the ADR-0013 confirmation; a module that cannot ingest or cannot expose is
  denied outright rather than asked about. Reminders are a line in `status`, `doctor` and
  `aptuni memory review reminders`, never a prompt, defaulting to ten pending or fifteen days from
  the oldest pending memory, with `snooze` and `snooze --clear`.
  `aptuni memory review policy --auto-promotion off` restores the old behaviour entirely.
  Slice A corrected a shared derivation first: "revoked" was "any review event targeting a memory",
  which would have silently hidden memories from four subsystems once `accept`/`pin` could target
  one. `ReviewEvent` gains schema v2 (`policy_auto`, `pin`) resolved per record type, so no
  existing record migrates and a 0.1.0 install fails closed with `SchemaVersionError`. ADR-0018 is
  accepted. Review 56 returned **BLOCK** on six findings — a superseded memory left in the Profile
  export, non-idempotent decisions on a pinned memory, a reminder marker that could crash or
  silence reminders forever, the reminder missing from `status`/`doctor`, no `review_state` in the
  Context API, and `edit` ignoring `ingest_enabled` — all remediated test-first, and the final
  verdict is **APPROVE WITH NON-BLOCKING NOTES**. Slice D adds bounded
  `aptuni_get_memory_review` access to the permitted pending set and reminder under the exact
  `memory.review.read` scope. The feed reuses module/exposure/egress gates and a final canonical
  sequence check. Its structural regression pins both the MCP handler allowlist and transitive
  service/mixin reachability from every MCP read facade, so promotion, owner decisions and commit
  sinks cannot enter a read path silently. Review 57 initially blocked the direct-only proof, then
  approved the transitive remediation with one non-blocking disposable-snooze race note.
- **Automatic Profile promotion (runnable, Review 59).** An owner-pinned current Memory becomes one
  stable Profile Fact only when its complete support is owner-declared CLI material, current module
  ingest and expose permissions both allow it, no unresolved candidate contradicts it, automatic
  promotion is enabled, and no historical promoted Fact already names it. Pin, policy event and
  exact lineage-linked Fact commit atomically; `aptuni profile refresh` repairs older pins and is
  idempotent even after rejection. `aptuni profile review list|accept|reject` supplies retrospective
  review, while Context marks pending promoted Facts explicitly. Canonical validation binds exact
  statement, module, provenance, temporal fields, evidence, fixed labels and unique transition
  events at incremental commit time. ADR-0020 is accepted; Review 59 is **APPROVE WITH
  NON-BLOCKING NOTES** after five independently reproduced contract blockers were remediated.
- **GitHub Deep authored activity (runnable, `f994446`).** `aptuni source add-github URL --deep-actor
  LOGIN --module M --role R` creates an additive `github_deep` source; GitHub Standard is unchanged.
  One explicit linked login is used to attribute only repository-local authored commits, opened pull
  requests and submitted reviews. Deep never reads blobs, diffs, bodies, comments, emails, issue or
  discussion threads, file lifecycle, or cross-repository account activity. `github.activity@1`
  stores only the exact repository/activity identity, occurrence time, mode and bounded commit/PR
  metadata declared by ADR-0019. Commits and PR search are capped at five 100-item pages; review
  discovery is capped at 100 candidate PRs, two pages per PR, 100 requests and 500 admitted reviews;
  every Deep response is capped at 2,000,000 bytes. Any exhausted or changing search boundary makes
  the combined snapshot partial, so absence cannot withdraw prior Evidence. Malformed identity,
  rate limits and response overruns abort without changing Evidence or source state. Review 58 first
  blocked boolean/non-positive repository IDs, an undeclared locator field and missing cap
  regressions; all were remediated, and the final verdict is **APPROVE WITH NON-BLOCKING NOTES**.
- **Official Notion MCP source (runnable, Review 60).** `aptuni source connect-notion` authorizes
  Aptuni's own OAuth/PKCE client against `https://mcp.notion.com/mcp`; credentials remain in
  macOS Keychain. `add-notion` grants only exact normalized page/database roots. Sync calls
  `notion-get-users(self)` for connection identity and `notion-fetch` for those roots—never
  search, workspace browsing or writes—then emits minimized Evidence with `notion.locator@1`.
  Ambiguous IDs, malformed provenance/completeness, bounds, auth loss and schema drift fail closed;
  missing/truncated/unknown roots cannot withdraw prior Evidence. ADR-0021 is accepted; Review 60
  is **APPROVE WITH NON-BLOCKING NOTES** after all identity, SDK, exact-scope, validation and
  production-shaped test blockers were remediated.
- **Longitudinal maintainer dogfooding (runnable, Review 61).** `aptuni evaluate setup|trial|score|
  capture|report|reset` measures the ordinary Context path without retaining query or returned
  context text. Private schema-v2 derived state contains only query digests, canonical IDs, labels,
  bounded context metrics and content-free lifecycle snapshots. Reports cover usefulness/noise,
  unsupported useful records, provenance, exposure, source updates, corrections/supersession,
  promotion/review state and context-unit efficiency. Purge and explicit reset remove the full
  dataset. ADR-0022 is accepted; Review 61 is **APPROVE** after deletion-order, terminal-rendering
  and migrated-metric blockers were remediated. One real authorized Folder baseline is recorded.
- **Obsidian owner interface (runnable, Review 62).** `aptuni interface obsidian install VAULT`
  copies the bundled desktop plugin without enabling it. Its versioned, bounded local bridge shows
  Profile, Memory, Evidence, Recent Changes, Pending Reviews and promotion state from one Vault
  snapshot, with explicit truncation and valid-action metadata. Accept/Edit/Reject/Pin, evidence
  display, Profile review and digest-confirmed Forget reuse canonical services. It stores no
  returned personal content and neither scans nor grants access to Obsidian notes. The installer
  pins and revalidates the complete destination path and fails closed on directory swaps. ADR-0023
  is accepted; Review 62 is **APPROVE** after all currentness, consistency, contract-version and
  filesystem-confinement blockers were remediated test-first.

## Implemented (Milestone 3)

- **Versioned public developer API and SDK plugin platform (runnable, `a1a04fb`, Review 63).** `aptuni.api.v1`
  exposes bounded Profile, Memory, Context and minimized Evidence reads plus quarantined memory
  proposals and read-only review queues through immutable `aptuni.api@1` DTOs. Strict
  `aptuni.plugin@1` manifests request authority but grant none; owner-created grants bind an exact
  manifest digest to narrowed capabilities/modules, are revocable, privacy-visible and revalidated
  for every operation. Calls and lifecycle mutations share a no-follow cross-process lock, and one
  deterministic grant generation makes concurrent/interrupted apply single-effect. Aptuni v1 does
  not discover, import or execute third-party entry points. `aptuni developer` supplies inspect,
  scaffold, plan/apply/list/cancel/revoke. The separate Top-Down Learning example completes
  goal → prerequisite map → project-first teaching → learner check → next step, using only the
  public API. ADR-0024 is accepted and Review 63 is **APPROVE**.

## In progress

- Milestone 1 and its first public release are complete. The selected Milestone 2 priorities and the
  first Milestone 3 developer-platform slice are complete; S10, the Mem0
  projection preview, the opt-in hybrid retrieval preview, the Obsidian vault source, automatic
  promotion slices A–D, automatic Profile promotion, GitHub Deep, the official Notion MCP source,
  longitudinal maintainer dogfooding, the bounded Obsidian owner interface, public SDK and flagship
  example are complete.

## Awaiting maintainer decisions

- None blocking. Real usefulness labels beyond the synthetic activation fixture need the owner's own
  queries and judgments; trials on private sources are the owner's call.

## Next highest-priority task

1. The owner runs real trials in both context modes (`evaluate trial [--evidence]`, then
   `evaluate score --useful … --rest-noise`) and periodic `evaluate capture`; agents never invent
   labels. Revisit the KI-018 fallback floor only when real owner-labelled `profile_memory` trials
   show persistent noise. Remaining Notion items in BACKLOG need live server evidence first.
2. Review lessons that carry forward: write injection tests with **real** control bytes (the
   literal text of an escape sequence proves nothing); route every outside-controlled token through
   `sanitize_token` where stored or `delimited_untrusted` where rendered; and when a rule about
   "current records" changes, check *every* view of it — Review 56 found the same supersession gap
   in export, the Mem0 projection and the repeat-observation path after `memories()` was fixed.
3. Keep every source read-only, keep `ingest_enabled`/`expose_enabled` independent, and emit
   minimized Evidence through the common snapshot/delta pipeline with crash/replay coverage.
4. Do not add a remote model or embedding key to any default path; keep provider scores derived and
   policy-check every hydrated result.
5. Keep the 0.1.0 release immutable; any concrete public defect gets a new patch release.

## Latest validation state

- Notion hardening and owner-labelled evaluation (2026-09-25, `6e05e8a` and `1ba862c`):
  full repository gate 801 passed, 3 optional-runtime skips and 62 subtests; Ruff,
  strict mypy, relay and frozen lexical/hybrid evaluation green. Reviews 68 and 69 **APPROVE WITH
  NON-BLOCKING NOTES**. Real Security.framework round trips used throwaway services only.

- Notion session refresh (2026-09-25): full repository gate 767 passed, 3 optional-runtime skips
  and 62 subtests before review-note fixes; focused Notion suites 65 passed after them. Ruff,
  strict mypy, relay and frozen evaluation green; live expired session refreshed silently; Review
  67 **APPROVE WITH NON-BLOCKING NOTES**.

- Real dogfooding fixes (2026-09-25): full repository gate 749 passed, 3 optional-runtime skips and
  62 subtests before review-note fixes; Ruff, strict mypy (95 source files), relay and frozen
  lexical/hybrid evaluation green. Reviews 65 and 66 **APPROVE WITH NON-BLOCKING NOTES**. Live
  Vault: commit 7, `doctor` healthy, evaluation state schema v3 with 3 scored trials.

- Public API/plugin SDK platform: full repository gate 725 passed, 3 optional-runtime skips and 61
  subtests; Ruff, strict mypy (95 source files), relay, notices/secrets/workflow and fresh-artifact
  supply-chain checks, frozen lexical/hybrid evaluation, clean-wheel SDK/scaffold/revoke smoke,
  JavaScript syntax and exact installed Obsidian asset comparison are green. Review 63 independently
  approved the final contract after concurrent, crash and live-revocation adversarial remediation.

- Obsidian owner interface: full repository gate 704 passed, 3 optional-runtime skips and 61
  subtests; Ruff, strict mypy (85 source files), relay, JavaScript syntax, notices/secrets/workflow
  and built-artifact supply-chain checks, frozen lexical/hybrid evaluation and wheel asset
  inspection are green. Review 62 drove stale-Forget, single-snapshot, contract-version and full
  installer path/target continuity fixes to deterministic regressions. Final verdict: **APPROVE**.

- Longitudinal maintainer dogfooding: full repository gate 692 passed, 3 optional-runtime skips and
  61 subtests; Ruff, strict mypy (81 source files), relay, notices/secrets/workflow supply-chain and
  frozen lexical/hybrid evaluation are green. Review 61 verified
  content absence, bounded state/migration, permission metrics, purge/reset closure and terminal
  safety with final verdict **APPROVE**. A real content-free schema-v2 baseline exists at Vault
  sequence 3 for one authorized Folder source and one Evidence record, with zero review backlog and
  zero exposure violations; no retrieval trial was recorded.

- Official Notion MCP source: full repository gate 683 passed, 3 optional-runtime skips and 61
  subtests; Ruff, strict mypy (81 source files), relay, notices/secrets/workflow supply-chain and
  frozen lexical/hybrid evaluation are green. Review 60 independently reproduced and drove fixes
  for identity/tool selection, SDK error handling, exact-scope parsing, absence semantics,
  provenance/completeness validation and production-shaped boundary coverage. Final verdict:
  **APPROVE WITH NON-BLOCKING NOTES**.

- Automatic Profile promotion: full repository gate 642 passed, 3 optional-runtime skips and 47
  subtests; Ruff, strict mypy (76 source files), relay, notices/secrets/workflow supply-chain and
  frozen lexical/hybrid evaluation are green. Review 59 independently reproduced and drove fixes
  for rejection re-promotion, invalid/duplicate transition targets, exact-claim binding, correction
  compatibility and incremental validation. Final verdict: **APPROVE WITH NON-BLOCKING NOTES**.

- GitHub Deep authored activity: full repository gate 627 passed, 3 optional-runtime skips and 47
  subtests; Ruff, strict mypy (74 source files), relay and the notices/secrets/workflow supply-chain
  checks clean; frozen lexical/hybrid evaluation unchanged and green. Review 58 is **APPROVE WITH
  NON-BLOCKING NOTES** after all three blockers and both initial warnings were remediated. Its one
  remaining direct mocked-Urllib response-overrun test suggestion is recorded in `BACKLOG.md`.

- Automatic promotion slice D: full repository gate 600 passed, 3 optional-runtime skips and 47
  subtests; Ruff, strict mypy (74 source files), relay and the notices/secrets/workflow
  supply-chain checks clean; the frozen evaluation passes with unchanged lexical and hybrid
  metrics. Review 57 is **APPROVE WITH NON-BLOCKING NOTES** after its transitive-boundary blocker
  was remediated; the only remaining note is a harmless marker-only race in disposable snooze state.

- Automatic promotion slices A–C: full repository gate 598 passed, 3 optional-runtime skips and 47
  subtests; Ruff, strict mypy (74 source files), relay and the notices/secrets/workflow
  supply-chain checks clean; the frozen evaluation passes with unchanged metrics. CLI dogfood:
  `observe` reports the memory as already in use and names the undo command, `status` and `doctor`
  both show the reminder when due and fall silent after `snooze` until `snooze --clear`, `edit`
  leaves exactly the correction in `memory list`, and `--auto-promotion off` restores the
  confirmation path. Review 56 is **APPROVE WITH NON-BLOCKING NOTES** after six remediated
  blockers.
- Obsidian vault source: full repository gate 542 passed, 3 optional-runtime skips and 47 subtests;
  Ruff, strict mypy (72 source files), relay and the notices/secrets/workflow supply-chain checks
  clean; the frozen evaluation still passes with unchanged lexical and hybrid metrics. Three
  mutation probes confirm the Review 55 blockers are now caught (removing `sanitize_token`'s
  scrubbing fails 4 tests; restoring BOM blindness and the `...` terminator fails 2; un-sanitizing
  `note_name` with a raw CLI row fails 1). Real-vault dogfood: 5,750 Markdown files, 3,814
  admitted, 7.8 s initial sync, 4.0 s deterministic no-op re-sync, `doctor` passed. An
  aggregate-only audit checked all 1,597 non-tag/alias property values against every excerpt and
  every frontmatter-derived locator field: zero reached either, and zero control characters reached
  any sanitized field. That vault has 64 BOM notes holding 101 property values, which is exactly
  what Review 55 B1 would have exposed. No note content was recorded in any artifact.
- Hybrid retrieval preview: full repository gate 501 passed, 3 optional-runtime skips and 47
  subtests; Ruff, strict mypy (69 source files), relay and the notices/secrets/workflow supply-chain
  checks clean. The frozen evaluation run passes with unchanged lexical metrics (dev recall@5
  0.9921569 / MRR 1.0 / FPR 0.0; holdout 1.0 / 1.0 / 0.0) and new hybrid dev+holdout recall@3 1.0 /
  MRR 1.0 over 3 cases each. The hash-locked isolated runtime (S10 lock plus `ollama==0.6.2`) ran
  the Mem0, hybrid and retrieval suites with 55 passed, including a real Mem0 2.0.20
  rebuild-then-search through the production boundary. CLI dogfood: plain `search` returns the
  Fact, and `search --hybrid` without a projection fails closed with the bounded
  `aptuni memory provider rebuild` remediation and no traceback. Review 54 is **APPROVE WITH
  NON-BLOCKING NOTES**.
- Mem0 projection preview: full repository gate 479 passed, 3 optional-runtime skips and 47
  subtests; Ruff, strict mypy (68 source files), 35 developer checks, relay, lock/notices/secrets and
  diff checks clean. The pinned isolated Mem0/Ollama runtime passes all 23 focused tests, including
  real provider rebuild, redirect refusal, purge/rebuild concurrency and publication failures.
  Offline wheel/sdist build exposes only the explicit `mem0` extra. Review 53 is **APPROVE WITH
  NON-BLOCKING NOTES**.
- S10 Mem0 admission: 15/15 focused tests pass in the isolated Mem0 2.0.20 runtime; the standard
  product runtime passes 13 with 2 honest dependency skips. Fresh fixture and Mem0 evidence runs
  reproduce their checked-in JSON byte-for-byte. Full repository gate: 459 tests plus 47 subtests;
  Ruff and strict mypy clean. Review 52 independently reproduced the evidence and returned
  **APPROVE WITH NON-BLOCKING NOTES**.
- Aptuni 0.1.0 public release: tag workflow 35619712980 and release-commit CI 35572245440 passed.
  Fresh PyPI-only Python 3.13 import/version, CLI, synthetic Vault/search/context/doctor, local-only
  setup plan and MCP health/default-deny/EOF/network-confinement smokes passed. Fresh exact-tag,
  hosted, PyPI and GitHub Release artifacts are byte-identical at the hashes recorded in
  `docs/dev/releases/0.1.0.md`; the hosted audit found zero vulnerabilities. Review 50 is
  **APPROVE**.
- Slice 18: 459 tests plus 47 subtests; ruff, strict mypy and 34 developer checks clean. The four
  fixture smokes ran provider conformance tests, a frozen evaluation manifest, no-sync lock/notice/
  secret/workflow checks, and two byte-identical offline builds whose wheel/sdist legal files pass.
  Review 46 independently verified the no-sync remediation and returned **APPROVE**.
- Slice 16: 459 tests plus 47 subtests; ruff, strict mypy, 32 developer checks, relay, workflow and
  secret contracts clean. The SBOM-bound real run reproduced dev recall@5 0.9921569 / MRR 1.0 /
  FPR 0.0 and holdout recall/MRR 1.0 / FPR 0.0; the context-noise example reproduced 328 total and
  82 irrelevant units. Review 44 independently mutation-tested freeze and workflow-retention
  boundaries and returned **APPROVE**.
- Slice 15 hosted run 35520369299 at `c86e861`: macOS 15, Ubuntu 24.04 and supply-chain jobs passed.
  Ubuntu recorded 459 tests plus 47 subtests, ruff, strict mypy, relay and 34 developer checks; the
  explicit ext4 filesystem/concurrency/Vault/backup gate recorded 91 tests plus 11 subtests. The
  supply-chain job retained the frozen evaluation and verified locked audit, reproducible artifacts,
  legal files and a clean-wheel smoke. Review 41 remains **APPROVE WITH NON-BLOCKING NOTES**.
- Slice 17 closure: all four frozen host versions passed the synthetic L0 handoff and exact
  denied-module journey; both Claude versions completed the focused conservative observations.
  The full local gate is 459 tests plus 47 subtests; ruff, strict mypy, relay and 34 developer checks
  are clean. Review 48 is **APPROVE**. Raw host output and sessions were not persisted.
- `.tools/bin/uv run pytest`: 456 passed, 47 subtests passed; `ruff check .` and strict `mypy src`:
  clean (2026-09-20 Slice 14 gate). Backup + Vault focused suites: 84 passed. Review 39 independently
  fault-injected all four restore crash points with fresh state and verified legacy recovery.
- Real CLI backup/privacy dogfood: machine A created pre/post-purge backups; machine B imported the
  portable ledger, restored the older backup, dropped exactly one ledgered record, kept the survivor,
  produced zero raw purged-marker hits and passed `doctor`.
- Guided-setup focused suite: 53 passed. Review 34 reproduced a mid-bundle crash and verified that
  retry restores the complete Codex bundle, preserves grant ownership and shows the full
  recommendation plus exact effect plan before `APPLY`. Dogfood at the checkpoint: `setup plan →
  APPLY → search → evidence → doctor` on a real folder source admitted one Evidence record and
  passed every check.
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

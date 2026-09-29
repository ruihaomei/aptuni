# Backlog

Non-blocking improvements from reviews and self-review. Each item records where it came from.
Pick an item up when its owning slice starts; do not open a review round for these alone.

| Item | Source | Owning slice |
|---|---|---|
| Out-of-band-edit path: quarantine and diff a hash mismatch instead of a read refusal | S01 F2; ADR-0013 item 5 | M1 Vault hardening |
| Segment compaction (chain-preserving rewrite) | S01 F1 | M1 Vault hardening |
| ADR-0001 untested items: same-valid-time conflict, out-of-order observation, export/import round-trip | Review 15 F4 | M1 ingestion + export slices |
| Plugin approval-to-import atomicity; files not listed in RECORD | Review 15 F5 (S02) | Plugin activation slice |
| `spikes/s03_fts/frozen/thresholds.json` says "24k-document" (actual 25,000); the file is hash-frozen, so fix only in a new versioned protocol | Review 15 F6 | none (evidence stays frozen) |
| Re-run S01 in a fresh pinned venv to refresh its recorded run | Review 15 F1 | optional |
| OPML/Folder held-item review loop, stale review items, held growth | S05A rounds 2–3 | Review workflow slice |
| Pending-review ops may also flag dependent facts | S05A round 3 note 2 | Review workflow slice |
| Tests for bad locator values, `records/` and state-directory permissions, and revoking a memory candidate | Review 19 N4 | Next Vault slice |
| Manifest schema: strict typing (`contract_version = true` coerces), duplicate egress/recipe entries, file name must equal `id`, orphan message keys, `suggested_sources` vocabulary | Review 20 N3 | Plugin activation slice |
| i18n polish: localized `recipe show` unknown-id error, CJK list separator `、`, CJK column widths, `--lang fr` notice, Claude Desktop file-access wording, retention heading vs provider-managed data | Review 20 N7, Review 21 | i18n pass |
| R3-demoted parent's children become moves under the parent's new generated ID | Review 22/23 | MarginNote ingest slice |
| Replay harness: hidden truth attribute inflates modify/no-op counts; restart stopped chains at later full snapshots; order roots by canvas position | Review 22/23 | MarginNote ingest slice |
| MarginNote: permanent no-parent-stat TCC pre-probe test; deterministic multi-parent ordering; refresh Evidence on locator-only drift; source-specific crash/replay test | Review 25 R1–R3 | MarginNote hardening |
| Profile export: injected render/rename/race tests, broader adversarial Markdown/control characters, explicit corrected/retracted Fact and withdrawn Evidence chains | Review 27 N2–N5 | Export hardening |
| Memory proposals: extend high-confidence protected-pattern corpus and keep errors/logs content-free; preserve forced concurrent-idempotency regression | Review 28 N3–N4 | Memory hardening |
| Restore journal: fold segment-read failure into journal validation, and tell "journal not applicable, keep the old generation" apart from genuine corruption | Review 31 N1 | Vault hardening |
| Route `source list` and the `source add-folder` / `add-github` echoes through `_delimited_untrusted()` as `privacy status` now does | Review 31 N2 | Source UX hardening |
| Narrow the confusable flag to real confusable/bidi characters so ordinary CJK or accented names are not labelled | Review 31 N6 | i18n pass |
| Strict schema validation for stored purge previews and intent result values (`_preview_from_dict` still coerces) | Review 30, Review 31 | Privacy hardening |
| Make `_owned_child()` and the deletion that follows descriptor-relative (`dir_fd`, no-follow) before broadening the threat claim | Review 30, Review 31 | Privacy hardening |
| `privacy status` column widths overflow for long control labels | Self-review 2026-09-20 | i18n/CLI polish |
| `src/aptuni/application/privacy.py` is past the 400-line guidance; split inventory, preview and confirm once the contract stops moving | Self-review 2026-09-20 | Privacy hardening |
| An unreadable committed purge intent still wedges canonical writes with no in-product remedy | Review 32 N3 | Privacy hardening |
| A wedged purge action id is not discoverable from any surface; `privacy status` should name the committed intent | Review 32 N6 | Privacy hardening |
| Backup restore preview can still accept a manifest whose ledger-drop simulation is refused only at confirmation; align the claim or move the simulation earlier | Review 37 N17 | Backup/restore hardening |
| Backup verification: pin symlinked `HEAD.json`/`records`/manifest tests, validate every digest read, tolerate Finder `.DS_Store`, and clarify source-folder versus replay-state wording | Review 36 N13/N15; Review 37 N18–N20 | Backup/restore hardening |
| Resolve the sync-root filesystem gate against a resolved home path so a symlinked `HOME` cannot bypass it | Review 37 observation | Vault filesystem hardening |
| Mem0 projection adapter: inject failed add/delete/rebuild operations and emit bounded structured failure evidence with cleanup | Review 51 note | M2 Mem0 adapter |
| Qdrant Client 1.19.1 opens a temporary in-memory SQLite connection without explicit close on Python 3.13; recheck on any pinned upgrade | S10/Review 51 follow-up | M2 Mem0 adapter |
| Mem0 provider status: bound the final old-generation scan and distinguish exact-version incompatibility from missing optional modules | Review 53 notes | M2 Mem0 hardening |
| Hybrid service tests monkeypatch `AptuniService._semantic_search`, bypassing the lock, the freshness gate and `Mem0Projection.search`; move the module-filter, policy-race and non-memory-id cases to factory-level doubles as the CLI test already does | Review 54 N5 | M2 hybrid hardening |
| Obsidian: deduplicate the `SourceConfig` construction shared by `add_folder_source` and `add_obsidian_source` | Review 55 N8 | Source hardening |
| Obsidian: add an `obsidian://` deep link to `_open_url` so vault evidence can be opened in Obsidian | Review 55 N11 | Obsidian follow-up |
| A note or file that vanishes mid-walk raises an unwrapped `FileNotFoundError` from `path.stat()`; pre-existing in `folder.py` and shared by `obsidian.py` | Review 55 N12 | Source hardening |
| Folder/GitHub `_observe`-equivalent reads are not descriptor-relative the way Obsidian's now is; a parent-directory symlink swap remains possible for all three | Review 55 N2 | Source hardening |
| Automatic promotion: direct tests for a promotion racing a module-policy change, and for crash-replay idempotence beyond the same-statement case | Review 56 N8 | M2 promotion |
| Reserve an unknown `record_type` for `SchemaVersionError` so a newer record type fails legibly on an older install instead of as a pydantic validation error | Review 56 N4 | Schema compatibility |
| Corroboration linking so a statement observed in two episodes strengthens one candidate instead of creating two, which would let a repeated host proposal become stable | ADR-0018 rule 2 follow-up | M2 promotion |
| Add a direct mocked-`UrllibGitHubTransport` regression for a 2,000,001-byte Deep response; the integration suite already proves the 2,000,000-byte request bound and durable no-change consequence after `github_response_too_large` | Review 58 W3 | GitHub source hardening |
| Count inline enhanced-markdown `<unknown …/>` blocks as unknown block IDs once the live format is confirmed from `notion://docs/enhanced-markdown-spec` | Review 65 B1 recommendation 4 | Next Notion slice |
| MCP `aptuni_search_context` description: state that item order means relevance, not trust, now that a tainted L4 unit can lead an Evidence-requested response | Review 66 note 1 | Next MCP/adapter slice |
| `mcp.client.streamable_http` can still log `post_writer` tracebacks to stderr; route the transport logger too once its failure modes are mapped to bounded errors | Review 67 N6 | Next Notion slice |
| A stored `client.issuer` mismatch makes the SDK re-register and overwrite the Keychain `client` entry even on the non-interactive path (pre-existing) | Review 67 (c) | Next Notion slice |
| Notion bare-result pass-through: reject text with an exact `<page`/`<properties>` line or the `Here is the result of "fetch"` header but no `<content>` envelope, and require a `<page` line before `<content>`, once the real server's non-enveloped shapes are known | Review 68 notes 1–2 | Next Notion slice |
| Stable gate: bind `candidate.version` to package metadata and require a final (non-pre-release) version for Stable publication | Review 73 note 5 | Stable readiness |
| Stable gate: require a records-per-trial floor or report zero-return trials so 30 trials with one record cannot pass G | Review 73 note 6 | Stable readiness |
| Stable gate: produce B evidence by running the suite/Ruff/mypy, check A–J against an in-repo Beta checklist, add an evidence-input digest to the report, fsync the parent directory | Review 73 notes 9–12 | Stable readiness |
| Top-Down redaction: cover `./secrets/.env`-style relative paths, `/mnt/…`, UNC paths, `password=` pairs and URL-fragment tokens | Review 74 note 6 | Top-Down hardening |
| Top-Down verification: `is_affirmative` is a word-list heuristic ("looks ok? what about X" passes); consider requiring the host to echo the exact summary digest in a dedicated confirmation turn | Review 74 note 8 | Top-Down hardening |
| Public API: an any-term/OR retrieval mode and per-item corroboration counts would remove plugin-side lexicons and per-term query fan-out (see `docs/research/findings/plugin-platform-friction.md`) | Flagship #1 platform feedback | Plugin platform |
| Top-Down: forged demonstration bullets with distinct timestamps still yield a (quarantined) proposal; consider binding demonstrations to a local seal | Review 74 re-review note 2 | Top-Down hardening |
| Top-Down: rewrite bare `—`/`›` in targets and concepts instead of rejecting them | Review 74 re-review note 3 | Top-Down UX |
| `aptuni developer grant apply` raises an unhandled `EOFError` traceback when stdin is closed; print a bounded "confirmation required" error and exit non-zero | Clean-install journey 2026-09-27 | CLI polish |
| Plugin NOTICE: tailor it to the plugin distribution (it references root-only brand and notice paths) | Review 75 note 6 | Plugin packaging |
| Setup: freeze whether the Vault step creates or attaches in the plan digest instead of deciding at render/apply time (both outcomes are safe) | Review 76 note 5 | Setup |
| Attach: add a snapshot test attaching a Vault with an interrupted restore or purge, the case `recover()` would rewrite | Review 76 note 6 | Attach hardening |
| Setup preview: the recommendation block before the plan is long (internal plugin ids, ~10 benefits and ~10 trade-offs); consider a short summary with details on request | Beta new-user journey 2026-09-28 | Onboarding |
| Setup plan: retention and scope ids (`externally_controlled_unknown`, `identity.read`…) and ISO expiry timestamps are shown raw; localize them | Beta new-user journey 2026-09-28 | Onboarding i18n |
| Codex connect text: `codex mcp add` registers the server for all projects (skills are per project); say so | Beta new-user journey 2026-09-28 | Onboarding |
| Top-Down plugin: the grant ID must be exported as `APTUNI_TOP_DOWN_GRANT_ID` before launching the host, documented only in the plugin README; print it after grant apply or let the plugin find its own grant | Beta new-user journey 2026-09-28 | Plugin UX (next plugin version) |
| Top-Down context file headings are English for Chinese learners | Beta new-user journey 2026-09-28 | Plugin i18n |
| Setup memory question offers `automatic`/`temporal` experiences; confirm each is installable in Beta or mark it | Beta new-user journey 2026-09-28 | Onboarding |
| Setup: `--module` does not narrow a plugin grant's modules (disclosed on the consent screen); consider `--plugin-module` | Review 78 N5 | Setup |
| `aptuni connect`: choose the newest grant by a recorded creation time, and after a revoke tell the owner to uninstall the Claude plugin | Review 78 N7 | Host connect |
| APPLY prompts: consider requiring a real TTY for `setup apply` like `developer grant apply` (agent-guide rule is behavioural) | Review 78 N8 | Owner confirmation |
| Setup `--json`: exit 0 with `failure: null` when sources were deferred; tell Agents to read `source_failures` | Review 80 N3 | Setup / Agent guide |
| 0.2.0b3 rejects `sync:src_…` journal entries, so an older build cannot replay or cancel a setup that deferred a source | Review 80 N5 | Compatibility |
| ADR-0027 gaps: `status` counts include removed sources; Obsidian `recent_changes` shows a bare `revoke`; redundant purge-scope clause; `source remove` accepts piped APPLY (reversible, matches `memory forget`) | Review 80 N6 | Source removal |
| English confirmation screens can now print non-ASCII (CJK names) and may fail on a non-UTF-8 stdout | Review 80 N7 | Rendering |

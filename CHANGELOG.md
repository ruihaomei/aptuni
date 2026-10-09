# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project will use
[Semantic Versioning](https://semver.org/) from its first release.

## [Unreleased]

## [0.2.0b10] — 2026-10-09

### Security

- Notes that contain obvious credentials are no longer taken into Aptuni from any source:
  passwords, keys and tokens written as a labelled `name: value` (also in Markdown bold, inline
  code, JSON/YAML/Python quotes, `.env`-style `DB_PASSWORD=` lines and Markdown tables), known
  provider tokens, private keys, JWTs and logins in a URL. A sync lists each withheld item by path or
  id (never its text), and the next sync also retracts such notes taken in earlier. Removing a
  source, re-granting its authority or retracting a Fact no longer copies the secret into new
  records. Context never returns an item that looks like a credential, the identity card drops only
  the affected line, and Agents are not told how many items were withheld. `aptuni doctor` lists any
  that remain in history, and `aptuni privacy purge preview --credential-history` erases that
  withdrawn history without removing the whole source. Not detected: an unlabelled random string, a
  password written in a sentence (`my password is …`), or a lowercase word or passphrase used as a
  password. Your files are never changed.

### Added

- Agents in an explicitly enabled Full session can now list which of your projects,
  documents and studied subjects exist (`aptuni_search_context` `mode="inventory"`) and fetch
  Evidence for the ones they choose (`mode="evidence"`), so "choose two from my history" no
  longer depends on guessing search words. Same grants, exposure and credential guards; no
  storage change (ADR-0032, Proposed).

- Selection research: a grant-scoped candidate inventory (what projects, documents
  and study topics exist) followed by Evidence for chosen candidates fixed unnamed
  "choose two from my history" tasks on fresh real data for both Codex (3/6 → 6/6)
  and Claude Sonnet (0/6 → 3/6). Research seam only; not yet in the product.

- A zero-model follow-up found that every exposable record is filed under the
  `knowledge` module, so selection cannot target projects or experiences.
  Scoping to the candidate class did not help at the current packet size, and
  deeper packets saturate below release quality. b10 stays unreleased; no
  production change.

- Selection retrieval research localized the missing second candidate to the
  Agent's concept choice (R1b) and a rank cutoff (R1c), not to indexing or
  packaging. A one-line concept exception fixed the development cases. On a
  fresh, independently graded six-task real set it was no better (strict 1/6
  each) and was reverted. b10 remains unreleased; no production change remains.

- Real authorized selection research audited candidate support before a fresh
  two-task strong-single comparison. The disposable bounded roster improved
  strict success from 0/2 to 1/2 but did not improve accepted-pair selection,
  and used more model tokens and time. It remains research-only; b10 is
  unreleased. No production retrieval, grant, activation or storage change.

- Locked paired architecture research is complete: strong single A and bounded
  discovery F each pass6/6 ordinary tasks, then1/2 fresh selection tasks. F shows
  no paired quality gain; the research phase closes with b10 unreleased. Independent
  grading preserves all attempts and separates runtime, judge and review overhead.
  No production runtime, activation, permission or policy change follows.
- Local research tools freeze Agent evaluation policies and task hashes, keep raw
  trials outside Git, and report content-free calls, token components and latency.
  Seven post-fix ordinary-prompt trials have now been measured per host; b10 remains
  unreleased because material answer grounding/project discovery failures remain.
- Disposable research controls compare discovery contracts and fixed-evidence
  planner/worker handoffs, preserving failed variants and independent grading.
  These tools do not change installed guidance or production MCP behavior.
- A separately reviewed research tool can test bounded project discovery from
  currently permitted Evidence inside explicit Full. It preserves existing grants,
  read-only canonical state and fixed resource limits; it is not installed in production.

- Agents can pass `concepts` with Profile, Memory and Full activation (and `aptuni context
  --concept`): short terms the task is about, in English and Chinese. Each concept must match
  whole (English words in singular or plural form), so results are precise and unrelated notes that
  share only one generic word are no longer returned. In a local evaluation on one real Vault the
  share of useful top-5 items rose from 74% to 98%, and none of 12 off-topic test queries returned
  anything. Queries without concepts work as before.

### Changed

- Agent guidance now plans personal-context retrieval once, skips generic tasks,
  consolidates relevant concepts into one call and permits only one justified
  alternate-term/language retry. It distinguishes task activation from session-only
  search and reminds Agents that study records do not prove proficiency. Complex
  plans request a larger initial context budget rather than repeatedly searching.
  Activation remains OFF by default; regenerate bundles for this guidance.

- Agents now name only the few specific things a task is about when they look up your context —
  usually one to four, such as "MySQL join" rather than "database" — instead of filling all eight
  slots with broad fields and translations. If a term finds nothing they try once with a broader
  name or the other language, then stop. In a local evaluation on one real Vault this kept
  relevance level with the previous lists of eight and returned nothing for off-topic tasks.
  Regenerate your Claude or Codex bundle to get the new guidance.

## [0.2.0b9] — 2026-10-01

Agent memory auto-save opt-in and more varied Context. Top-Down Learning stays 0.2.1.

### Added

- `aptuni memory review policy --host-proposals on` lets memories proposed by your Agent save at
  once instead of waiting for your confirmation. They stay marked as added automatically, wait in
  `aptuni memory review list` for you to keep or revoke, and never become Profile facts; proposals
  about identity, relationships or behaviour still ask first. Off by default.

### Changed

- Profile, Memory and Full activation now list distinct topics before repeats: a note's Fact, its
  Evidence and nested copies of the same topic no longer fill the budget with one concept, and a
  single notebook contributes at most three items before others get a turn. Nothing is dropped, and
  matches on every keyword still come before partial matches.

### Compatibility

- Turning the option on records a version-2 review policy; 0.2.0b8 and older then refuse to open the
  Vault (restore a backup to downgrade).

## [0.2.0b8] — 2026-10-01

Day 1 dogfooding fixes for Agent activation. Top-Down Learning stays 0.2.1.

### Fixed

- Full, Profile and Memory activation no longer return nothing when an Agent queries with a list of
  keywords and one of them does not appear in your notes: Aptuni now falls back to records that
  match any whole keyword. A single compact keyword (for example “金融危机” or “Python数据分析”) still
  matches only as a whole.
- A refused activation now says which requested modules are not granted and which are.
- Saving a memory from an Agent now explains why it was refused: the grant does not allow memory
  proposals (re-plan the adapter with `--allow-memory-proposals`), or Full is not active for the
  session.

### Changed

- `aptuni_activation_status` also lists the granted modules and whether memory proposals are
  available. Neither contains personal content.
- Regenerated Claude Code and Codex bundles tell the Agent to check the granted modules first, to
  query with a few distinctive keywords, and that saving a memory needs Full for the session.

### Security

- The MCP dependency PyJWT is locked at 2.15.1 (2.14.0 has CVE-2026-101918).

### Compatibility

- No Vault, schema or grant change; 0.2.0b7 and 0.2.0b8 open the same Vaults. Regenerate the adapter
  bundles to get the new skill text.

## [0.2.0b7] — 2026-09-30

General Knowledge Evidence Model (ADR-0029). Top-Down Learning stays 0.2.1.

### Added

- `aptuni knowledge [QUERY]` shows a derived Knowledge State per concept: counts of exposure,
  studied, applied and demonstrated Evidence, their sources, your own claims kept separate, and an
  evidence level that is explicitly not a proficiency score.
- `aptuni source reclassify SOURCE_ID` re-checks each item of a source with the current classifier
  and changes it only after you type `APPLY`; history, rejections and edits are kept.
- GitHub Standard repositories now record per-repository concept usage (applied, imported, declared
  or mentioned; never code text), and `aptuni source authorize SOURCE_ID --grant knowledge.applied`
  lets real, constructed-and-called library use count as applied Evidence.

### Changed

- Source authority is a ceiling, enforced by the Vault: an item carries `studied` or `applied` only
  when its own content shows it. A MarginNote card counts as studied when it organises sub-topics,
  collects several excerpts or carries your annotation; an isolated card stays reference material.
- `aptuni source authorize` re-derives items through this classifier instead of labelling every item.
- `$aptuni-profile` / `/aptuni:profile` lead with at most five cited Knowledge State lines instead of
  many individual `Studied …` facts.

### Compatibility

- Existing Vaults validate unchanged. Both of the following fail closed: 0.2.0b6 and older cannot
  open a Vault that holds a `knowledge.applied` grant, and they refuse to sync a MarginNote or GitHub
  source last synced by 0.2.0b7.

## [0.2.0b6] — 2026-09-30

Fix for the first real `aptuni source authorize` run. Top-Down Learning stays 0.2.1.

### Fixed

- `aptuni source authorize` and source sync no longer fail as a whole when a note title reads as a
  proficiency claim (for example "Mastery learning"): that topic stays reference Evidence and every
  other topic still forms a Profile Fact. Found on User #1's Vault (2 of 26,417 topics).

## [0.2.0b5] — 2026-09-30

Your approved sources now form your Profile. On a Vault with ~27k Evidence records the Profile
had stayed empty because nothing turned source Evidence into Profile facts. Top-Down Learning stays 0.2.1.

### Added

- Authoritative `studied`, `applied` and `demonstrated` Evidence now creates active Profile Facts
  during source sync without per-item approval (ADR-0028). The Facts keep exact Evidence lineage,
  are deterministic on replay, and can be rejected or corrected retrospectively in the CLI or
  Obsidian. `aptuni profile refresh` backfills eligible existing Evidence.

### Changed

- Profile activation can retrieve permitted Evidence as well as Facts, so an approved cold-start
  source is useful before it has produced stable Facts. Plain document exposure remains Evidence
  and never becomes a durable skill or proficiency claim.
- Guided setup records MarginNote study notes as authority for `knowledge.studied`; the plan
  confirmation says so, and a plan confirmed by an earlier version keeps its reference-only meaning.
- `aptuni source authorize SOURCE_ID --grant knowledge.studied` lets an existing MarginNote source
  count as evidence of what you studied after a typed APPLY; its current items are re-read as
  studied (history kept) and form Profile Facts. Owner rejections and edits hold across later
  source changes, and `aptuni profile review accept` is refused for these already-active Facts.
- Source sync output reports how many Profile Facts it wrote.

### Fixed

- An empty GitHub repository (GitHub's `409 Git Repository is empty`) syncs as zero files with a
  `repository_empty` note instead of failing as `github_request_failed`; any other conflict still fails.

## [0.2.0b4] — 2026-09-29

Fixes from the User #1 Beta Day 0 journey, where an agent-led setup with sixteen sources stopped
before any agent access was written. Top-Down Learning stays 0.2.1.

### Added

- `aptuni source remove SOURCE_ID` stops using an approved source: after a typed APPLY its evidence
  is withdrawn so no agent sees it, history is kept, and the same location can be approved again
  (ADR-0027). `aptuni privacy purge` still deletes a source for good.
  Upgrade every installation before removing a source: older builds do not honour a removal and
  can read the source again; running `aptuni source remove` again withdraws what they added.
- `aptuni setup apply` prints progress for every step and every source while it runs.
- `aptuni status --lang` (and `APTUNI_LANG`); `--json` is unchanged.

### Changed

- A source that cannot be read during setup no longer stops it: setup completes, and the result
  lists that source with a plain reason and the exact `aptuni sync` (or `source remove`) command.
- Setup plans stay valid for 24 hours, and a confirmed setup never expires while it resumes.
- A plan that approves GitHub sources with `--github-token-env` says to set that variable in the
  same terminal before APPLY.
- Chinese, Japanese and Korean folder names are shown readably on plans and consent screens;
  look-alike and invisible characters stay escaped and flagged.
- The Agent guide forbids runnable placeholder commands and explains least-scope GitHub tokens.

### Fixed

- A GitHub repository with files larger than Aptuni reads (such as multi-megabyte notebooks) no
  longer fails as a whole: those files are skipped with a note.
- A GitHub error while reading files is reported as `github_sync_failed` with its real reason,
  not as the misleading "the source changed while syncing".

## [0.2.0b3] — 2026-09-29

Bug-fix Beta for returning users before the User #1 Day 0 journey. Top-Down Learning stays 0.2.1.

### Fixed

- After `aptuni attach`, guided setup uses the attached Vault by default instead of planning a new
  `~/Aptuni` and failing after APPLY; a different `--vault` is refused before APPLY.
- Scripted setup lists Notion and MarginNote as later steps with exact commands instead of
  requiring a MarginNote store path, matching the interactive flow and the Agent guide.

## [0.2.0b2] — 2026-09-29

Second Beta, from the first real User #1 reinstall and a disposable brand-new-user install in
English and Chinese. Aptuni can now be set up from inside a Claude Code or Codex chat with one owner
APPLY. Top-Down Learning plugin 0.2.1 finds its own grant.

### Added

- `aptuni guide agent`: a packaged playbook the user's Agent follows in chat. The Agent asks the
  questions and runs the commands; the owner types only `aptuni setup apply ACTION_ID` and APPLY.
- `aptuni attach PATH` reconnects a fresh installation to an existing Vault after a read-only
  verification, without changing anything inside it; guided setup also reuses an existing Vault.
- `setup plan --plugin-manifest` puts a plugin's grant consent into the setup plan, so one APPLY
  covers Vault, sources, agent access and the plugin; `setup cancel` revokes it.
- `aptuni connect claude|codex` prints the exact host commands for the current grant. The Claude
  bundle doubles as a local marketplace for `claude plugin install aptuni@aptuni-local`.
- Repository marketplaces for Claude Code and Codex install Top-Down Learning with two commands.
- An Obsidian setup step; first-run questions in product language ("which parts of you may Aptuni
  learn from") with the exact location asked in the same flow; a welcome screen for bare `aptuni`.

### Changed

- Plugin grant previews and applies show a readable English/Chinese consent screen built from the
  real plan (`--json` is unchanged). It states that memory suggestions are stored in the Vault as
  pending items and that network use is the plugin's declaration.
- `setup apply` and `adapter apply` print the exact Claude Code and Codex connect commands. The setup
  plan shows a short recommendation, localized retention and expiry, and module names in Chinese.
- Agent catalog copy no longer promises automatic context: Aptuni stays OFF until invoked.
- Top-Down Learning 0.2.1 no longer needs `APTUNI_TOP_DOWN_GRANT_ID`; it uses the newest owner
  grant bound to its exact manifest digest and prints its manifest path. Re-plan its grant.

### Fixed

- Choosing a folder in interactive setup no longer ends in an English flag error; Obsidian and
  Notion choices are no longer silently dropped; unsupported sources are not offered.
- Setup steps for GitHub show the repository address instead of internal JSON.

## [0.2.0b1] — 2026-09-27

First Beta. Aptuni becomes a personal context platform for Agent plugins: canonical Profile, Memory
and Full activation (OFF by default), plugin-declared context capabilities under exact owner grants,
and Top-Down Learning as Flagship Plugin #1. Stable remains gated on the owner UX Gate, the
automated Stable readiness gate and a clean-room audit.

### Added

- Top-Down Learning is now Aptuni Flagship Plugin #1 (plugin 0.2.0). It uses task-scoped context
  retrieval, asks at most three material questions and requires an explicit learner verification
  gate before teaching. It maintains a portable `top_down_learning_context.md`
  (`aptuni.top-down-learning.context@1`, ADR-0026) with separate stable and dynamic state, an
  Agent-generated teaching strategy, preference-derived affordances, a just-in-time
  descend/return loop that requires learner output, and a privacy-minimized cloud export that
  continues without Aptuni. It uses eight stateless MCP tools shared by Claude Code and Codex.
  Memory proposals are explicit and quarantined. The previous fixed-catalogue tools are replaced,
  and 0.1.0 grants must be re-planned.

- A commit-bound machine-readable Stable readiness evaluator covers fresh install, correctness,
  data integrity, privacy, Agent/plugin integration, real owner-labelled quality, longitudinal
  stability, documentation and supply chain. Missing owner evidence remains explicitly insufficient
  or owner-required; it is never converted into PASS.

- Agent plugins may declare required and optional Aptuni context capabilities in their existing
  `aptuni.plugin@1` manifest. Owner grants must include required capabilities, may omit optional
  authority, and preserve live module, revocation and privacy checks; legacy manifests retain their
  exact digest and behavior (ADR-0024 amendment).

- Top-Down Learning is now an installable manual Agent plugin with native Claude Code
  `/top-down-learning:top-down-study` and Codex `$top-down-study` skills over one no-egress STDIO
  workflow. It requires active learner output, advances only demonstrated prerequisite progress,
  stores no session transcript, and uses only its exact public-API grant.

- Explicit Beta Agent activation (ADR-0025): Aptuni is OFF for ordinary Claude Code and Codex
  tasks. Native host skills map Profile, Memory and Full to host-independent activation intents;
  task scope is the default, while explicit session Full is inspectable and disableable. OFF blocks
  new retrieval, capture and disclosure but cannot erase context already delivered to a capable host;
  manual-only skills are a UX safeguard rather than an authenticated-human security boundary.

- Public developer API and local plugin platform (ADR-0024): `aptuni.api.v1` provides bounded,
  permission-checked Profile/Memory/Context/Evidence reads, quarantined memory proposals and
  read-only review queues through immutable versioned contracts. `aptuni developer` validates
  manifests, creates revocable exact owner grants and scaffolds public-API-only clients without
  discovering or executing third-party code. The separate
  Top-Down Learning example dogfoods the complete goal-to-adaptive-next-step loop.

- Obsidian desktop owner interface (ADR-0023): a bounded local JSON bridge and three-file plugin
  show Profile, Memory, Evidence, recent changes, pending reviews and promotion state. Review,
  evidence and two-phase Forget actions reuse canonical services; installation neither scans notes,
  grants source access nor enables the plugin, and returned personal content is not cached.

- Content-free longitudinal dogfooding (ADR-0022): `aptuni evaluate` records explicit usefulness/
  noise labels, lifecycle snapshots, provenance, permission and context-efficiency metrics without
  retaining query or context text; purge and `evaluate reset` remove the complete derived dataset.

- Official Notion MCP source (ADR-0021): `aptuni source connect-notion` uses OAuth/PKCE and macOS
  Keychain, while `add-notion` approves exact page/database roots. Sync calls only official
  `notion-get-users(self)` identity and exact-root `fetch` tools,
  retains minimized `notion.locator@1` provenance, and treats truncation or missing roots as partial
  coverage so it cannot silently withdraw prior Evidence.

- Conservative automatic Profile promotion (ADR-0020): an owner-pinned Memory with exact
  owner-declared CLI lineage, current permissions and no unresolved contradiction becomes one
  lineage-linked Profile Fact atomically. `aptuni profile refresh` handles older pins and
  `aptuni profile review list|accept|reject` provides retrospective owner review; host proposals
  and semantic guessing never cross this boundary.

- Preview-only local Mem0 2.0.20 projection commands: content-free status, exact fresh-generation
  rebuild from accepted canonical memories, and whole-store deletion. Inference and raw-conversation
  ingestion are disabled; Mem0/Ollama remain an optional extra.
- Obsidian vault source: `aptuni source add-obsidian` plus the ordinary sync pipeline. Only a
  directory holding `.obsidian/` is a vault; `.obsidian/`, `.trash/` and every attachment are
  excluded before any read. Each note contributes bounded topology (note name, folder, wikilink
  targets, tags, aliases, frontmatter property *names*) in `obsidian.locator@1`, and the Evidence
  excerpt is taken after the frontmatter block is removed, so property values never reach the
  locator, the excerpt or the search index (ADR-0017).

### Changed

- Claude Code adapter bundles no longer inject an identity card at SessionStart. Generated Claude
  and Codex bundles run MCP in activation-required mode, and live grant revocation stops subsequent
  reads in an already-running session.

- Context with Evidence requested keeps retrieval rank across Profile/Memory (L3) and Evidence (L4),
  so a better-matching Evidence unit is no longer placed after, or budget-truncated in favour of, a
  weaker Profile/Memory match. `layers` is reported in canonical L0–L4 order (ADR-0005 amendment).
- `aptuni evaluate trial --evidence` measures the explicit Evidence layer; evaluation state moves to
  schema v3 and `evaluate report` separates Profile/Memory-only and with-Evidence trials
  (ADR-0022 amendment). Existing state migrates automatically.
- Official Notion MCP results without completeness metadata are accepted with `partial` coverage
  and a `notion_completeness_unverified` note instead of being recorded as complete; the page body
  is taken from exactly one enhanced-markdown `<content>` envelope (ADR-0021 amendment).
- `aptuni evaluate discard TRIAL…` removes exact test or mislabelled trials (never one that recorded
  an exposure violation); `evaluate score --rest-noise` labels every unlisted record noise; and
  `evaluate report` lists unscored trials, prints per-mode results and shows first-versus-latest
  usefulness for repeated queries (ADR-0022 amendment).
- `aptuni source disconnect-notion` now fails with `notion_credentials_delete_failed` when Keychain
  refuses the delete, instead of reporting the credential as removed. A Notion page that quotes the
  `<content>` markers in its own text no longer stops the sync.
- The Notion source no longer demands a new browser authorization once its access token expires:
  Aptuni persists the token expiry in its Keychain item and refreshes silently with the stored
  refresh token. OAuth failures print the bounded Aptuni message instead of an SDK traceback.
- **Automatic promotion (ADR-0018).** An observation you make yourself through the CLI now becomes
  an active memory immediately instead of waiting in a review queue. It is marked
  `auto_promoted_pending_review` and reviewed retrospectively with
  `aptuni memory review list|accept|edit|reject|pin`. Host proposals, sensitive modules
  (`identity`, `relationships`, `behavior`) and anything contradicting a record still standing keep
  the typed confirmation. Reminders default to ten pending or fifteen days and are never blocking;
  `aptuni memory review policy --auto-promotion off` restores the old behaviour. `ReviewEvent`
  gains schema version 2, so a Vault written after this change cannot be read by 0.1.0.
- `aptuni memory list` no longer shows a memory that a correction has replaced.
- `aptuni evidence` and `aptuni source add-folder` now render source paths as bounded, escaped,
  delimited data rather than raw terminal text, so a crafted filename cannot forge an output row.
  The `--json` output of both commands is unchanged.
- Opt-in `aptuni search --hybrid` preview with deterministic rank-only fusion across SQLite/FTS and
  the fresh local Mem0 accepted-memory projection; default search and Context API remain lexical.

## [0.1.0] — 2026-09-21

First public pre-alpha release of the Milestone 1 personal context core.

### Added

- Profile Vault: canonical open-format records with temporal facts, corrections, retractions,
  full history, crash-safe writes, recovery, and `aptuni doctor`.
- Module permissions with independent `ingest` and `expose` switches.
- Folder source with incremental snapshots, candidate deltas, provenance and a review queue.
- GitHub source (Standard mode): bounded tree traversal, verified blob identity, exact-origin
  network policy, rate-limit and crash-safe replay.
- Bilingual (English/Chinese) SQLite FTS5 search projection, rebuildable at any time, with a ranked
  any-term fallback for task-shaped queries.
- Bounded Context API with L0–L4 progressive disclosure and response budgets.
- `aptuni-mcp`: read-only, permission-checked MCP server over STDIO with no network sockets.
- Claude Code and Codex adapter bundles with an informed, terminal-confirmed egress grant.
- Plugin catalog, Recipes (Starter Lite, Researcher), and the read-only `aptuni advise` Plugin
  Advisor in English and Simplified Chinese.
- Direct read-only MarginNote 4 source with native note/notebook identity and bounded concept
  evidence.
- Quarantined interaction-memory proposals with explicit accept, reject, and forget lifecycle.
- Owner-readable Profile export plus privacy inventory and digest-bound purge receipts.
- Guided setup with exact effect previews, resumable application, and grant-aware cancellation.
- Verified owner backup and restore that carries deletion history across machines.
- Versioned production retrieval evaluations and reproducible wheel/sdist supply-chain evidence.
- Repository-local source-provider, evaluation, license-audit, and release-readiness skills.

### Security

- Deletion-ledger torn-tail repair before append; unsafe-state failures never print tracebacks or
  content.
- Module-scoped host grants, network-denied MCP STDIO, conservative host-confinement reporting, and
  tracked-secret checks in the release gate.

[Unreleased]: https://github.com/ruihaomei/aptuni/compare/v0.2.0b7...HEAD
[0.2.0b7]: https://github.com/ruihaomei/aptuni/releases/tag/v0.2.0b7
[0.2.0b6]: https://github.com/ruihaomei/aptuni/releases/tag/v0.2.0b6
[0.2.0b5]: https://github.com/ruihaomei/aptuni/releases/tag/v0.2.0b5
[0.2.0b4]: https://github.com/ruihaomei/aptuni/releases/tag/v0.2.0b4
[0.2.0b3]: https://github.com/ruihaomei/aptuni/releases/tag/v0.2.0b3
[0.2.0b2]: https://github.com/ruihaomei/aptuni/releases/tag/v0.2.0b2
[0.2.0b1]: https://github.com/ruihaomei/aptuni/releases/tag/v0.2.0b1
[0.1.0]: https://github.com/ruihaomei/aptuni/releases/tag/v0.1.0

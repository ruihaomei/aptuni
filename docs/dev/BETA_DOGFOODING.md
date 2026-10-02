# Beta User #1 dogfooding (Aptuni 0.2.0b1)

**Window:** starts at the first real host first-run journey after publication (Day 0) and lasts at
least 14 calendar days. The final seven days must contain no unresolved P0/P1 defect.
**Participant:** the maintainer (User #1), on a fresh install of the published Beta.

## What is being exercised

1. Aptuni Core: init, sources, review/correction, backup, privacy controls.
2. Claude Code and Codex activation UX: OFF by default; Profile, Memory and Full; task vs. session
   scope; disable.
3. Top-Down Learning, local mode: `/top-down-learning:top-down-study` and `$top-down-study`.
4. Top-Down Learning, portable/cloud mode: export, continue in a cloud Agent, and resume a refreshed
   checkpoint.
5. The plugin grant experience: inspect, plan, `APPLY`, withhold optional capture, revoke.
6. Learning-context quality: foundation accuracy, questions asked, path minimality, usefulness of
   the teaching strategy.

## Evidence rules

- Only the owner's real queries and judgments count. Agents never invent labels or treat synthetic
  fixtures as owner evidence.
- Retrieval quality uses real trials: `aptuni evaluate trial [--evidence]`, then
  `aptuni evaluate score TRIAL_ID --useful … --rest-noise`, with `aptuni evaluate capture`
  periodically. The Stable threshold needs at least 30 scored real trials.
- Do not tune retrieval (KI-018) or learning behavior from synthetic data alone. Change them only
  when real owner-labelled evidence shows a persistent pattern.
- Learning contexts stay in the owner's workspace. Only content-free observations are recorded
  here or in the Stable evidence document.

## Defect intake

Each real Beta defect gets a severity (P0 data loss, privacy or security; P1 blocks a core journey;
P2 degraded; P3 polish) and a regression test written before the fix. The release evidence is
preserved: `docs/dev/releases/0.2.0b1.md` is never rewritten, and fixes ship in a new Beta
(`0.2.0b2`, …) under the same release policy.

| Date | Area | Severity | Content-free symptom | Test / fix commit | Status |
|---|---|---|---|---|---|
| 2026-09-27 | Install / reinstall | P2 | A fresh install could not attach an existing Vault; `init` and `setup apply` refused it and no doc covered reinstall, so the config pointer had to be written by hand. | `tests/integration/test_vault_attach.py`; `aptuni attach PATH` (read-only verify) and setup adoption | Fixed in 0.2.0b2 |
| 2026-09-27 | Plugin grant consent | P3 | `developer grant plan` printed raw JSON with an escaped preview, unlike the readable adapter consent. | `tests/integration/test_grant_consent.py`; bilingual consent screen, `--json` unchanged | Fixed in 0.2.0b2 |
| 2026-09-28 | First-run onboarding | P1 | Interactive setup offered sources as connector ids (incl. unsupported ones); choosing a folder ended in an English flag error after all questions; choosing Obsidian/Notion was acknowledged in the recommendation but never connected or explained. | `tests/integration/test_onboarding.py`; product-language source menu, in-flow folder/Obsidian/GitHub location, `source_obsidian` step, later-connect commands, localized errors | Fixed in 0.2.0b2 |
| 2026-09-28 | First-run onboarding | P3 | Bare `aptuni` printed a usage error, `No Vault configured` pointed only to `init`, and the README's first step assumed a cloned repository. | `test_onboarding.py`, `test_cli.py`; welcome screen, setup/attach hint, README first step | Fixed in 0.2.0b2 |
| 2026-09-28 | Agent connection | P1 | After setup/adapter apply the user was told to "point the host at the bundle" with no command; a new user could not connect Claude Code or Codex. | `tests/integration/test_host_connect.py`; exact `claude --plugin-dir` and Codex skill copy + `codex mcp add` lines derived from the bundle, bilingual | Fixed in 0.2.0b2 |
| 2026-09-28 | Setup recommendation copy | P2 | Catalog copy promised context "without you asking" and an identity card "at session start", contradicting Beta OFF-by-default. | `test_host_connect.py::test_agent_catalog_copy_does_not_promise_automatic_context` | Fixed in 0.2.0b2 |
| 2026-09-29 | Returning-user setup | P1 | After attaching a Vault at a custom path, setup planned a new `~/Aptuni` and failed with `setup_vault_conflict` after APPLY; scripted MarginNote required a store path the Agent guide does not ask for. | `test_vault_attach.py`, `test_onboarding.py` | Fixed in 0.2.0b3 |
| 2026-09-29 | Setup apply / source sync | P1 | One failing source (missing GitHub credential, then a retryable `sync_retry`) stops the whole setup at the sync step, so agent grants, bundles and the plugin grant are never written; the only recovery is re-running APPLY. | `test_setup_resilience.py`, `test_github_oversized.py`; failed sources reported with reason and retry, oversized GitHub files skipped, real GitHub error codes | Fixed in 0.2.0b4 |
| 2026-09-29 | Source management | P1 | Once approved, a source cannot be removed or paused from the CLI (`aptuni source` has no remove/disable), so "connect only public repos" was impossible after private repos failed. | `test_source_removal.py`; `aptuni source remove` (ADR-0027) | Fixed in 0.2.0b4 |
| 2026-09-29 | Setup apply progress | P2 | A resumed apply that syncs many GitHub repositories runs for minutes with no progress output, and other `aptuni` commands block meanwhile. | `test_setup_resilience.py::test_apply_prints_progress_for_each_step_and_each_source` | Fixed in 0.2.0b4 |
| 2026-09-29 | Setup plan / credentials | P2 | A plan with private GitHub repos and `--github-token-env` never says the variable must be set before APPLY; the ~30-minute plan expiry is too short to create a token, and a plan can expire mid-journey. | `test_setup_credentials.py`; token-env notice, 24 h plans, confirmed setups never expire | Fixed in 0.2.0b4 |
| 2026-09-29 | Agent guide copy | P2 | The Agent put a placeholder token in a runnable shell block and the user ran it; the guide should forbid runnable placeholders and tell the Agent how to handle private-repo tokens. | `test_agent_guide_day0.py` | Fixed in 0.2.0b4 |
| 2026-09-29 | Plan rendering (zh-CN) | P3 | Chinese folder paths are shown as `\uXXXX` escapes with `[non-ascii/confusable-escaped]`, unreadable for Chinese users. | `tests/unit/test_render_cjk.py`; CJK readable, confusables escaped | Fixed in 0.2.0b4 |
| 2026-09-29 | CLI consistency | P3 | `aptuni status` rejects `--lang` while other commands accept it. | `test_status_lang.py` | Fixed in 0.2.0b4 |
| 2026-09-29 | GitHub source sync | P1 | A repository with multi-megabyte notebooks failed its whole sync (`github_response_too_large`), although the tree already reports each file's size. | `test_github_oversized.py` | Fixed in 0.2.0b4 |
| 2026-09-29 | Error reporting | P2 | A GitHub error while reading files surfaced as `sync_retry` ("the source changed while syncing"), hiding the real cause; diagnosing it needed a manual `aptuni sync`. | `test_github_oversized.py::test_a_github_failure_while_reading_files_keeps_its_own_code` | Fixed in 0.2.0b4 |
| 2026-09-29 | Agent guide / shells | P3 | A command run through the chat's own shell (`!`) did not see a variable exported in the owner's terminal tab. | `test_agent_guide_day0.py` (same-terminal rule in the guide) | Fixed in 0.2.0b4 |
| 2026-09-29 | GitHub source sync | P2 | An empty repository (GitHub answers `409 Git Repository is empty`) is reported as a failed source (`github_request_failed`) instead of syncing as zero files; three of User #1's repos showed as failures on 0.2.0b4. | `tests/integration/test_github_empty_repository.py` | Fixed in 0.2.0b5 |
| 2026-09-30 | Profile / `source authorize` | P1 | The first real upgrade of a 26,417-topic MarginNote source was refused as a whole: 2 titles rendered a statement the no-proficiency invariant rejects. Nothing was written. | `tests/integration/test_source_authority.py`; `2cc818d` | Fixed in 0.2.0b6 |
| 2026-09-30 | Profile / knowledge model | P2 | After `source authorize`, every MarginNote card counted as studied (26,415 near-identical Profile facts), GitHub could never show applied use, and Profile activation listed individual facts instead of what the Evidence says per concept. | ADR-0029; `tests/integration/test_knowledge_model.py`, `test_knowledge_state.py`; `fd8d0b6` + remediation; migration `aptuni source reclassify` | Fixed in 0.2.0b7 |
| 2026-10-01 | Full activation / retrieval | P1 | A real Full task returned no context: Agent keyword-list queries had no task language, so one keyword absent from the Vault emptied the whole result (the Vault and server were correct). | ADR-0004 2026-10-01 amendment; `test_lexical.py`, `test_retrieval.py::test_keyword_lists_return_records_matching_any_whole_keyword` | Fixed locally; awaiting Beta |
| 2026-10-01 | Full activation / module grants | P1 | A multi-module activation failed with a bare `mcp_module_denied`, naming neither the denied nor the granted modules; the Agent probed subsets by trial. | ADR-0025 2026-10-01 amendment; `test_activation_guidance.py` | Fixed locally; awaiting Beta |
| 2026-10-01 | Memory proposal | P1 | Saving after a task-scoped Full failed with a bare `aptuni_activation_required`; the grant also lacked `memory.propose`, so session Full would have failed next. | ADR-0025 2026-10-01 amendment; `test_activation_guidance.py` | Fixed locally; awaiting Beta |
| 2026-10-01 | Full activation / result diversity | P1 (maintainer: better method → P1) | Full spent its budget on one or two concepts: a topic appeared as Evidence, its derived Fact and nested path repeats. | ADR-0005 2026-10-01 amendment; `test_diversify.py`, `test_retrieval.py::test_context_lists_distinct_concepts_before_repeats` | Fixed locally; awaiting 0.2.0b9 |
| 2026-10-01 | Evidence duplication | P3 | Two Evidence items with identical text and location but different ids were both returned. | Same concept key → the repeat is demoted after distinct concepts (ADR-0005 2026-10-01) | Fixed locally; awaiting 0.2.0b9 |
| 2026-10-01 | CJK fallback precision | P3 | Under the task-language fallback a cross-word 2–3-character fragment matched an unrelated item. | jieba query segmentation tried and rejected (`docs/research/findings/retrieval-experiments.md`) | Open — KI-018 |
| 2026-10-02 | Retrieval / KI-018 | P1 (maintainer brief) | Plain multi-keyword queries leaked records sharing one generic or homonymous word into Full/Profile context. | ADR-0030; `tests/integration/test_concept_queries.py` | Fixed locally for hosts that pass `concepts`; plain queries unchanged; awaiting release decision |
| 2026-10-02 | Source ingest privacy | P1 (proposed) | A folder-source note containing account credentials (email, password, account login) was ingested as Evidence and is exposable to Agents through Full; host proposals already reject such patterns, source ingest does not. | ADR-0031; `tests/unit/policy/test_secrets.py`, `tests/integration/test_credential_containment.py` | Contained 2026-10-02 (file renamed to `*secret*`, source synced; record not exposable); product fix local, awaiting release; owner: rotate credentials, decide on history erasure |

## Gates kept open in parallel

- **UX Gate:** open until the owner writes exactly `Aptuni User Experience Gate: PASS`.
- **Automated Stable readiness gate:** run `python3.13 tools/stable_gate.py --evidence … --output
  artifacts/stable-readiness.json` at each checkpoint. Absent evidence stays FAIL, INSUFFICIENT or
  OWNER ACTION.
- **Stable publication:** needs UX Gate PASS, Automated Stable Gate PASS and a clean-room Stable
  audit PASS, and then the owner must be asked again.

## Observations inbox (any session; triaged by the next development session)

Append one content-free line per meaningful observation: date · host (Claude Code/Codex) · area ·
proposed severity (P0–P3 or note) · what happened in product terms (no personal content, queries,
file names or Vault text) · whether the owner was interrupted. Do not commit from non-development
sessions; a development session triages lines into the tables below and clears them.

- 2026-10-02 · Claude Code/Codex · context orchestration · P1 · retrieval guidance omitted a relevance decision and confused task permission with session search; corrected locally, fresh product validation pending · interrupted: yes (activation policy decision)

## Daily log (content-free)

| Day | Date | Journeys exercised | Trials scored | Defects opened / closed | Notes |
|---|---|---|---|---|---|
| pre-Day 0 | 2026-09-27/28 | User #1 reinstall/attach; disposable brand-new-user install (en, zh-CN) through setup, connect, MCP activation, plugin grant, Top-Down prepare | 0 | 6 opened / 6 fixed locally | Day 0 not yet: no real host first-run journey has succeeded |
| pre-Day 0 | 2026-09-29 | Agent-led setup (guide, one APPLY with plugin grant, connect) in a disposable home | 0 | 0 opened; Reviews 78 BLOCK → 79 approve | Day 0 starts in a fresh Agent session on public 0.2.0b2 |
| Day 0 | 2026-09-29 | Setup APPLY completed on public 0.2.0b4 (12 sources synced, 3 empty repos reported, grants + plugin grant written, doctor and smoke OK) | 0 | 10 fixed in 0.2.0b4; 1 opened | Host connection and first real journey next |
| Day 1 | 2026-09-30 | Owner backed up, then ran `source authorize` on the MarginNote source: refused on 0.2.0b5 (Vault unchanged), applied on 0.2.0b6 — 26,415 Profile facts, 2 topics kept as Evidence, commit 38, doctor healthy; Profile context query answered | 0 | 1 opened and fixed (0.2.0b6) | First real task with the Profile skill; reject/edit what is wrong |
| Day 1 (cont.) | 2026-09-30 | Knowledge model upgrade (ADR-0029) rehearsed on a deleted scratch copy of the real Vault: `doctor` healthy under the ceiling invariant; `source reclassify` would downgrade 3,737 isolated cards and keep 22,678 studied facts; resolution fixed for image placeholders, role headings and Latin/CJK titles | 0 | 1 opened / fixed locally | Owner runs `source reclassify` themselves after a backup |
| Day 1 (b7) | 2026-09-30 | On public 0.2.0b7: owner backup; `source reclassify` applied (3,737 cards to exposure, 22,678 studied facts kept); all 14 sources synced (3 empty repos); agent-led, owner-confirmed-in-chat `knowledge.applied` grants on 10 repositories → 51 Applied facts; `doctor` healthy (commit 59); `aptuni knowledge` shows cross-source levels (e.g. studied + applied → practiced) | 0 | 0 opened | Frictions for agent-led setup: `uv tool upgrade` keeps exact-pinned installs; `sync` needs one id per source; first b7 GitHub sync took ~10 min for 13 repos; private repos need `APTUNI_GITHUB_TOKEN` (the agent passed `gh auth token` per process); the applied grant is a separate step per repository |

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
| 2026-09-29 | Setup apply / source sync | P1 | One failing source (missing GitHub credential, then a retryable `sync_retry`) stops the whole setup at the sync step, so agent grants, bundles and the plugin grant are never written; the only recovery is re-running APPLY. | — | Open (Day 0) |
| 2026-09-29 | Source management | P1 | Once approved, a source cannot be removed or paused from the CLI (`aptuni source` has no remove/disable), so "connect only public repos" was impossible after private repos failed. | — | Open (Day 0) |
| 2026-09-29 | Setup apply progress | P2 | A resumed apply that syncs many GitHub repositories runs for minutes with no progress output, and other `aptuni` commands block meanwhile. | — | Open (Day 0) |
| 2026-09-29 | Setup plan / credentials | P2 | A plan with private GitHub repos and `--github-token-env` never says the variable must be set before APPLY; the ~30-minute plan expiry is too short to create a token, and a plan can expire mid-journey. | — | Open (Day 0) |
| 2026-09-29 | Agent guide copy | P2 | The Agent put a placeholder token in a runnable shell block and the user ran it; the guide should forbid runnable placeholders and tell the Agent how to handle private-repo tokens. | — | Open (Day 0) |
| 2026-09-29 | Plan rendering (zh-CN) | P3 | Chinese folder paths are shown as `\uXXXX` escapes with `[non-ascii/confusable-escaped]`, unreadable for Chinese users. | — | Open (Day 0) |
| 2026-09-29 | CLI consistency | P3 | `aptuni status` rejects `--lang` while other commands accept it. | — | Open (Day 0) |

## Gates kept open in parallel

- **UX Gate:** open until the owner writes exactly `Aptuni User Experience Gate: PASS`.
- **Automated Stable readiness gate:** run `python3.13 tools/stable_gate.py --evidence … --output
  artifacts/stable-readiness.json` at each checkpoint. Absent evidence stays FAIL, INSUFFICIENT or
  OWNER ACTION.
- **Stable publication:** needs UX Gate PASS, Automated Stable Gate PASS and a clean-room Stable
  audit PASS, and then the owner must be asked again.

## Daily log (content-free)

| Day | Date | Journeys exercised | Trials scored | Defects opened / closed | Notes |
|---|---|---|---|---|---|
| pre-Day 0 | 2026-09-27/28 | User #1 reinstall/attach; disposable brand-new-user install (en, zh-CN) through setup, connect, MCP activation, plugin grant, Top-Down prepare | 0 | 6 opened / 6 fixed locally | Day 0 not yet: no real host first-run journey has succeeded |
| pre-Day 0 | 2026-09-29 | Agent-led setup (guide, one APPLY with plugin grant, connect) in a disposable home | 0 | 0 opened; Reviews 78 BLOCK → 79 approve | Day 0 starts in a fresh Agent session on public 0.2.0b2 |

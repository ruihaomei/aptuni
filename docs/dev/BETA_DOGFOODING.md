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
| 2026-09-27 | Install / reinstall | P2 | A fresh install could not attach an existing Vault; `init` and `setup apply` refused it and no doc covered reinstall, so the config pointer had to be written by hand. | `tests/integration/test_vault_attach.py`; `aptuni attach PATH` (read-only verify) and setup adoption | Fixed (pending 0.2.0b2) |
| 2026-09-27 | Plugin grant consent | P3 | `developer grant plan` printed raw JSON with an escaped preview, unlike the readable adapter consent. | `tests/integration/test_grant_consent.py`; bilingual consent screen, `--json` unchanged | Fixed (pending 0.2.0b2) |

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

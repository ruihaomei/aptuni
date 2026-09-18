# Execution and Test Review Remediation

- **Date:** 2026-09-18
- **Responds to:** `03-execution-test-review.md`
- **Status:** planning changes complete; focused re-review pending

| Finding | Remediation |
|---|---|
| B1 S04 egress | SPIKES/Phase 0 isolate the server process with sockets denied, define expected STDIO disclosure, fail undeclared server/dependency destinations, and record host/vendor boundary separately with synthetic data. |
| B2 S01 concurrency | S01/Phase 0 add multiprocess append/supersede, stale writer, lock crash/recovery, reader during commit, directory durability, lost-update detection, and OS/filesystem assumptions. |
| B3 S05 ordering | S05A validates the common envelope before v1 freeze; S05B gates each provider. Graph/roadmap/plan use the same order. |
| B4 Advisor/install | M1.4 and `plans/02-onboarding-advisor.md` own a bilingual scripted 15-step flow with final confirmation, cancellation/no-side-effect, crash resume/rollback, doctor/smoke, and Vault output. |
| H1 build/install | Foundation Slice 1 builds sdist/wheel, non-editable clean installs, package-data/entry-point smoke, exact CI parity, compatibility matrix, and wheelhouse+socket-denied offline definition. |
| H2 migration/backup | Foundation Slice 3 adds transaction markers, step faulting, idempotent resume, unknown-newer refusal, corrupted-generation fallback, restore verification before rotation, and pre-purge restore tests. |
| H3 evaluation | `EVALUATION_PLAN.md` defines fixtures, precommitted thresholds, automated gates, dogfood scorecard, manifests, and failure policy. |
| H4 bilingual/hosts | `COMPATIBILITY.md` defines Python/OS/SQLite/host/locale matrix, four host×locale journeys, CJK paths/normalization, fallback, snapshots, and upgrade behavior. |
| H5 relay | Added tested `tools/check_relay.py`; Gate 0 schedules it and cold-host drills. STATE/HANDOFF now record current blockers and validations. |
| H6 policy done | Foundation narrows M1.1 to contract/mandatory port; every later slice must enumerate entry points and prove deny/epoch/final recheck. |
| M1 plan gate | Roadmap forbids any slice without an accepted TDD plan and exact exit evidence. |
| M2 S03 thresholds | Phase 0 freezes/checksums corpus, judgments, metric code, numeric thresholds, and holdout before runs; runner fails closed. |
| M3 binary criteria | Foundation names required properties/mutation exception record and executable docs; roadmap requires binary checks/evidence. |
| M4 skills/artifacts | M1.5 owns four post-contract skills, CITATION, CODEOWNERS, and third-party notices. |
| M5 placeholder | Foundation uses `personal-context-core` / `personal_context_core` / `personal-context`. |

Cold Codex/Claude Code drills remain execution evidence, not a paper closure. Re-review must keep the
gate blocked if any acceptance rule is still non-binary or contradictory.

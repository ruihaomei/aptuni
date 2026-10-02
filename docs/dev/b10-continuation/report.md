# b10 continuation report — 2026-10-02

**b10 was not released.** Managed credential cleanup and the engineering/guidance
checkpoint are verified; fresh ordinary-prompt product validation remains blocked.
No original task was rerun or discarded. No private prompt, source excerpt or
credential value is included in committed records.

| Requested outcome | Status / evidence |
|---|---|
| 1. Credential cleanup | Owner-confirmed targeted action; receipt `complete_managed_external_action_needed`. Two records deleted, zero sources purged. |
| 2. Historical credentials | Both incident ids absent; canonical inventory zero. Old backup still has one flagged record. Source/host/provider/export copies and rotation remain outside managed cleanup. |
| 3. Vault health | Doctor passes at commit 62, 110,194 records; all 125 unrelated exposed Evidence records in affected source retained. |
| 4. Adapters/grants | Active Claude/Codex grants restored with original six modules/scopes; Claude retains its prior memory-proposal scope. Claude plugin reinstalled; Codex MCP uses guarded checkout and four user skills installed. Real STDIO confirms OFF and new guidance. Superseded Claude and developer-plugin grants remain revoked. Public local CLI remains b9. |
| 5. Original ten runs | One pass with note, nine failures under full-product criteria. See original-e2e-grading.md. h01/h04 broad fragmented planning and h10 missing invocation remain failures. |
| 6. Root causes | Unconditional skill retrieval; task/session search confusion; guessed course inventories and broad parent fields; too-small initial context encouraging repeated calls; unsupported mastery/progress claims; two usage-exhausted final answers. |
| 7. Guidance changes | Decide relevance, plan concepts/modules once, one consolidated call, one justified replacement-term/language retry; use named programme/role/project; no syllabus or scope escalation; complex tasks request 4000 units initially; ground claims in evidence. |
| 8. Fresh mini-holdout | Seven unseen tasks locked before results, SHA-256 recorded in research findings. Not executed: activation-policy decision pending; Claude capacity exhausted; Codex CLI canary rejected configured model. No fresh pass claimed. |
| 9. Call frequency | Original runs: retrieval on 9/10 tasks; 19 attempts, 15 successful, four refused. Five single-call, four multi-call, one no-call task. |
| 10. Retry frequency | Ten additional attempts beyond first calls; four multi-call tasks. No clean justified alternate-language-only retry; repeated refused searches and broad expansions counted. |
| 11. Concept count | First-call median four/max five, >4 on 2/9. All-call median four/max five, >4 on 6/19. Fresh behavior unmeasured. |
| 12. Specificity | Good named methods in technical tasks; broad/speculative planning terms in h01/h04/h09 and generic follow-ups in h02 fail. |
| 13. Language behavior | Chinese/mixed requests can retrieve English records naturally; useful named bilingual variants in h05. Broad bilingual lists still fail; h10 has no language evidence before quota failure. |
| 14. KI-018 | Substantially better concept-mode retrieval evidence preserved, but actual Agent product closure unproven; stays open. |
| 15. Remaining issues | KI-024 memory-id purge wedge separately tracked; Review 96 detector residuals; existing deferred issues; developer grant revoked; external credential copies/rotation unverified. |
| 16. Commits | Prior boundary record `9520605`; current implementation/review checkpoint `b8ba178`; subsequent record checkpoint appears in git log. Local only, no push/tag. |
| 17. Reviews | Review 96 credential guard and Review 97 orchestration guidance APPROVE WITH NON-BLOCKING NOTES. Review 97 corrected a privacy wording defect; host parity follow-up applied. Neither establishes a fresh product pass. |
| 18. Release | Not released; version/tag/publication unchanged. |
| 19. Clean backup | New post-purge backup created and independently verified at commit 62: 110,194 records, two ledger digests, zero flagged credential records/incident ids. |
| 20. Old backup deletion | New backup retains every unrelated old canonical record; only the incident id is missing. Safe to retire for current-state recovery, but deletion also removes the pre-b9 downgrade checkpoint. Old backup retained; no irreversible deletion authorized/performed. |
| 21. Owner-only decisions/actions | Decide whether normal prompts operate inside explicitly enabled Full session (preserve ADR-0025) or automatically activate per task (new privacy policy). Credential rotation/external-copy remediation remains owner-only and unverified. Old backup deletion needs explicit authorization if desired. |

Engineering validation on the final production/test changes: **1263 tests passed,
three optional skips, 62 subtests**; Ruff, strict mypy (122 files), relay, 56 developer
checks, supply-chain secrets and frozen evaluation pass. Scope is guidance and one
activation-contract regression; lexical matching/ranking, schemas, grants and
activation semantics remain unchanged.

Exact next step: resolve the pending privacy-policy interpretation, obtain an
available real host, run the locked unseen tasks with ordinary prompts and no manual
concept repair or forced task retrieval. Grade full answers and invocation behavior.
If a generalizable defect is fixed, lock a fresh set rather than reusing those tasks
as proof. Release only after the complete product/engineering gate passes.

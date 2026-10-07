# Known Issues and Open Risks

| ID | Severity | Issue | Disposition |
|---|---|---|---|
| KI-009 | Deferred | Graphiti projection loses canonical semantics and needs a ledger. | S11 before Milestone 3 adapter. |
| KI-016 | High | S01 findings F1–F3: whole-Vault revalidation per commit, integrity mismatch blocks all reads, purge needs startup `recover()`. | Mandatory M1.1 Slice 3 requirements (incremental validation + compaction; out-of-band edits → quarantine; recover before serving); fold into ADR-0001/0010 on acceptance. |
| KI-017 | High | S02 F1: pip RECORD does not hash `.pyc`; a forged bytecode file passes closure verification and executes. | M1.1 sets `sys.pycache_prefix` to a core-owned directory before importing plugins (proven in S02) and adds F2/F3 (manifest placement; lockfile artifact hashes). |
| KI-018 | High | S03 used a templated synthetic corpus; broad two-character queries admitted top-5 distractors even though aggregate gates passed. | M1 adds dogfood judgments and per-result context-noise tests; retain size telemetry and score/reranking seam before user-facing quality claims. 2026-09-25 real data point: on a 10-record Vault, an Evidence-answerable query in default L3-only Context returned 2/2 noise via the ADR-0004 any-term fallback, whose 25% floor is relative to the best *remaining* hit and therefore admits single-term matches when no strong L3 candidate exists. Deliberately not retuned on one trial; collect more real `profile_memory` trials (now separated by `evaluate report`) before changing the frozen lexical contract. 2026-10-01 (ADR-0004 amendment): multi-keyword queries now fall back to whole keywords, so a two-word phrase can return a record matching one word (e.g. “machine translation” → a machine-learning note); judge with real trials before adding a phrase rule. 2026-10-01 experiment (`docs/research/findings/retrieval-experiments.md`): 4 of 6 negative queries still return items via generic single words; neither jieba nor a small dense model with a score floor separated them. 2026-10-02 (ADR-0030): solved for callers that pass host `concepts` (0% leakage on 12 should-be-empty queries); plain queries keep the b9 behaviour (67% leakage); semantic gates reach 25% but were not adopted. |
| KI-021 | Medium | The opt-in hybrid semantic lane has no relevance floor: Mem0 is queried with `threshold=0.0`, so a query with no lexical match still returns exposable accepted memories up to the requested limit. The lexical path deliberately has the opposite guarantee (relative-score floor). | Documented in ADR-0004's 2026-09-22 amendment and the READMEs. Opt-in, owner-CLI only, and every row already passed the final exposure check, so this is an honesty/quality gap, not a leak. Decide a floor or a reranking seam before any hybrid quality claim or before hybrid reaches the Context API. |
| KI-019 | High | Portable `realpath`/`stat` cannot identify APFS clone ancestry. The pinned native bridge is implemented, but this APFS Data volume does not advertise `VOL_CAP_FMT_CLONE_MAPPING`; therefore real positive clone-family cases are unavailable on the Gate 0 host. | Predicate and fail-closed adversarial tests pass. Foundation `fileContentIdentifier` is diagnostic only. Missing capability, incomplete scans and absent matches remain `unverified`; no negative result proves confinement. Focused review decides closure. |
| KI-022 | Low | Aptuni's Notion OAuth item uses the legacy file-keychain `SecKeychain*` APIs (deprecated but functional). New items trust the creating Python interpreter, so any script run by that same interpreter can read the token without a prompt; the old `security` CLI path trusted `/usr/bin/security` instead. | Accepted for the local-first single-owner model (Review 65 N4). Revisit with a data-protection keychain or a signed helper before multi-user or distributed binaries. |
| KI-023 | Medium | ADR-0029 v1 classifiers are deterministic heuristics: MarginNote `studied` = sub-concepts, ≥2 further excerpts or an annotation; GitHub `applied` = import plus a registered construct/call; only ~35 registered concepts are detected in code. The first GitHub sync after upgrading reads every selected manifest/code/doc file once more (an unauthenticated user can hit the 60-request/hour limit and retry later). | Tune only with an ADR-0029 amendment and owner-labelled evidence; extend the registry as real repositories need it. |
| KI-024 | High | Pre-existing exact-id purge of an auto-promoted CLI memory by its memory id may commit an unappliable intent and block canonical writes until cancel. | Review 96 N1; separate reviewed privacy slice required. Do not use memory-id purge for credential cleanup. Targeted withdrawn Evidence cleanup is approved and verified. |

Resolved issues move to an appended history section; do not silently delete them.

**KI-018 product update (2026-10-02):** original ten Agent runs graded: one pass with
note, nine failures. Precise concept retrieval stays strong and the two negative
queries return no substantive records, but unnecessary calls, broad planning terms,
fragmented retries and unsupported answer claims prevent product closure. Guidance
fix `b8ba178` approved in Review 97; fresh ordinary-prompt validation is still pending,
so do not mark KI-018 resolved or release b10 from retrieval-only figures.

**KI-018 product update (2026-10-03):** unchanged post-fix ordinary-prompt seven
completed: Sonnet 2/7, Codex Astra 6/7; inside-Full relevance 7/7 each. Sonnet answer
grounding and Astra goal-to-project discovery remain material failures. The original
1/10 is not the current rate. Two blind project-goal probes miss candidates while an
oracle retrieves a tentative source-backed candidate. No production retune or b10
release; bounded discovery is a research hypothesis. Fresh six remain sealed.

**KI-018 research update (2026-10-04):** named-identity synthetic controls pass
on Astra but fail on Sonnet scope/sequence handling. Cheap fixed-evidence E
guidance establishes no drafting benefit. One strong versus planner/worker/
integrator comparison passes both finals; the three-role path uses more tokens
and latency. These are development/component results, not new product success
rates. Real named-catalog packing fails at 800 units; a separately frozen compact
format fits in 532 units after normal stale-index repair (owner Vault62→66).
Both strong compact controls pass with actual Evidence lookup. One original
application-task development retry passes the complete rubric and scope/budget
checks (3555/4000 units); a preceding zero-model configuration failure remains
counted, one acceptable completion in two attempts. Coverage remains partial
and generalization unproven. No production
contract adopted or release. C/D remain unmeasured.

**KI-018 research update (2026-10-05):** fresh locked six independently grade
A6/6 and F6/6; context-use agreement6/6 each, no unsafe/observed boundary failure.
F discovery ran on two tasks; no material paired gain, and A has better historical
support on three. A uses fewer task tokens/calls/journey time; prefer A on this
covered set. Conservative/recovery branches do not resolve original m05 actual
project selection or Sonnet grounding failures. Final assessments/accounting were
locked before evaluator quota exhaustion; lead rendered the sanitized report
without rerun or regrading. No production policy change or b10 release.

**KI-018 focused selection update (2026-10-05):** fresh two-case A/F mini
independently grades1/2 each, same required-two-reference failure. All four
claim-support judgments pass, but safe limitations do not complete a missing
selection. F does not earn promotion; A remains measured reference, not a
near-best/population-quality proof. Original2/7 and6/7 unchanged, no production
retune or b10 release. Actual catalog/Evidence coverage is partial; whether the
required source material exists elsewhere is not established by returned packets.
See `b10-continuation/selection-mini-results.md`.

**KI-018 selection mechanism update (2026-10-05):** a two-task, frozen
invented-record mechanism mini measured ordinary search0/2, automatic bounded
source-group coverage1/2 and Agent-directed planning1/2 strict E2E. Automatic
coverage raised candidate Evidence recall1/4→4/4 but still missed one required
comparison. Agent-directed query filtering omitted a gold group and had two
refused calls; no paired E2E gain. The fixture and lead grading do not prove
real-Vault quality or production privacy. Keep the single strong Agent as the
measured production candidate and the explicit interface research-only. The
release blocker remains supported multi-candidate selection with a complete
answer on fresh real tasks. See `b10-continuation/selection-mvp-results.md`.

**KI-018 real selection update (2026-10-07):** explicit-Full, current-grant
audit found two candidate-adequate real tasks and excluded one ambiguous
role/outcome task. The first freeze stopped before B's task after a research
policy contradicted Full setup; s01 A is diagnostic only. Review 112 approved
the test-first repair, and four fresh v2 sessions completed once at sequence
66. A strict E2E0/2, bounded B1/2; accepted pairs1/2 each; audited minimum
Evidence recall1/6 and2/6. All comparisons complete, so no R4 completion
intervention is justified. B still selected an artifact as a project on one
task and used more tokens/latency. A omitted Evidence IDs. Candidate precision
and corpus-wide recall cannot be inferred from the non-exhaustive audit.
Keep strong single, B research-only, and b10 closed on reliable,
evidence-attached multi-candidate selection. See
`b10-continuation/real-selection-results.md`.

**KI-018 grounded selection continuation (2026-10-07):** a prompt-only
candidate eligibility/Evidence ledger on the same strong single-Agent path
strictly passed1/3 fresh real tasks versus ordinary0/3. Eligible pairs fell
from2/3 to1/3; audited-minimum Evidence recall was0/9 in both arms, while
supported alternatives outside that minimum did appear. Three primary R1
failures show the immediate coverage issue; ordinary had two R3 omissions,
and neither arm had an R2 or independent R4 pattern. The single C pass carried
actual returned IDs. The tiny lead-graded set does not prove a reliable fix.
No product policy or privacy boundary changed; b10 remains closed on reliable
evidence-attached two-candidate selection. See
`b10-continuation/grounded-selection-results.md`.

**KI-018 R1 localization (2026-10-08):** offline replay of recorded production
calls localized the missing second candidate to concept coverage (R1b, 4/5
calls matched no candidate) plus one rank/limit cutoff (R1c). Candidates were
exposable, indexed and packaged intact when matched. A one-bullet concept
exception fixed the development cases. On a fresh, independently audited,
independently and blindly graded six-task real set it did not generalize:
strict 1/6 versus ordinary 1/6, candidate entity recall 5/21 versus 7/21, and
nine R1 primary failures across both arms. It moved R1b to R1c and was reverted.
Offline widening (round-robin, deep over-fetch, doubled budget) reaches only
17/42. No unsupported personal claim or boundary failure. Unnamed-candidate
discovery is not solvable by guidance or cutoff tuning in the current design;
next steps are owner-level (candidate-discovery surface or semantic recall).
See `b10-continuation/r1-localization-results.md`.

## Resolved history

- **KI-008 (2026-09-22):** S10 isolated Mem0 2.0.20 and conditionally admitted only a disposable
  local projection populated with `infer=False`. Upstream inference retains raw messages and is
  rejected. `Memory.delete()` leaves marker bytes in Qdrant/history, so privacy deletion must close
  and remove the entire provider root and rebuild active records from the canonical Vault. Fresh
  rebuild, exact projection equality, canonical-byte isolation, guarded network paths and complete
  managed-root purge passed; focused Review 52 approved the boundary with non-blocking notes.
- **KI-014 (2026-09-21):** Slice 17 completed the exact frozen Claude Code 2.1.267/2.1.266 and
  Codex 0.155.0/0.154.0 daily-task matrix plus focused Claude file-tool and Apple Event
  observations. The file-tool calls were not emitted, so no denial is claimed; both Apple Event
  attempts produced no outer effect. Complete effective settings remain unavailable and status
  stays `unverified`. Review 48 independently approved the conservative evidence contract.
- **KI-021 (2026-09-20):** Resolved by ADR-0016. The deletion ledger and in-flight restore journal are canonical Vault state, so deletion and restore recovery survive a wiped state directory; reads union the Vault ledger with any not-yet-migrated legacy file, and `recover()` migrates legacy ledger/journal state safely. `aptuni backup create | verify | list | restore` is the supported path, and a folder without a manifest is refused. Verified end to end on a simulated new machine: restoring a pre-purge backup dropped the purged record, kept the survivor, `doctor` passed, and a raw byte scan found no purged marker. Permanent regressions live in `tests/integration/test_backup.py`; Review 39 closed the stream **APPROVE**.
- **KI-020 (2026-09-20):** The canonical MarginNote 4 integration no longer depends on OPML. The
  accepted direct local source uses native IDs, a fail-closed schema fingerprint and text-free
  `marginnote.locator@2`; real-library sync and focused re-review 25 passed. OPML remains an optional
  compatibility path whose exporter shape is unverified, not a production blocker.
- **KI-004 (2026-09-20):** Direct MarginNote 4 native IDs replace unproven export identity for the
  flagship macOS path. Unknown layouts stop before producing deltas (ADR-0015, review 25).
- **KI-002 (2026-09-19):** License confirmed as Apache-2.0 (ADR-0009 accepted).
- **KI-010 (2026-09-19):** Thin research memory initialized (`PROJECT_KNOWLEDGE.md` → `docs/research/`).

- **KI-001 (2026-09-18):** S00 selected temporary development distribution
  `personal-context-core` / import `personal_context_core`; public naming remains a release workstream.
- **KI-012 (2026-09-18):** Execution review stream reached APPROVE WITH NON-BLOCKING NOTES (report 10);
  its notes NF1–NF8 are addressed in remediation 10.
- **KI-013 (2026-09-18):** Cold Claude Code relay drill passed (report 11); defects fixed in
  remediation 11.
- **KI-011 (2026-09-18):** Security stream reached APPROVE WITH NON-BLOCKING NOTES (report 14) after the
  maintainer chose the honest host trust boundary (ADR-0013); notes addressed in remediation 14.
- **KI-006 (2026-09-18):** S01 proved the Vault write protocol on the Gate 0 baseline (46 tests; crash at
  four boundaries, 8-process concurrency, lock-holder SIGKILL, purge/restore). Power-loss durability
  remains an assumption (`spikes/S01-vault.md` F4).
- **KI-007 (2026-09-18):** S02 proved entry-point discovery without execution, isolation of duplicate,
  broken and incompatible plugins, approval bound to the installed closure, and drift denial
  (12 tests). Undeclared-network checks are detection only.
- **KI-003 (2026-09-19):** S03 measured all three extension-free FTS5 strategies on frozen bilingual
  evidence. Deterministic 2–4-character CJK lexemes passed development, 25k-scale, and untouched
  holdout gates (23 tests); generalization and broad-query noise continue as KI-018.
- **KI-015 (2026-09-19):** S04 ran the required Codex current/preceding stable pair (0.155.0 and
  0.154.0); both returned `HOST_OK 61` on the bounded annotated read path. Installed 0.153.4 remains
  an additional observation, not the release target.
- **KI-005 (2026-09-19):** After the account limit reset, Claude Code 2.1.267 and 2.1.266 each called
  the bounded strict-config MCP tool exactly once and returned `HOST_OK 61`. Both versions also
  completed baseline and project-merge host canaries.

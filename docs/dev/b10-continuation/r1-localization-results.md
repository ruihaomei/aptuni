# R1 localization, minimal fix and fresh real-context validation

2026-10-08. Local research; one candidate guidance change, validated, rejected and reverted.
**Product decision: keep b10 frozen.** Content-free
per-run accounting is in [`r1-localization-metrics.json`](r1-localization-metrics.json).
Raw traces, answers, task wording, candidate audits and the arm map stay in owner-only
scratch outside Git.

## Boundary

Start: `b7e32c7` on `main`, unrelated owner edits preserved. Vault and disposable index at
canonical sequence 66, policy epoch 1; existing Codex grant `grant-c449a729973f45c6` unchanged
(six modules, read scopes). Every research session started OFF and enabled Full explicitly in
a separate setup turn (ADR-0025). No grant, activation, credential, backup, Vault, index,
schema, ranking, MCP server or VPN change. The installed adapter bundle was not regenerated;
both arms ran from private copies.

## Where the second candidate disappeared

The deleted grounded-selection traces could not be re-parsed, so the three earlier development
tasks were rerun once on the unchanged ordinary path (A) to record the actual tool arguments.
A research-only tracer replayed each recorded call offline through the same projection,
concept matching, diversification, limit and packing code, against the audited candidate
sources. For every call the replay reproduced the returned record set. Stages checked per
audited candidate group: exposable → indexed → matched by each concept → in the over-fetched
rows → after diversification and the Agent's `limit` → packed under `max_units` → returned.

| Stage (five recorded A calls, three tasks) | Calls where an audited candidate group survives |
|---|---:|
| Exposable and indexed (all 18 audited Evidence records) | 5/5 |
| Matched by at least one Agent concept | **1/5** |
| In over-fetched rows | 0/5 |
| After diversification and `limit` | 0/5 |
| Packed and returned | 0/5 |

Four of five calls never matched any audited candidate: the Agent's concepts were the
qualities the task would judge candidates by ("research software", "learning companion",
"context management" and Chinese forms). Under ADR-0030 each concept must match whole; those
phrases do not occur in the candidates' records, and the one allowed retry swapped in a
synonym of the same quality (zero hits). In the fifth call two audited groups matched a broad
concept at bm25 ranks 38 and 103 among 200 hits dominated by short study notes, and the
Agent's own `limit=8` cut them before packing.

**Root cause.** R1 is dominated by **R1b — query/concept coverage** (4/5 calls), with one
**R1c — ranking/cutoff** instance. It is not searchability (R1a), post-retrieval filtering
(R1e) or packaging (R1f): candidates were exposable, indexed and, once matched, packed and
returned intact. The cause sits in the shipped guidance, not the engine: the concept bullets
tell the Agent to name the specific programme, role or *prior project* and not to add methods
or neighbouring topics the request does not name. For "choose two of my projects that show
X", the request names no candidate, so the only compliant concepts are the qualities, which
lexical whole-concept retrieval cannot connect to the records.

## Smallest intervention

One guidance bullet, added to the generated Profile/Memory/Full skills (both hosts) as an
explicit exception: when the user asks to choose among their own unnamed items, use concepts
for concrete artifacts, methods or tools such work leaves in the user's files or notes, judge
eligibility only from returned Evidence, and let the single retry try different artifact
terms. No server, ranking, limit, tool, schema, grant, activation or index change. Checkpoint
`ba92faf` (test-first).

Development replays on the same three tasks (one session per arm and task):

| Arm | Calls | Returned repository groups per task | Audited pool groups returned | Task tokens | Setup + task |
|---|---:|---|---:|---:|---:|
| A ordinary | 5 | 1 / 0 / 1 | 0/8 | 274,255 | 418.731 s |
| D draft policy text | 4 | 4 / 2 / 5 | 4/8 | 256,203 | 375.340 s |
| D final skill text | 4 | 4 / 4 / 1 | 4/8 | 238,235 | 474.930 s |

D final d02 is the retry after one upstream capacity refusal with zero model output (retained).
In final-wording D the change happened at the predicted stage: the Agent's concepts became
artifact/method terms, they matched candidate records, and those groups survived to the
packet. Eligible, Evidence-supported pairs: A 1/3, D final 3/3 (one with a weaker-fit second
pick). The d03 task already names concrete practices, so the exception did not fire and D
behaved like A. Costs: fewer calls and tokens, more journey time on the d02 two-call retry.
Run-to-run variance prevents a causal cost claim.

The Agent partly echoed the example terms in the draft text, so the final wording spreads
examples across computational work, writing and organizing. Because the lead had inspected
the corpus while localizing, the fresh validation deliberately includes non-software shapes.

## Fresh validation

**Freeze.** Six new real-context goals, none reusing a development task: clinical-prediction
projects, operations-research projects, two studied subjects from study notes, a short
"name two" task that must stay brief, two extracurricular experiences, and one project plus
one studied subject (cross-category). Candidates are *entities*: several repositories or a
recollection note documenting one project count once. The lead proposed pools with Evidence
IDs. An independent auditor then judged all six adequate (four with notes), merged
same-project repositories, removed an off-kind candidate and recorded weak alternates and
ineligible decoys. All of this was applied before any session ran. Tasks, rubric, audits,
bundles, runner, server and manager digests are frozen in owner-only scratch, manifest SHA-256
`93edcccc968cf26450b91826ebe3d3ca93690270df5122ea050da66ae220c087`. Arms: A, the installed b10
bundle; D, the same bundle plus the one bullet. Both used Codex `gpt-6-astra` xhigh with explicit
Full setup, ran concurrently and ran each task once.

**Operational record.** Ten of twelve first attempts were refused upstream with
`usageLimitExceeded` during the setup turn, with zero model output and no task turn sent. Under
the predeclared zero-model refusal rule (written for capacity/overload; quota exhaustion is the
same class and is disclosed in a freeze addendum), those ten were retried once after the quota
reset, unchanged, in separate directories. All ten retries completed. No answer was inspected
before all twelve existed.

**Grading.** An independent model grader received arm-masked packets: the task, the final
answer, and every item the session actually received, with no tool arguments, because those
could reveal the arm. It graded against the frozen rubric and audits and locked the grades
before unmasking (grades SHA-256 `58cd5831…`). Evidence IDs in prose were not required; S4
grounding was checked against returned text. There was no human replication.

| Metric (six tasks per arm) | A ordinary | D concept exception |
|---|---:|---:|
| Strict end-to-end | **1/6** | **1/6** |
| Eligible selection | 1/6 | 1/6 |
| Selected candidates traceable to returned Evidence | 3/3 that selected | 3/3 that selected |
| Requested deliverable complete | 3/6 | 3/6 |
| Candidate entity recall (pool entities with substantive returned support) | 7/21 | 5/21 |
| Unsupported personal claims | 0 | 0 |
| Retrieval calls / refused | 12 / 0 | 12 / 0 |
| Task tokens | 557,792 | 579,636 |
| Setup + task journey | 639.151 s | 534.122 s |
| Primary failures | R1 4, R2 1, pass 1 | R1 5, pass 1 |

Across both arms: R1 = 9, R2 = 1, R3 = 0, R4 = 0 (R4 appears only as a consequence of R1), two
passes. Every session used two calls (one retry). Both arms stayed inside explicit Full, the
existing grant and modules, and the bounded output; there was no privacy or boundary failure.
A's pass was the extracurricular task, where the user's own vocabulary matched the quality
words. D's pass was the cross-category task.

**Where D lost candidates.** The same stage tracer on the fresh traces shows the exception
*moved* the failure instead of removing it. D's concepts now matched audited candidates (for
example 2, 4 and 7 pool entities on three tasks), but only 0–1 survived the Agent's `limit`
(6–12) and the 4,000-unit packet. Broad artifact words match thousands of study-note records
that outrank candidates: R1b became R1c. On the non-software extracurricular task, D's
artifact words matched nothing (R1b), while A's quality words had worked. The development gain
over-fit software repositories.

**Next stage tested offline, not live.** Replaying every recorded fresh call with alternative
ordering (zero model cost), pool entities returned across the 12 sessions were: recorded order
12/42; one-per-source-group round-robin 14; round-robin with full over-fetch 15; plus `limit=20`
and a doubled 8,000-unit budget 17. A bounded cutoff/diversity rule therefore cannot rescue
selection. Most candidates are never matched by the concepts an Agent can guess for items it
cannot name.

## Decision

The concept exception is **rejected and reverted** (`5b1e33d`), as Review 113 required on
rejection. Production source is again identical to `b7e32c7`. No storage, index, schema,
ranking, grant, activation or tool change remains.

**Diagnosis.** Within the current lightweight design (one strong Agent, whole-concept lexical
retrieval, bounded top-k packets), unnamed-candidate selection depends on the Agent guessing
words that the candidates' records happen to contain. Quality words (A) and artifact words (D)
each reach about a quarter to a third of eligible entities. Widening the cutoff adds little at
twice the budget. R1 repeated across all six fresh shapes. Per the stop rule, this is
evidence that the blocker cannot be solved by guidance or cutoff tuning without
disproportionate cost. What remains plausible is materially heavier: a grant-scoped
candidate-discovery surface (an inventory of the user's projects, experiences and subjects
that the Agent can scan before targeted retrieval), or semantic recall. Both are owner
decisions with privacy and dependency implications. Neither was built or tested here.
`/aptuni retrieve` stays research-only; nothing here shows that external planning would fix
missing-vocabulary recall.

**b10 is not ready to release.**

Verification: full suite 1,265 passed / 3 skipped / 62 subtests while the bullet existed;
Ruff, strict mypy, relay, secrets and notices pass. After the revert the source equals
`b7e32c7`. Raw traces, answers, packets, bundle copies and the arm map were removed after
grading. The frozen tasks, rubric, audits, manifest, addendum and locked grades remain in
owner-only scratch. The cleanup receipt is
[`r1-localization-cleanup.json`](r1-localization-cleanup.json).

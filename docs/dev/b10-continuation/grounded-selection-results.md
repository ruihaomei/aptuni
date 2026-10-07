# Grounded multi-candidate selection — diagnosis and fresh real-context mini-holdout

2026-10-07. Local, research-only. **Product decision: keep b10 frozen.** A small
single-Agent instruction improved Evidence citation in the one fresh task that
returned an eligible pair, but strict end-to-end success was only 1/3 and the
intervention selected an eligible pair on only 1/3. There is no production
policy, retrieval interface, grant, activation, storage, schema, index, or
release change. Content-free per-run accounting is in
[`grounded-selection-metrics.json`](grounded-selection-metrics.json).

## Recovered boundary and prior evidence

The starting checkpoint was `0adb0f2` on `main` (31 local commits ahead of
`origin/main`), with unrelated owner edits already present. The owner Vault and
disposable search index were both current at canonical sequence 66, policy
epoch 1. The existing active Codex grant retained the same six modules and
read scopes; research sessions started OFF and enabled Full explicitly in a
separate setup turn. ADR-0025's OFF/Profile/Memory/Full choice, live exposure
checks, credential guard, bounded disclosure, and no automatic OFF-to-Full
transition remained in force. No VPN, backup, credential, or source state was
changed.

The previous synthetic mechanism mini was ordinary 0/2, automatic bounded
coverage 1/2, and explicit planning 1/2 strict, on invented records. The
previous fresh two-task real mini was ordinary A 0/2 and bounded B 1/2 strict,
with accepted pairs 1/2 each and all comparisons completed. B used 20,123 more
task tokens and 117.485 more journey seconds without a pair-selection gain.
Its artifact-as-project mistake was R2; A's omitted Evidence IDs were R3.
Those tasks are development evidence here, never fresh validation.

## Mechanism diagnosis

**Why a runner could become a project.** Canonical GitHub Evidence already has
repository identity, owner/name, file path, and source provenance. The host
Context payload retains `source_id` and `canonical_id` but does not expose the
locator's file path or an explicit project-entity relationship. The bounded
roster groups by repository and then hydrates file-level Evidence; its bare
anchor/label does not make a file an eligible project. The Agent could rank a
runner artifact as a second project because the contract never required it to
establish a distinct project entity before ranking. Existing provenance is a
useful grouping clue, but `source_id` alone is not a universal eligibility
rule: two distinct experiences can share a source. No new ontology or canonical
type field was proven necessary.

**Where IDs disappeared.** Ordinary tool items already contained canonical
Evidence IDs. Prior A answers omitted them in the final selected claims. The
old raw traces were cleaned after the earlier audit, so the precise internal
loss between parsing, integration, ranking, and generation cannot be observed.
The supported finding is a loss between returned tool items and final answer
composition, not an absent ID in retrieval. The new dev replay showed a
per-candidate source/ID/claim ledger could carry returned IDs into the final.

Separate one-mechanism development replays used the old s03 wording once each:

| Intervention | Target and observed dev result | Calls | Task tokens | Setup + task |
|---|---|---:|---:|---:|
| H1: +473 bytes of general entity-eligibility instruction on the prior bounded policy | R2: selected two distinct documented project-level candidates; all four cited IDs had been returned | 2 | 94,338 | 98.506 s |
| H2: 420-byte internal candidate/source/ID/claim ledger instruction on ordinary A | R3: two project references, two cited IDs both returned | 1 | 58,486 | 111.535 s |

For comparison, the old s03 B run used 91,543 tokens, two calls and 243.264 s;
the old s03 A run used 81,794 tokens, two calls and 104.615 s. Different model
runs and call patterns mean these deltas are **observations, not causal cost
savings**. H1 still used the research-only bounded seam, so its dev success
does not justify that seam. The smallest credible candidate for fresh testing
was the two ideas distilled into a 158-word instruction on ordinary strong A:
identify task-eligible entities before ranking, then retain returned Evidence
IDs per shortlisted candidate. It added no tool call, runtime role, source
filter, metadata field, or reviewer.

## Fresh freeze and evaluation

Before any fresh task, a current-grant, sequence-66 audit rechecked five
documented candidate groups, 18 current exposable non-credential Evidence
records across four source IDs. Three new tasks were frozen: a research-software
application, a local learning workshop, and a maintainability handoff. Their
wording, minimum candidate pools and acceptable example pairs, goal-level
strict rubric, grant, snapshot, intervention and six-session order were saved
in owner-only local scratch. The freeze manifest SHA-256 is
`e5c920f36c45bdb4faf1c18d04b55484c7770921dbbdc04fea66ce6ee0844db0`.
The audit establishes minimum support, not exhaustive candidate recall or
personal role/outcome proof. A cross-source-category task was not forced where
the available audited project evidence did not support one.

Three paired tasks ran once each in the frozen order. A used ordinary strong
single-Agent retrieval; C used the same model, ordinary tool path, grant and
task wording plus the small instruction. No answer was inspected between runs.
The lead locked an answer-only assessment before checking returned packets and
locked support judgments before unmasking arm/resource mapping. The lead wrote
the rubric and graded the answers; there was no independent replication.

| Fresh task | A ordinary | C minimal policy | Main observation |
|---|---|---|---|
| h01 application | R3; two distinct supported software efforts, no final Evidence IDs | R1; one project plus non-project material, correctly declined a second | C cited its one candidate but lost pair coverage. |
| h02 learning | R1; only reading evidence, no eligible pair | R1; only reading evidence, no eligible pair | Both correctly refused to promote reading to project work. |
| h03 maintenance | R3; two supported project-level alternatives, no final IDs | **Strict pass**; same two alternatives, returned IDs attached, complete comparison/checklist | C preserved support into the final answer. |

The h01/h03 alternatives were outside the *minimum* pre-audited candidate
list. Their distinct source/project status and support were verified from the
actual returned packets under the frozen goal-level rule. Treating the
predeclared examples as exhaustive would wrongly label those relevant projects
irrelevant; this alternative adjudication and the single lead grader limit
confidence. Audited-minimum Evidence recall was **0/9 in each arm**, which is
not corpus-wide recall. h03 proves some relevant alternatives were returned
despite that zero. No personal role, successful result, or test-passing claim
was inferred from a title or filename.

| Metric, three tasks per arm | A ordinary | C minimal policy |
|---|---:|---:|
| Strict end-to-end | 0/3 | **1/3** |
| Eligible pair selected | 2/3 | 1/3 |
| Selected pair with returned IDs attached | 0/2 | 1/1 |
| Candidate-type errors | 0 | 0 |
| Audited-minimum candidates returned as Evidence | 0/9 | 0/9 |
| Requested comparisons completed | 2/3 | 1/3 |
| Unsupported personal claims observed | 0 | 0 |
| Retrieval calls / refused | 5 / 0 | 5 / 0 |
| Follow-up retrieval attempts | 2 | 2 |
| Task tokens | 283,341 | 255,748 |
| Setup + task journey | 362.332 s | 349.773 s |

C used 27,593 fewer observed task tokens and 12.559 fewer observed journey
seconds, with the same call count. This small, model-variable set cannot
establish a cost reduction; the quality result is insufficient regardless.
Every session observed explicit Full, canonical sequence 66 and policy epoch 1.
No call was refused, and all returned text passed the credential detector.

Primary failure classification across six fresh answers: **R0 0, R1 3,
R2 0, R3 2, R4 0; one pass.** By arm, A had R1 1/R3 2; C had R1 2/one pass.
The missing comparisons followed missing second candidates, so they do not
establish an independent R4 completion-checker need. Both h02 paths used two
bounded searches yet reached only a reading source; h01 C's two searches also
failed to bring a second project into the packet. This is observed R1, not
evidence for fetching every source or increasing roster breadth.

## Decision

The lightweight instruction deserves **no production promotion yet**. It
carried Evidence on one supported pair, but the fresh set had only 1/3 strict
success, fewer eligible pairs than A, and too little evidence to conclude R3
is generally fixed. No bounded-roster machinery, storage/schema migration,
additional Agent/runtime role, completion checker, embedding, or reranker is
justified. `/aptuni retrieve` remains inactive research only. The old bounded
roster's existence-disclosing labels also deserve privacy scrutiny before any
future product proposal; this phase added no such disclosure surface.

**The single b10 release blocker remains reliable evidence-attached selection
of two eligible real-context candidates.** The immediate observed failure in
this fresh set is R1: bounded ordinary retrieval often failed to return two
eligible candidate groups despite audited corpus support. A later experiment
should isolate that coverage mechanism under the same authorization and token
boundary; it should not retune these development tasks or adopt exhaustive RAG.
b10 is **not ready to release**.

Verification: 28 focused research tests passed; Ruff, source mypy, relay and
frozen-asset checks passed. The Vault/index stayed at sequence 66. Private
frozen inputs and content-free grades remain owner-only outside Git. After
grading, 191 phase-derived raw files (4,423,942 bytes), including native traces,
answers and the arm map, were removed; the content-free receipt is
[`grounded-selection-cleanup.json`](grounded-selection-cleanup.json). The
earlier research scratch and owner backups were untouched. This report and its
metrics contain no source contents; removed traces cannot be regraded here.

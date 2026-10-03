# Frozen ordinary-prompt E2E results — 2026-10-03

**Decision: b10 remains unreleased.** All seven unchanged tasks ran on each host
before any policy retuning. Independent grading found **Claude Sonnet 4.6: 2/7
acceptable (28.6%)** and **Codex GPT-6 Astra, xhigh: 6/7 (85.7%)**. Every trial
completed; none was repeated or discarded. These are separate host/model rates,
not a pooled product rate. The original 1/10 is the pre-orchestration-fix baseline.

## Recovery and contract

The owner locked explicit activation under ADR-0025. Full was explicitly enabled
in a separate setup turn, then each exact ordinary prompt was submitted without
an activation/search prefix. Both installed skill bodies matched the current
AdapterManager generator. Both grants used the guarded checkout, with their
original modules and no broader access. Actual STDIO checks verified OFF refusal,
explicit session Full and disable/refusal again. Setup returned zero substantive
items. Both hosts autonomously retrieved on all five personal tasks and remained
silent on the two generic tasks: **relevance accuracy 7/7 for each host**. This
measures relevance inside Full, not automatic activation from OFF.

Claude execution recovered without credential changes. The local Codex API rejected
configured `gpt-6.1-sol` and a `gpt-5.4` canary. Actual app-server model discovery and
a successful `gpt-6-astra` canary justified replacing only the global configured
model line, preserving the remaining settings. A private prechange config copy was
kept for recovery. No VPN, routing, authentication or proxy settings changed.

Frozen input SHA-256:
`8da90d4a3b7bd3d7baa152c63fdbc5a55006038607eddd9c21ee940037784c3a`.
Protocol: [unseen-protocol.md](unseen-protocol.md). Raw prompts, concepts, personal
records and answers stay in private scratch. Original-run tool confinement relied
partly on instructions; actual traces showed no extraneous Codex tools or Claude
filesystem/web execution. Stronger configuration/catalog verification was a later
generic canary, not a retrospective proof. See the protocol for this limitation. The table reports opaque task IDs
and general categories; independent item-level diagnoses were retained privately.

## Seven results

| Task | General category | Use expected/actual, both | Claude verdict / calls / seconds | Astra verdict / calls / seconds |
|---|---|---|---|---|
| m01 | Long Chinese career/study planning | yes/yes | FAIL / 2 / 65.48 | PASS / 2 / 128.19 |
| m02 | Existing research continuation | yes/yes | FAIL / 1 / 79.27 | PASS / 2 / 70.12 |
| m03 | Prior-learning mathematical exercise | yes/yes | FAIL / 1 / 36.53 | PASS / 2 / 136.37 |
| m04 | Methods comparison from prior notes | yes/yes | FAIL / 1 / 35.14 | PASS / 2 / 82.13 |
| m05 | Project selection for an application | yes/yes | FAIL / 4 / 30.69 | FAIL / 2 / 64.21 |
| m06 | Self-contained translation | no/no | PASS / 0 / 2.74 | PASS / 0 / 10.95 |
| m07 | Generic explanation | no/no | PASS with minor note / 0 / 2.81 | PASS / 0 / 16.31 |

Claude's m01–m04 materially overclaim personal proficiency, progress or absence
from study records, filenames, mentions or limited/truncated retrieval. m05 omits
the evidence-bearing `knowledge` module initially, exceeds the retrieval bound,
falls back to plain queries and misses the requested deliverable. Two module
requests were refused; protections held. No actual scope expansion or memory write
was observed. Some useful context was retrieved, but it did not produce acceptable
personalized answers.

Astra's m01–m04 give complete useful answers grounded in the limited records, with
contribution/progress/proficiency gaps made explicit. m05 retrieves preparation
material rather than actual project candidates, then supplies placeholders. It is
honest but does not satisfy the project-selection goal. Other task traces show
source-derived project evidence in `knowledge`: this is a discovery/planning gap
worth diagnosing, not proof that the missing projects meet the application goal.

## Diagnostic metrics

| Metric | Claude Sonnet 4.6 | Codex GPT-6 Astra |
|---|---|---|
| E2E acceptable | 2/7; personalized 0/5 | 6/7; personalized 4/5 |
| Relevance accuracy inside Full | 7/7 | 7/7 |
| Retrieval attempts / successful / refused | 9 / 7 / 2 | 10 / 10 / 0 |
| Attempts beyond each task's first | 4 | 5 |
| Justified language/alias retries | 0 | 5 |
| Plain-query fallback calls | 2 | 0 |
| Median calls, all / positive tasks | 1 / 1 | 2 / 2 |
| First-call concept median / maximum | 4 / 5 | 3 / 4 |
| Generic-task retrieval / narration | 0 / none | 0 / none |
| Task wall time total / median | 252.67 s / 35.14 s | 508.29 s / 70.12 s |
| Setup wall time total | 101.47 s | 194.21 s |
| Task processed tokens | 354,750 | 833,395 |
| Uncached input | 56 | 70,934 |
| Cache creation input | 17,062 | 0 |
| Cached input | 324,773 | 751,872 |
| Output, includes reasoning where reported | 12,859 | 10,589 |
| Separately reported reasoning output | unavailable | 4,902, already included above |
| Task provider-reported cost | $0.3544674, derived cumulative subtraction | unavailable |

Claude task-result `usage` is turn-scoped; its `modelUsage` and cost are cumulative
setup plus task. Codex task totals subtract setup final cumulative counters; the
last model-call usage is not a whole-task measurement. Host instruction catalogs
and caching contribute substantially to processed input. These totals do not
isolate planner cost, subscription billing or architecture effects. Judge usage
was not instrumented and is unavailable.

Exact per-task content-free accounting and trace digests (legacy run manifests
were reconstructed after execution from independently checked runner provenance
and exact record hashes; they are labelled as reconstructed, not pre-run freezes):
[frozen-claude-metrics.json](frozen-claude-metrics.json),
[frozen-codex-metrics.json](frozen-codex-metrics.json). `answer_success` stays null
in automatic accounting; the independent verdict table above supplies grading.

## Coverage, specificity, language and benefit

Claude uses broad/speculative planning topics on m01, useful specific project
aliases on m02, noisy formula terms on m03, specific methods but duplicate study
hierarchies on m04, and generic/plain fallback on m05. Concept-bearing attempts
have median five concepts; four of seven exceed four. Bilingual anchors sometimes
retrieve useful records, but grounded integration is the larger failure on four
of five personalized tasks. Two attempts have no concepts.

Astra stays within one to four concepts. Its second calls use concrete alternate
languages, shorter topic names or observed aliases. They can improve coverage,
repeat context or collide with unrelated acronym meanings. Nine calls contain
substantive records; m05's acronym retry is metadata-only. Remaining retrieved
noise includes duplicated study hierarchies, thin summaries and an acronym
collision correctly rejected by the answer.

Coverage/precision are qualitative, based on every returned substantive item in
private grading. Corpus-wide recall and numerical context precision have no valid
denominator here. m05 misses important project evidence accessible in other tasks;
its precise suitability and contribution still require evidence. Material benefit
on Astra m01–m04 is trace-supported; no no-context control establishes a causal
improvement. Claude's retrieved relevant context does not rescue failing answers.
Generic tasks correctly benefit from leaving personal context unused.

## Research consequence

A single strong host is much better on this set, but it is not yet sufficient for
the complete gate. There is no evidence that adding workers repairs an unknown
project anchor. First test a task-defensible concept bridge, then use a separately
reported oracle diagnostic only if necessary. Do not reopen settled ranking,
credential or privacy contracts. See [architecture-hypotheses.md](architecture-hypotheses.md).

A separately curated six-task mini-holdout (four personal, two generic) is sealed,
SHA-256 `6b6dda4fb23f35b7b6c2a89be4fee7e7e11b05b248e2a0eaade873d2ddf16e26`.
Candidate planners have not read its prompts. Freeze one finalist before comparing
it with A. The seven above are now development diagnostics, never independent
acceptance evidence for policies tuned using these failures.

**Verdict:** **MEASURED — b10 closed; strong single-Agent planning is promising, with a material project-discovery failure and a cheaper-host grounding failure.**

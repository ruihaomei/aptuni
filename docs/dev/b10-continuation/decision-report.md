# B10 E2E architecture decision report

2026-10-05. Local research; b10 is not released. This report separates unchanged
acceptance results, reused development controls and component experiments.

**Current recommendation:** keep one strong Agent as the quality reference. No
multi-Agent runtime has demonstrated a quality/resource advantage. A bounded,
deterministic discovery seam is the remaining research candidate; it is not
installed. Its one reused real-task retry passes, with a preceding zero-model
launch failure retained. Fresh independent six: A6/6,F6/6 with no unsafe/boundary failure. F has no
material paired gain and costs more task tokens/calls/journey time; prefer A for
these measured cases. Near-best production performance remains unestablished.
One strong-manager-justified two-case selection mini-holdout is the next bounded
experiment, with unchanged policies and at most four sessions.

The seven frozen tasks ran unchanged before tuning. Actual post-fix acceptable
E2E is **Sonnet 4.6 / Claude: 2/7 (28.6%)** and **GPT-6 Astra xhigh / Codex:
6/7 (85.7%)**, separately. The old 1/10 is the pre-fix baseline. Never substitute
a development repair for m05 and claim a new 7/7 acceptance result.

The separately locked fresh six were run once per arm, all12 completions retained.
Both arms pass6/6; context-use agreement6/6 each. F exercised discovery on two
cases but these task-allowed recovery/conservative branches do not establish
original m05 selection success. A has better historical support on three cases;
F has a modest source-fit difference on one. A uses5 retrieval calls,374550 task
tokens and635.950s total journey; F6 calls,385493 and660.061s. F returns fewer
units but establishes no monetary saving. The independent evaluator locked initial
masked grades before evidence, then support grades before arm/resource analysis.
Its quota ended after final grades/metrics; lead rendered the sanitized report
without regrading. [Fresh paired results](fresh-comparison-results.md) and
[content-free metrics](fresh-comparison-metrics.json) preserve all twelve rows.

## Original seven and current quality

| Task | General task | Should / did use, both | Sonnet E2E / calls / seconds / tokens | Astra E2E / calls / seconds / tokens |
|---|---|---|---|---|
| m01 | Long Chinese career/study plan | yes / yes | Fail / 2 / 65.48 / 49,922 | Pass / 2 / 128.19 / 156,125 |
| m02 | Research continuation | yes / yes | Fail / 1 / 79.27 / 138,416 | Pass / 2 / 70.12 / 154,742 |
| m03 | Prior-learning mathematical exercise | yes / yes | Fail / 1 / 36.53 / 36,020 | Pass / 2 / 136.37 / 158,797 |
| m04 | Methods teaching from prior notes | yes / yes | Fail / 1 / 35.14 / 36,091 | Pass / 2 / 82.13 / 154,512 |
| m05 | Application project selection | yes / yes | Fail / 4 / 30.69 / 73,249 | Fail / 2 / 64.21 / 151,087 |
| m06 | Self-contained translation | no / no | Pass / 0 / 2.74 / 10,525 | Pass / 0 / 10.95 / 29,011 |
| m07 | Generic explanation | no / no | Pass with minor note / 0 / 2.81 / 10,527 | Pass / 0 / 16.31 / 29,121 |

Personalized success is 0/5 versus 4/5. Inside-Full relevance is **7/7 each**;
there is no automatic OFF activation. Sonnet makes nine attempts, seven successful,
two refused and four extra; none of those extra calls is a justified alias retry.
Astra makes ten successful attempts, including five justified alternate-language
or observed-alias retries. Median calls over all tasks: one versus two; over the
personal tasks: one versus two. Both generic tasks remain silent.

Sonnet's first-call concept median/max is 4/5, with broad/speculative planning
terms and plain-query fallback in m05. Astra's is 3/4, using specific task anchors
and bounded bilingual/alias replacements. Language variants can recover useful
notes but also duplicate context or produce acronym collisions. Actual concepts,
queries, returned items and answer judgments were recorded in private grading;
public reports contain only general diagnoses and content-free counters.

Context precision/coverage are qualitative. There is no complete corpus relevance
label set from which to calculate numerical recall or precision. Astra uses useful
context in m01–m04 and rejects irrelevant acronym/summary material; m05 misses
project candidates. Sonnet sometimes retrieves useful context but its answer
upgrades study, mention or source material into personal ability, progress or
absence. Trace-supported material usefulness is not a causal no-context-control
estimate. [Complete seven-task results](frozen-unseen-results.md) retain these limits.

Failure taxonomy: (1) unsupported personal claim integration; (2) goal-to-project
information discovery; (3) module/call-sequence violations and excess retrieval;
(4) broad/noisy concepts or missing language aliases; (5) useful evidence displaced
or absent under bounded packing; (6) operational host/configuration or projection
state failures. Privacy refusals held. Honest placeholders still fail when the
real task requires actual project selection.

## Architectures and model roles actually tested

| Architecture / scope | Roles | Actual evidence | Resource result / decision |
|---|---|---|---|
| Current lightweight single | Sonnet 4.6 on Claude; Astra xhigh on Codex | Unchanged E2E 2/7 versus 6/7 | Strong single is current quality reference; host/model effects are confounded |
| A strong single, matched drafting | Astra xhigh | One reused fixed-evidence planning packet: full rubric pass | 18,250 tokens; 84.269-second journey; no retrieval in this component |
| B planner / bounded drafter / integrator | Astra xhigh / Sonnet 4.6 / Astra xhigh | Same packet: final full rubric pass; worker draft grounded | 46,563 tokens; 186.636 seconds; three sequential calls, no gain over already passing A |
| C cheap fast path / escalation | No task candidate run | Deferred: no validated recoverable detector or saving | Unmeasured, not empirically rejected |
| D selected runtime specialists | No task candidate run | Deferred: no identified specialist information that repairs the missing anchor | Unmeasured; research manager/curator/reviewer work is not a D runtime test |
| E cheap guidance distillation | Sonnet 4.6; two fixed packets, baseline/E | Four full-rubric failures; no planning grounding improvement | No accepted cheap finalist; methods drafts grounded but technically incomplete |
| Single strong + original synthetic discovery | Astra xhigh; four known worlds/arms | All four full-rubric failures, including lookup/citation identity confusion | Rejected original contract; retain failures |
| Single strong + named discovery | Astra xhigh then Sonnet transfer | Strong 2/2 known controls pass; Sonnet 0/2 fails scope/sequence | Combined identity/guidance effect, not field-only causality |
| A current strong single, fresh six | Astra xhigh/Codex | 6/6 complete passes, context-use6/6, no unsafe/boundary failure | 374,550 task tokens;635.950s total journey;5 retrieval calls |
| F unchanged single strong + discovery, same fresh six | Astra xhigh/Codex | 6/6 complete passes, context-use6/6; discovery exercised twice; no material gain | 385,493 task tokens;660.061s journey;6 calls; prefer A on tie |
| Single strong + compact discovery | Astra xhigh | 2/2 reused synthetic controls and completed real-task retry pass | Two staged calls, no retries; one acceptable real completion in two retained launch attempts |

Roles remain abstract: strongest practical planner/integrator, bounded worker
meeting the measured threshold, independent evaluator. Actual model availability
was verified; GPT-6 Luna passed a nonpersonal canary but was not tested as a task
worker. Neither model catalogs nor the availability of a generation establish
quality. No architecture depends on Astra specifically.

The A/B input audit uses the same task and evidence. B's strong integration stage
receives complete evidence and can rewrite freely, so B success does not isolate
the worker's contribution. Its 2.55× processed tokens and 2.21× journey time show
no measured advantage on that case. Full monetary cost is unavailable; the
worker-only reported USD0.047094 is not B's cost.
[Complete A/B accounting](strong-worker-grounding-results.md).

## Hypotheses, smallest tests and decisions

| Hypothesis | Smallest falsifier actually used | Evidence / decision |
|---|---|---|
| Relevance activation is the main failure | Inspect unchanged ordinary-prompt seven | Relevance 7/7 both while E2E differs; it is insufficient to explain failures |
| Concrete goal concepts recover unknown projects | Two bounded blind concept bridge probes | Neither returns an actual candidate; stop guessing broader concepts |
| Relevant project material exists but discovery lacks its anchor | Separate independent oracle diagnostic | Tentative evidence recovered; diagnostic only, not autonomous task success |
| Explicit identifier contract prevents lookup confusion | Separately freeze named fields and identity guidance on same two worlds | Strong both pass, cheap both fail other contracts; combined treatment only |
| A worker reduces strong reasoning cost without reducing quality | Matched A/B fixed-evidence journey | Both pass; B costs more tokens/time; prefer A on this component |
| Guidance alone fixes cheap integration | Two fixed packets under baseline/E | No demonstrated full-task gain; do not install E |
| Compact anchors fit without erasing selection information | Label boundary/collision tests, guarded aggregate audit, two strong controls | 532 real packing units; both known controls pass; packing is not real E2E |
| The bounded seam solves the actual unknown-project task | One independently frozen original m05 development probe | Completed retry fully passes; one prior zero-model failure retained; actual fresh selection remains unproved |
| The unchanged seam preserves ordinary-task quality and earns a paired gain | Fresh locked six,12 native sessions | Both6/6, no material gain; A richer/cleaner on three. Prefer A on covered set; keep original selection gap open |

No blind parameter grid, embedding research, bigger budgets, new permissions or
all-specialist workflow was used. Original failed variants remain separate.

## Tokens, latency and complexity

| Measured path | Task processed input + output | Task wall total / median | Setup / call footprint |
|---|---:|---|---|
| Original Sonnet seven | 354,750 | 252.67s / 35.14s | 101.47s setup total; 9 retrieval attempts |
| Original Astra seven | 833,395 | 508.29s / 70.12s | 194.21s setup total; 10 retrieval attempts |
| Matched A component | 18,250 | 84.269s journey | One model call; startup/close included |
| Full B component | 46,563 | 186.636s journey | Three model calls/handoffs; startup/close included |
| Compact positive / study-only controls | 92,450 / 92,366 | 64.476s / 56.115s | 22.243s / 21.657s setup; two retrieval stages each |
| Fresh A six | 374,550 | 487.174s /86.708s | 137.413s setup;635.950s full journey;5 retrieval calls |
| Fresh F six | 385,493 | 486.439s /85.552s | 164.520s setup;660.061s full journey;6 calls |
| Real m05 development retry | 95,084 | 60.868s task | 20.980s setup; two successful staged calls |

Original Sonnet: 56 uncached input, 17,062 cache creation, 324,773 cache read,
12,859 output. Astra: 822,806 input including 751,872 cached, 10,589 output
including 4,902 reasoning. B: 41,764 input, 4,799 output; known strong reasoning
1,789 is already a subset and worker reasoning is unavailable. Do not add subsets
again. Grader tokens and separate final-answer-versus-planner billing are
unavailable. Claude original reported task cost is USD0.3544674 after cumulative
setup subtraction; Codex costs are unavailable.

Static independent Reviews106/107 used89,393 input and11,294 output tokens
(including9,741 reasoning, already a subset). These are research review overhead,
not task-runtime or judge tokens. Both configured MCP/provider-off traces contain
no observed tool calls; this does not establish the complete possible host inventory.

Real retry: 93,507 input including 88,704 cached and 1,577 output including 1,101
reasoning. No supplied concept list is needed for its explicit anchors/evidence
modes; automatic `plain_query_calls=2` and `extra_calls=1` counters do not mean
fallback or retry. These are isolated observations, not latency/cost benchmarks.
Ordinary-task wall time covers prompt submission through completion, including
retrieval and answer generation. Full setup is separately timed. Cold CLI launch,
catalog negotiation and pre-turn script startup are outside these runner timers;
the A/B component journey has broader startup/close coverage as described above.

The production single path needs one host Agent plus the existing Python MCP,
local Vault and rebuildable SQLite projection. Research adds disposable CLI
runner/accounting, synthetic backend, bounded real-data wrapper and private
trace/grading files; no new package or heavy dependency. B adds three model
stages, cross-host handoff and integration complexity. C would need an empirically
validated escalation policy; D would add manager/specialist selection and critic
coordination. Neither has justified that footprint yet.

## Product decision and remaining gates

**Highest measured paired quality:** A and F tie6/6 on the fresh six.
Astra single is6/7 on the separate original seven; Sonnet2/7. Never rank or pool
these different task sets as one success rate. No tested multi-Agent architecture has a complete E2E success
rate; B's component pass cannot compete numerically with the seven-task rate.
**Best observed quality/resource tradeoff:** A over B on the matched component,
and A over F on the fresh-six quality tie. One strong single Agent remains the
research reference. No near-best general production winner or cheap-model
threshold has been proved.

Distill the successful research into clear lookup identity, minimized labels,
evidence-backed claims, study/contribution separation, a bounded two-stage
unknown-project plan, exact existing grants, and ordinary-task silence when
context adds nothing. These discoveries support deterministic/tool/skill policy
rather than permanent specialist calls. They are candidate findings, not
permission to install the research representation.

**Production recommendation:** retain the existing explicit-activation single
runtime while its material E2E gap remains tracked. Do not release b10 yet.
The next production candidate is a single strong host with the smallest reviewed
discovery seam that passes independent E2E; do not treat a heavy runtime as the
answer to missing information. **Research recommendation:** strong single A as
comparator, reusable bounded harness and independent fixed-rubric evaluation.
Run C or selected D only for a new falsifiable reason, not to fill a table.

The six were frozen before candidate outputs and provided no interim tuning.
Review106 blocked two scheduling/accounting defects; three reproductions failed
before repair and all seven invented checks then passed. Review107 approved one
12-attempt comparison, completed from483f8d3 with0 unattempted, no stop and all
observed sequences66. Final grading is A6/6,F6/6; no repeated task or silent repair.
The original project-selection requirement and Sonnet failures remain consequential.
The strong research manager proposes exactly one new, independently locked two-case
paired selection mini-holdout, at most four sessions, unchanged A/F policies and
a zero-model structural coverage preflight. Selection must be intrinsic to the
new task goals, without m05 rephrases, source hints or favorable-catalog selection.
If exclusion is provable, stop before model calls with unattempted cases; otherwise
run all four once. Prefer A on another tie; promote F only as a research candidate
for paired gain without regression, not automatic b10 release. C/D are not justified.
[Manager decision](fresh-mini-decision.md). Any held-out-informed fix needs a new
mini-holdout; production adoption requires tests/ADR/independent review.

The completed development answer and actual Evidence support a concrete
provisional candidate and useful application material; ownership and attributable
results remain unconfirmed. Two stages used546+3009=3555 units. Its catalog and
Evidence coverage remain partial. The two-attempt operational denominator is1/2,
not a new unseen success rate. [Independent development report](real-discovery-development-results.md).

No production code, installed policy, canonical schema, ranking, public MCP,
permission or credential change was made during this research phase. Global
Codex's model line was repaired earlier to a verified execution route with a
private recovery copy; the later retry repair affected only a private bundle.
A normal disposable index rebuild corrected owner-induced sequence62→66 drift;
original acceptance remains tied to sequence62. The new backend refuses drift.

Local checkpoints: `7b7919c` (frozen measurement/harness), `2ed671e` (confined
bridge/synthetic controls), `64a459c` (bounded worker and compact controls),
`91bbbdb` (bounded real development task), `483f8d3` (reviewed frozen comparison).
Reviews98–107 cover the respective research/confined/private-data boundaries;
none approves production adoption or release. Current developer suite102 passes,
Ruff/source and research mypy, relay and secret scan pass. Prior production full
baseline:1263 pass,3 skips,62 subtests; no production behavior change required
repeating it.

Remaining issues: KI-018 grounding/discovery quality; unmeasured numerical context
recall and population generalization; incomplete deterministic discovery coverage
(first5 of11/first20 Evidence); host/model and caching confounds; unavailable
full billing/judge usage; research configuration table serialization limitation;
separate KI-024 exact-memory-id purge wedge. External credential rotation and
copies remain owner-only/unverified. Both credential-clean and old pre-b9 backups
are preserved; retirement waits for stable released/verified architecture and
understood downgrade requirements.

No owner privacy, permission or product-philosophy decision blocks these
reversible research steps. Publishing b10 is not authorized by test green status.
Private raw scratch remains only while grading/review continue; remove it after
phase completion while preserving frozen inputs, prior evidence, recovery copy
and owner backups. The owner’s unrelated working-tree changes remain intact.

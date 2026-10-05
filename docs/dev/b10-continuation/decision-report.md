# B10 E2E architecture decision report

2026-10-05. Local research; b10 is not released. This report separates unchanged
acceptance results, reused development controls and component experiments.

**Current recommendation:** keep one strong Agent as the quality reference. No
multi-Agent runtime has demonstrated a quality/resource advantage. A bounded,
deterministic discovery seam was tested without installation; it failed the
fresh selection promotion condition. Its one reused real-task retry passes, with a preceding zero-model
launch failure retained. Fresh independent six: A6/6,F6/6 with no unsafe/boundary failure. F has no
material paired gain and costs more task tokens/calls/journey time; prefer A for
these measured cases. Near-best production performance remains unestablished.
The strong-manager-justified fresh selection mini is complete: **A1/2,F1/2**,
with the same required-two-selection failure and no paired gain. Unchanged F
fails its promotion bar. Safe answers are necessary; they are insufficient when
required supported selections are absent.

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

The focused mini used exactly four native sessions once and two staged offline
judge batches after Reviews109–110. Both arms use context correctly2/2, all four
source-support judgments pass, but both fail s01's two-supported-reference goal.
Both complete s02's bounded workflow/claim decision. A170588 task tokens/3 calls/
188.114s journey versus F187366/4/153.553s. F is faster on these two observations
but uses9.84% more tokens and another call, with no quality gain. Judge43921
processed tokens are separate research cost. [Focused results](selection-mini-results.md)
and [metrics](selection-mini-metrics.json) preserve all four records, hashes and limits.

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
| A/F focused fresh selection mini | Astra xhigh/Codex; two masked offline evaluator batches | A1/2,F1/2, same-case goal failure; source support4/4; no paired gain | A170588 tokens/188.114s/3 calls; F187366/153.553s/4 calls; unchanged F not promoted |
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
| The bounded seam solves the actual unknown-project task | One frozen reused m05 development probe, then separate fresh selection mini | Development retry passes; preceding zero-model failure retained. Fresh A/F1/2 each falsifies unchanged F promotion. |
| The unchanged seam preserves ordinary-task quality and earns a paired gain | Fresh locked six,12 native sessions | Both6/6, no material gain; A richer/cleaner on three. Prefer A on covered set; keep original selection gap open |
| F earns a gain when actual supported selection is intrinsic | Independently frozen focused two-case A/F mini,4 sessions | Both1/2, same required-two-reference failure; no paired gain. Do not promote F; close comparison, release frozen. |

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
| Focused A mini | 170,588 | 135.644s /67.822s | 46.814s setup;188.114s journey;3 calls |
| Focused F mini | 187,366 | 111.150s /55.575s | 38.704s setup;153.553s journey;4 calls |
| Real m05 development retry | 95,084 | 60.868s task | 20.980s setup; two successful staged calls |

Original Sonnet: 56 uncached input, 17,062 cache creation, 324,773 cache read,
12,859 output. Astra: 822,806 input including 751,872 cached, 10,589 output
including 4,902 reasoning. B: 41,764 input, 4,799 output; known strong reasoning
1,789 is already a subset and worker reasoning is unavailable. Do not add subsets
again. Earlier grader tokens and separate final-answer-versus-planner billing are
unavailable. The mini offline judge is measured separately:39117 input/4804
output=43921 processed;2631 reasoning already included, zero cache input.
Judge latency/provider billing remain unavailable. Claude original reported task cost is USD0.3544674 after cumulative
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

**Highest measured paired quality:** A and F tie6/6 on the fresh six and1/2 on the focused mini; the latter
rate fails the selection bar.
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
A future production candidate must show task-relevant selection coverage on
separate development material, then fresh independent E2E. Unchanged F is not
that candidate; a heavy runtime has no demonstrated remedy for missing support. **Research recommendation:** strong single A as
comparator, reusable bounded harness and independent fixed-rubric evaluation.
Run C or selected D only for a new falsifiable reason, not to fill a table.

The six were frozen before candidate outputs and provided no interim tuning.
Review106 blocked two scheduling/accounting defects; three reproductions failed
before repair and all seven invented checks then passed. Review107 approved one
12-attempt comparison, completed from483f8d3 with0 unattempted, no stop and all
observed sequences66. Final grading is A6/6,F6/6; no repeated task or silent repair.
The original project-selection requirement and Sonnet failures remain consequential.
The strong research manager's one new two-case selection mini was independently
locked and completed unchanged after Review108: four native attempts, no stop,
all66. Reviews109–110 repaired/reviewed only private offline grading integrity;
no candidate/task/rubric change or runtime rerun. Both offline permission gates
passed, initial answers locked before evidence, support before resources. A1/2,
F1/2 fails F's frozen promotion rule. [Focused results](selection-mini-results.md).
The final strong-manager decision **closes this bounded comparison with release
frozen**, no further experiment commissioned. Evidence establishes negative
promotion/release decisions, not a near-best-quality product. Reopening requires
a new falsifiable bottleneck, a bounded development result, then a fresh holdout;
C/D remain optional/unmeasured. [Final manager decision](final-research-decision.md).
No new production/permission/privacy action follows from the advisory result.

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
`91bbbdb` (bounded real development task), `483f8d3` (reviewed frozen comparison),
`8a59778` (fresh-six results), `e18cfe3` (focused-mini freeze), `d3743a7`
(reviewed two-stage offline grading).
Reviews98–110 cover the respective research/confined/private-data boundaries;
none approves production adoption or release. Current developer suite102 passes,
Ruff/source and research mypy, relay and secret scan pass. Prior production full
baseline:1263 pass,3 skips,62 subtests; no production behavior change required
repeating it.

Remaining issues: KI-018 grounding/discovery quality; unmeasured numerical context
recall and population generalization; incomplete deterministic discovery coverage
(first5 of11/first20 Evidence); host/model and caching confounds; unavailable
full billing/earlier judge usage; research configuration table serialization limitation;
separate KI-024 exact-memory-id purge wedge. External credential rotation and
copies remain owner-only/unverified. Both credential-clean and old pre-b9 backups
are preserved; retirement waits for stable released/verified architecture and
understood downgrade requirements.

No owner privacy, permission or product-philosophy decision blocks these
reversible research steps. Publishing b10 is not authorized by test green status.
Scoped cleanup after grading/audit removed1647 phase artifacts (31,685,494 bytes).
Nine frozen task/rubric files and the configuration recovery copy remain private;
original/preexisting inputs and both owner backups are unchanged. No phase-derived
raw trace, answer, Evidence packet or grading transcript remains in those roots.
[Cleanup receipt](private-scratch-cleanup.json) binds an opaque inventory digest.
Ephemeral native sessions were used; forensic erasure/all-system cache scanning
is not claimed. Public content-free counters/hashes preserve the completed audit. The owner’s unrelated working-tree changes remain intact.

## Required decision outputs

1–2. Seven unchanged results and current host-specific rates: table above,
Sonnet2/7 and Astra6/7. Old1/10 is pre-fix; later datasets are separate.
3–4. Failure taxonomy above; single strong handles covered tasks but is
insufficient for the demonstrated actual-selection goal, cheap single worse.
5–9. Architecture/role/hypothesis tables above; A/F fresh6/6 then mini1/2;
B is component-only; C/D unmeasured; relevance/use accuracy7/7,6/6,2/2.
10–14. Qualitative returned-context precision/coverage, calls, cache/role tokens,
task/setup/journey latency and runtime-component footprint above and linked metrics.
15–16. Raw measured quality ties A/F on paired sets; no multi-Agent E2E winner.
A wins measured simplicity and matched B resource tradeoff. Mini timing favors F,
while tokens/calls/complexity favor A; neither clears the selection quality bar.
17. Identity, bilingual replacement, bounded plans and source/owner-claim separation
are distillation candidates. No successful runtime D result exists to distill.
18–20. Retain single strong reference and current explicit-activation production;
research harness/independent evaluator only. No acceptable near-best general
production architecture is demonstrated and **b10 must not be released**.
21–22. No research-phase production change. Runner/mock/guarded seam and local
records are research-only; config model repair/index rebuild are described above.
Local commits/reviews listed; no push. Privacy/public/runtime changes would need
new test-first implementation, accepted contract and independent review.
23–24. KI-018 selection/coverage/cheap-host quality, KI-024 purge wedge, billing,
corpus truth and generalization limits remain. External credential rotation/copy
remediation requires the owner if pursued; it is separately unverified. No new
owner privacy/permission/product-philosophy decision is needed for the completed
bounded comparison. Preserve both backups and configuration recovery copy.

**Product answer:** the lightest design supported by these experiments is one
strong host Agent using autonomous, bounded retrieval inside explicit Full.
Workers/specialists have shown no advantage worth their runtime footprint. The
unchanged deterministic catalog does not repair the hard selection workload.
A near-best architecture that satisfies that workload has **not been established**;
do not trade the quality requirement for a pleasingly light design or claim
release readiness from covered-task passes.

The final independent strong manager closes this bounded candidate comparison;
no new experiment is commissioned. The overall near-best-quality objective is
partly unmet, openly recorded rather than claimed from a small passing subset.
Negative promotion and b10-release decisions are resolved. Final advisory overhead:
34808 input/3092 output,2070 reasoning already included; independent static
review/advisory/judge calls are research overhead, not runtime Architecture D.

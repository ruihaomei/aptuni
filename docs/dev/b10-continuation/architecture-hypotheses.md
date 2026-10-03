# B10 architecture hypotheses and minimum experiments

Date: 2026-10-03. Status: proposal only; no candidate policy or architecture has
been evaluated by this research manager. This note contains no private prompts,
source excerpts, answers or held-out items. It changes no runtime guidance.

## Decision to make

Find the simplest architecture that completes ordinary tasks with useful,
supported personal context at acceptable observed token use and latency. Aptuni
remains a local-first personal context layer. The concrete blocker justifying
this narrow investigation is material host orchestration failure after the
consolidated-retrieval guidance, despite useful concept-mode retrieval evidence.
Do not reopen embeddings, ranking, canonical contracts or activation policy.

The unchanged seven-task comparison is complete. The lead confirms independent
grades of 2/7 acceptable for Claude and 6/7 for Astra. The remaining
Astra failure concerns discovering suitable prior projects from a target goal.
First distinguish a recoverable concept-planning gap from missing discovery
information. More agents cannot invent unknown project names. Do not build a
catalog or multi-agent workflow before the narrow diagnostic below.

If a small single-Agent policy change closes the gap on fresh independent tasks,
prefer that architecture. Its success would establish sufficiency for those
tasks, not general reliability or unrelated release readiness. Further work on
cheaper models is worthwhile only against measured quality, cost and latency.

## Measured evidence and limits

Repository evidence:

- [Original ten E2E runs](original-e2e-grading.md): one pass with note, nine
  failures; 19 retrieval attempts, four refused. All prompts had a Full prefix,
  so these are a pre-consolidation, skill-following baseline, not ordinary-prompt
  performance. Two unavailable final answers remain failures.
- [Retrieval findings](../../research/findings/retrieval-experiments.md) and
  [ADR-0030](../DECISIONS/ADR-0030-host-structured-concept-queries.md): host
  concepts plus whole-concept matching improved the earlier local retrieval
  experiment. The same author constructed and judged that development set;
  it was not an independent E2E test. Its retrieval scores cannot substitute
  for completed, grounded answers.
- [Frozen protocol](unseen-protocol.md): explicit owner Full setup in a fresh
  persistent host process, then the exact ordinary prompt. Task metrics exclude
  setup, which is reported separately. No OFF-to-Full automatic activation.

Current-run observations supplied by the lead evaluator. This research manager
has not inspected private traces or independently graded either host:

- Claude Sonnet 4.6 completed the unchanged seven: **2/7 acceptable under the
  independent grade reported by the lead**. The two negative tasks had zero
  retrieval; the other five have material failures.
  Observed failure classes include an ungranted module request, omission of
  `knowledge` when relevant source-project evidence lives there, excess calls
  and a plain-query fallback, unsupported proficiency or progress claims, and
  broad concepts or missing language anchors that miss useful notes.
- Codex GPT-6 Astra completed all seven: **6/7 under the confirmed independent
  grade reported by the lead**. All five personal tasks used two bounded retrieval calls, without
  refusals and with careful answer grounding. The project-selection task failed
  to produce an actual project shortlist: initial target-discipline concepts
  followed by its acronym recovered coursework/application evidence. Other
  frozen tasks retrieved source-derived project evidence in `knowledge`, but
  that alone does not prove those projects satisfy this task's selection goal.
  The cheaper host's negatives also used zero calls. These cross-host results
  are not a causal architecture comparison.
- The local CLI rejected `gpt-6.1-sol` and `gpt-5.4` in attempted configurations;
  the GPT-6 Astra canary succeeded. These observations describe those routes,
  not global model availability. A Claude Opus research role requires a fresh
  access canary before scheduling it; it is not presumed available or superior.

The original ten and current seven are now diagnostic material. Neither may be
reported as an independent holdout after a policy is revised using its failures.

## A–E candidates and falsifiable hypotheses

| Arm | Role assignment | Hypothesis and evidence against it |
|---|---|---|
| **A: single strong Agent** | One strong host plans, invokes deterministic Aptuni, and writes the answer. Offline judge only. | Existing structure suffices if reliable reasoning follows the current policy. Material planning, grounding or permission failures on fresh tasks refute sufficiency on those tasks. Start with the available Astra path; report model and host together. |
| **B: strong planner + cheap worker + strong integration** | Strong planner emits a bounded task plan; cheap worker executes it; strong integrator produces the answer from permitted evidence. | Delegation saves enough strong-model work to offset handoffs while preserving A's quality. Compare **B-det**, where deterministic Aptuni executes the same structured plan, with **B-LLM**, where a cheap worker performs that execution. A worker with no semantic work should not require an LLM. Reject B-LLM if it adds calls or errors without a quality benefit; reject B overall if A or E gives the same quality more simply. |
| **C: cheap fast path + strong escalation** | Cheap host handles the task with deterministic Aptuni. A strong host takes over once on a declared gap. | Observable gaps identify tasks that need stronger reasoning without escalating routine successes. Refuted by missed material failures, needless escalation, or end-to-end cost/latency no better than A at comparable quality. |
| **D: manager-selected specialists** | Strong manager selects only a retrieval-planning specialist and/or an evidence-grounding specialist, then integrates. No default full panel. | Extra separation reveals an achievable quality improvement on failures that survive A/E. If D cannot correct those failures, there is no evidence to productize its complexity. D is a research upper bound to compare, not a proven ceiling or default deployment. |
| **E: distilled lightweight single-Agent policy** | One host follows the compact policy below and invokes deterministic Aptuni directly. No runtime judge or worker. | A short explicit decision procedure transfers the needed behavior to a cheaper host. Refuted by material held-out failures, or by matching A only through additional calls/latency that remove the intended benefit. |

Keep model capability and architecture effects distinct. A strong-model A versus
a cheap-model E estimates a deployment tradeoff. Current versus E on the same
cheap model tests the policy. A versus B/C/D with matched strong/cheap models and
the same host, corpus and grant tests the additional orchestration. Where a host
cannot support the same arrangement, label the confound instead of claiming an
architecture-only gain.

### Proposed E policy, to freeze before evaluation

1. Decide whether personal context materially helps the actual request. Answer
   generic tasks directly; an explicit context-inspection request is relevant.
2. Use the already explicitly enabled Full session. Read available module/grant
   status when needed; request only granted relevant modules. Source-derived
   learning or project evidence may be in `knowledge`; a source being a project
   does not imply its evidence is stored only in `projects`.
3. Plan the whole task once: a few specific entities, methods or requested topics
   as they could appear in notes, normally one to four concepts. Add a plausible
   alias or other language only for the same needed concept. Do not invent a
   syllabus or expand to generic parent fields to fill the list.
   For goal-to-project selection, test a defensible target equivalent or a
   directly justified domain bridge rather than relying only on a programme
   label/acronym. Such a bridge is a search hypothesis, not proof the owner has
   a relevant project. The diagnostic below must justify adding this rule.
4. Make one consolidated concept-mode retrieval with a task-appropriate bounded
   budget. Keep at most one retry for a concrete missing alias/language or
   shorter named entity. Preserve concept mode and permission scope. Truncation
   alone is not a retry reason. Count all retrieval attempts, including refusals.
5. Write the answer from the returned evidence. Distinguish mentioned, studied,
   applied and demonstrated signals; none alone proves proficiency. Names or
   titles do not establish course contents, project progress or completed work.
   State an evidence gap when it affects the task; an empty result establishes
   no absence of personal history. Give a useful answer without narrating search
   mechanics on generic tasks.

This is an untested distillation of general failure classes, not a production
change and not proof that additional instructions will be followed.

### Proposed C trigger and shared limits

Try one simple escalation rule: escalate once if a required personalized part
cannot be supported after the initial permitted retrieval **and** there is either
a concrete alternate name/language to try or conflicting evidence that changes
the answer. The cheap host emits a compact gap plus evidence references; a
structured, content-minimized handoff carries the original task, grant boundary,
prior concepts, permitted context and remaining budget to the strong host.

The strong host inherits the task's existing retrieval counter. It can use the
one remaining justified retry; escalation never creates a fresh call allowance,
grant or activation. If no justified retry exists, it answers with the known
limitation. A permission refusal is not authority to widen scope. Unavailable
models count as an operational failure, not as a reason to silently substitute.

The important falsifier is false-negative escalation: a cheap host may falsely
believe weak evidence is sufficient. Measure unsupported assertions that bypass
the trigger. Do not add a second always-on LLM judge to conceal this weakness;
test a simpler E policy or use A if C cannot detect its own gaps reliably.

D uses the retrieval specialist only for concept/module/alias planning gaps and
the grounding specialist only for evidence-to-claim or temporal ambiguity. No
general research, writing-style, domain or privacy specialist is justified by the
current evidence. Specialists receive the same bounded permitted context and
share the task's retrieval limit. Their output is advice, never a new permission.

## Smallest diagnostic before a catalog

### Frozen alternate plan — 2026-10-03, not executed by this manager

For the already failed development task, freeze exactly one alternate concept
list: `["operations research", "运筹学"]`. This is one bilingual domain bridge,
not two distinct topics. Operations research offers a defensible route from an
industrial-engineering application goal to evidence of quantitative decisions
and resource/process analysis. It is not a synonym for industrial engineering,
does not exhaust relevant project types, and does not assert that the owner has
done such work. No project name or known successful anchor informed this plan.

Keep the original task sentence as `query`, modules
`["projects", "goals", "knowledge"]`, and the 4000-unit response budget. Reuse
the unchanged first result and replace only the original second acronym retry.
Make one concept-mode call; no further list, fallback or permission change is
part of this diagnostic. Run in the existing explicit Full evaluation boundary.
The exact prompt and source content are intentionally not copied into this note.

The integrator must separate genuine project/work evidence from coursework,
reading or application aspirations. Select only supported candidates; explain
their evidenced relevance and leave undocumented contributions/results as
items to confirm. Study-only results, titles alone or an invented shortlist
fail the task. A negative result refutes this particular bridge's usefulness
under the fixed budget, not all possible aliases or the existence of projects.
The subsequent oracle diagnostic below remains conditional and separate.

### Diagnostic result and one final label-form probe

**Measured result, supplied by the lead:** the frozen list above returned only
metadata, with no matching permitted context, in **0.565 seconds**. It supplied
no new evidence from which an integrator could ground a project shortlist.
This rejects that particular list under the fixed retrieval conditions; it
does not establish that all goal bridges fail or that relevant projects do not
exist. No end-to-end integration success or general failure rate is claimed.

**Next plan, frozen before retrieval:** `["运筹"]`. This is the same named field
with the disciplinary suffix removed, testing whether notes use a shorter topic
label. One concept is sufficient; adding optimization or other related topics
would mix a new domain bridge into the label-form test. The concept remains a
goal-related search hypothesis and asserts nothing about the owner's experience.

Reuse the same original initial response, original query, granted modules
`["projects", "goals", "knowledge"]` and 4000-unit budget. Replace the second
retry with exactly one new concept-mode retrieval. This is a separate development
candidate, not a third call appended to the first candidate. Report its result
separately and include both probes in development resource totals. If it returns
only study material or metadata, it still fails to ground the requested project
selection. If it returns project evidence, apply the same strict contribution,
result and suitability checks before declaring the candidate useful.

One additional probe is justified because it isolates a concrete representation
mismatch at the existing retrieval boundary. Stop blind goal-concept variants
after this probe; do not start a list search or count best-of-development results
as independent success. The sealed holdout stays unread. Neither this probe nor
the earlier one has been executed by this research manager.

**Second measured result, supplied by the lead:** the shorter label returned six
study/application rows, no project candidate, in **0.596 seconds**. Blind goal
variants are now stopped. Both probes remain unsuccessful development attempts;
the first empty result and this study-only result are not pooled into a product
success estimate. The evaluator's separate oracle-anchor result is still pending.

**Code finding supplied by the lead's explorer:** retrieval's `documents_for`
selects statement, then excerpt, then subject, and does not index repository
locator metadata. The host has no project-discovery endpoint; Knowledge State
aggregates concepts without project labels. Stable repository identifiers and
bounded labels exist in permissioned Evidence locator/activity/concept data.
Owner-only `SourceConfig` is not a permitted discovery source. This finding
supports a concrete discoverability hypothesis, but does not establish that
relevant evidence will support a requested owner-project claim.

**H1 — goal vocabulary is the missing link.** The existing permitted concept
retriever can expose useful project evidence when given a defensible equivalent
or directly relevant bridge from the target goal. **H2 — the task lacks a
discoverable project anchor.** Relevant evidence is retrievable by its known
anchor, but goal-based concepts cannot reach it within the same bounded process.
**H3 — sufficient evidence is absent.** Returned project references do not
establish actual work or suitability; neither aliases nor a catalog can repair
that by inference. These hypotheses concern this failure, not every task.

1. Use the already failed case strictly as a local **development diagnostic**.
   A planner sees the task and current policy but no known project names, prior
   successful project results or oracle labels. Before any new retrieval, freeze
   one alternative concept list, normally no more than four entries, with a
   brief task-grounded reason for each. A target equivalent such as operations
   research and its Chinese form is eligible only if the actual goal supports
   that bridge; do not declare all related disciplines synonyms or enumerate a
   speculative syllabus. Freeze the same granted relevant modules and budget.
2. Replay the original initial call and replace only its second acronym retry
   with the frozen list. This is at most **one new alternative retrieval** when
   the original first response can be reused unchanged. Do not append a third
   task call or switch to generic plain-query search. Have the same strong host
   finish the answer; a separate evaluator checks whether the evidence supports
   the requested shortlist, its suitability and any claim about the owner's
   contribution. Mere project-name hits or a generic course list do not pass.
3. If it succeeds, H2 is unnecessary for this case. Test the general rule on two
   small synthetic controls before freezing E: one with only study/mention
   evidence and one with no relevant permitted project evidence. Neither may
   invent a portfolio. This is the smallest promising path to the sealed test.
4. If it fails, a separate evaluator may use an already observed, permitted
   project anchor for **one diagnostic retrieval**, only after confirming that
   the expected evidence is genuinely relevant to this task. Keep that name
   hidden from the candidate planner. This oracle-assisted retrieval is outside
   the product run, reported separately, and never scored as a successful task.
   If the evidence remains inadequate, H3 survives and a catalog is unjustified.
   If it supplies useful evidence, H2 becomes plausible; one failed alias list
   still does not prove that every reasonable alias would fail. Record the
   bounded result instead of starting an unrestricted query search.

The lead may run this diagnostic only within the already authorized local
evaluation boundary. This note neither authorizes new data access nor requests
private inputs. The research manager has performed none of these probes.

### Conditional catalog falsifier, still no implementation

The frozen synthetic fixtures and research-only contract are in
[`synthetic-discovery-probe.json`](synthetic-discovery-probe.json). Both cases
use the same invented task and five-label catalog with distractors. Only the
target Evidence changes: an authorship-linked implementation and bounded
synthetic result versus an imported tutorial with owner study annotations.
No private input or held-out prompt appears in the file. These are illustrative
research envelopes, not canonical schema changes.

The minimum comparison is two arms by two cases: four independent task sessions.
The catalog arm uses one counted discovery call (up to 800 units) and one
permission-checked exact-anchor evidence call (up to 3200 units), within the
same two-call/4000-unit total cap as the baseline. This explicitly tests discovery
plus a mock exact-anchor access seam; plain concept search does not currently
search the locator metadata, so catalog labels alone are not an executable fix.
The baseline keeps its ordinary retrieval freedom. If it already passes both,
there is no demonstrated catalog benefit. Do not execute either arm until the
lead chooses to proceed after the pending oracle diagnostic.

Only if step 4 supports H2, use a tiny synthetic corpus to compare the same
single strong Agent with and without a **mock bounded source/provenance anchor
catalog**. Two matched cases suffice for the first falsifier: an unknown but
relevant project and a source with an impressive title but insufficient evidence
of work. Include distractors. Construct one fixed catalog without knowing which
goal will be asked; do not hand-pick the target into its top positions. Limit it
to a predeclared small number of anchors, for example five, and report any target
omitted by that limit. Each entry contains only a permitted display label,
source kind and provenance reference; it asserts no skills or progress.

Charge the catalog as a personal-context disclosure within the same total
response budget. Replace a retrieval step rather than adding an uncounted
inventory call. One subsequent bounded evidence retrieval must ground the
shortlist; a catalog title alone cannot. If the mock catalog does not improve
the useful shortlist or induces unsupported claims on the second case, stop.
If it helps, that is only feasibility evidence for discovery, not proof a real
bounded selection algorithm will find the right anchors at Vault scale.

A production catalog would require a separate scoped proposal and applicable
privacy/public-interface review. Labels and provenance are personal data: apply
the existing grant, module, exposure and activation checks to every entry. No
unfiltered source inventory, source dump, new grant, persistent permission or
inferred owner competence is implied. The catalog stays a rebuildable projection.

## Which extra arms could address the surviving gap?

- **B:** deferred unless a strong planner finds a successful goal/anchor plan
  and execution cost is worth reducing. First replay that same structured plan
  through B-det versus B-LLM with identical budgets and integration. A paid
  worker is unwarranted if deterministic Aptuni returns the same evidence; it
  cannot repair information the plan does not contain.
- **C:** useful only if a cheap host can flag “project shortlist requested, but
  returned evidence contains no supported project candidate” and a strong host
  has a demonstrated successful recovery within the remaining call budget.
  Test one recoverable synthetic project case and the two insufficient/empty
  controls. Escalation without a reachable remedy merely adds latency. Preserve
  the false-negative grounding checks described above.
- **D:** at most one goal-to-evidence retrieval planner for this surviving gap;
  compare its frozen plan with the single strong Agent before any new retrieval.
  Both have the same task and permitted information. Add a grounding specialist
  only if new evidence shows a grounding failure after discovery. A manager
  cannot compensate for missing project anchors by naming more specialists.

These are conditional research arms, not a requirement to run all five. Report
their failures and full overhead if they are tried. Keep model/host confounds
explicit. First test a minimal E rule on the strong host so that its effect can
be separated from changing to a cheaper model; cheaper-host transfer is a later
development experiment if needed.

## Locked independent evaluation

The lead reports that an independent **six-task mini-holdout is already sealed:
four positives and two negatives**. Its prompts and labels have not been
requested or accessed for this proposal. Preserve its existing protocol and
hashes; do not replace it with the earlier suggested larger set.

Use the narrow development diagnostic to choose **one** finalist, freeze its
policy/model/host/budgets, then compare it with A on these same six tasks:
**12 task runs**. Judge each arm independently and report all failures. The
default comparison keeps A's strong model and host fixed and changes only the
small policy; a cheap-model finalist instead measures a deployment tradeoff,
not a policy-only effect. No further candidate tuning may use the six as an
independent holdout. A revision requires a new sealed set. Commission a larger
fresh set only if this comparison leaves the decision unclear; six tasks do
not establish a precise population success rate.

Prefer synthetic data for this architecture study. Existing explicitly consented
local evaluation data is an alternative under its original access boundary;
never upload private Vault content or transcripts to research/judging services.
Synthetic tasks may use available host models. A local test corpus and read-only
tools are sufficient; no live Vault or production change is required.

## Judging, accounting and selection

An independent evaluator, blind to arm labels where practical, grades completed
answers against the locked evidence and task rubric. It checks useful supported
personalization, missed required evidence, unsupported proficiency/progress,
permission requests and disclosures, justified retries, completion and generic
negative behavior. A strong model may assist on synthetic material after an
access canary; it is not the sole authority for disputed evidence entailment.
Keep the rubric fixed and resolve disputes against the evidence, with an owner
decision when task utility is ambiguous. Judge inference is evaluation cost,
not hidden runtime quality assistance.

Record raw input, cached-input, cache-creation and output tokens separately,
per role and in total. Record setup, task wall time, retrieval time, handoffs,
refusals, failures and escalation frequency. Include planner, worker and
integration overhead; parallel stages count by measured wall time, not summed
latency. Provider-reported cost is not subscription billing. Do not manufacture
missing usage components, cost estimates, precision or record-level coverage.
Use per-task measurements and descriptive medians/ranges for this small set.

All material failures remain visible. Compare quality first; privacy/permission
violations and unsupported personal claims cannot be traded for cheap tokens.
Among candidates with equal observed quality, prefer fewer model invocations,
lower measured task resources and fewer maintained components. Without a
no-context control, personalization benefit is a trace-supported judgment, not
a causal effect estimate. If that distinction determines the decision, add a
paired no-context control only for the relevant synthetic tasks.

**Verdict:** **PROPOSAL ONLY — falsify the goal-alias explanation before building a catalog; compare one frozen finalist with A on the sealed six; add roles only for a demonstrated recoverable gap.**

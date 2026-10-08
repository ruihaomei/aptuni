# Candidate Inventory MVP: unnamed-candidate selection

2026-10-08/09. Research seam only (`tools/agent_e2e_inventory.py`), not production code.
Content-free accounting is in [`candidate-inventory-metrics.json`](candidate-inventory-metrics.json).
Tasks, audits, rubric, packets, answers, traces and the arm map stay in owner-only scratch.

**Decision: Candidate Inventory is the production candidate for grounded selection. Semantic
recall is not needed. b10 stays frozen until the inventory is productionized, reviewed and
validated (see "Next").**

## Hypothesis

Unnamed selection fails because the Agent cannot enumerate candidates and must guess words that
the records happen to contain (R1b/R1c; [`r1-localization-results.md`](r1-localization-results.md),
[`r1-stage-followup.md`](r1-stage-followup.md)). If Aptuni tells the Agent *what exists*, and the
Agent decides what is relevant, recall and eligible-pair selection should rise without guessing.
Falsified if inventory exposure did not raise eligible selection, or if candidates were exposed
but repeatedly not picked or grounded.

## Primitive tested

Two research modes beside the unchanged ordinary concept search. Both require explicit Full,
grant scopes and modules, and run exposure and credential checks on every call:

- `inventory(categories)`: a category-scoped entity list derived only from provenance of
  exposable Evidence. **repositories** = GitHub repository groups (label = repository name, plus
  ≤90-byte README descriptor); **documents** = folder files (label = relative path);
  **subjects** = MarginNote root topics with ≥20 descendants (top 100 by size). No query terms
  are used. No storage, index or schema change. Built in ~1.6 s from the 49,734-record snapshot.
- `evidence(candidate IDs ≤6)`: ≤3 Evidence per candidate, README or root card first, round-robin.

Bounds: 3 task calls, inventory ≤20k units, evidence ≤10k, task ≤32k. A short policy tells the
Agent to use these modes only for choose/rank/compare-among-my-own-items tasks. Labels are clues
only; eligibility is judged from Evidence.

**Candidate identity.** A candidate is an entity, not a file. A repository, a recollection
document or a study root topic each names one. The Agent merges several repositories or notebooks
of one entity, and the grader enforces that merging. Structural coverage on the real Vault: all 18
audited v-pool entities and all 5 d-pool candidates are reachable from listed candidates.

## Development (burned v01–v06 + d01–d03, Codex)

The inventory exposed 30/30 audited pool entities. Evidence reached the Agent for 18/30, and for at
least two pool entities on 7/9 tasks (A on v-tasks: 7/21 vs I 13/21). Every task used
inventory → evidence with no concept guessing. Lead reading: about 8/9 plausible passes. The miss
(v05) is because Folder Evidence keeps only the first 280 characters of a file, so an experience
described deeper inside a multi-topic application document is invisible to *any* path, and the
Agent picked other documents. Cost on v-tasks: +6% task tokens, +3% journey time versus A.

## Fresh validation

**Freeze.** Six new goals (reproducible research software; messy real-world data; stochastic
processes preparation; causal-inference project + subject; most-studied pure mathematics; a
one-line single-project answer). An independent auditor judged all six adequate, added 12 entity
definitions (alternates and decoys) and merged one project's two code repositories before any run.
The manifest, rubric and audit were frozen (`f96dc28d…`). Arms: **A** = installed b10 bundle;
**I** = same bundle with the inventory seam and policy. Codex `gpt-6-astra` xhigh, and, at the
owner's request so that results are not Codex-only, Claude `claude-sonnet-5-5`. The Claude arms
were pre-registered in an addendum before they ran. Claude Opus 5.5 was not testable: the local
Claude Code 2.1.87 is too old for it.

**Operational record.** Three Codex sessions hit `usageLimitExceeded` in the setup turn, with no
task sent, and were retried once, unchanged, after the reset. The Claude-I seam first could not
start, because the research guard required FIFO stdout and Claude Code uses a UNIX socketpair. The
harness was fixed (reviewed, test-first, `1a24b3d`). The fix changed a hashed asset, so the running
Claude-A refused before f03 and continued f03–f06 once. Claude-I reran in full. All disclosed in
addenda. No answer was read before all 24 sessions existed.

**Grading.** An independent blind model grader received 24 host- and arm-masked packets in one
batch: task, final answer and returned Evidence/Fact items. Inventory listings and tool arguments
were removed. Grades were locked (`d1a367a8…`) before unmasking.

| Six fresh tasks per arm | Codex A | Codex I | Claude A | Claude I |
|---|---:|---:|---:|---:|
| Strict E2E | 3/6 | **6/6** | 0/6 | **3/6** |
| Eligible selection | 3/6 | **6/6** | 1/6 | **6/6** |
| Pool recall (audited entities with returned Evidence) | 9/16 | **16/16** | 3/16 | **15/16** |
| Primary failures | R1 2, R2 1 | none | R1 5, R2 1 | R4 2, R3 1 |
| Unsupported personal claims | 0 | 0 | 0 | 0 (+2 existence-only) |
| Privacy / boundary failures | 0 | 0 | 0 | 0 |
| Retrieval calls | 11 | 15 | 9 | 12 |
| Task tokens | 517,034 | 650,874 (+26%) | 294,268 | 464,004 (+58%) |
| Setup + task journey | 531.3 s | 785.0 s (+48%) | 268.9 s | 338.4 s (+26%) |

Both hosts combined: strict E2E 3/12 → **9/12**, eligible selection 4/12 → **12/12**, pool recall
12/32 → **31/32**, R1 7 → **0**, R2 2 → **0**.

**Claude-I's three non-passes are not retrieval failures.** Two are word-limit overruns (214/200
words; 54/45). One R3 comes from two *existence-only* mentions: the answer named inventory items it
never fetched Evidence for. The masking protocol hid those labels from the grader. They are
authorized context, but presenting unfetched labels as the user's items is exactly what the
policy forbids. This is a small, clearly causal guidance gap, and the same pattern appears in
regression.

## Regression (Claude, ordinary six from 2026-10-05, regression only)

A blind grader with the locked rubric scored A 5/6 and I 5/6. Context use was appropriate in 6/6
for each arm, and both stayed silent on the two self-contained tasks. I used the inventory only on
the one planning task that explicitly asks to choose from the user's history. A's miss is a
self-contained coding slip. I's miss is the same unfetched-label mention (2 existence claims).
There were no boundary or privacy issues.

## Privacy surface

New: **existence disclosure in breadth**. One call can list every authorized repository name,
folder path and large study-root title, regardless of query relevance. All of it is already
retrievable under the Full grant, and labels are derived mechanically from exposable records with
the credential check reapplied. No model generation, hidden data or new storage is involved. A
production version needs an ADR and privacy review. It should keep the inventory category-scoped
and selection-only, and consider an owner "hide from inventory" switch for sensitive paths.

## Answers to the locked research order

Candidate Inventory succeeded strongly on fresh real data across two model families, so
**semantic recall was not started**. A semantic layer could still help where entities live inside
long multi-topic documents (the 280-character Folder excerpt, R0/R1a). That is a corpus-depth
limit shared by every path, not the unnamed-discovery blocker. `/aptuni retrieve` stays
research-only.

## Next (exact)

1. Production design + ADR-0032 (privacy review): inventory/evidence as an extension of
   `aptuni_search_context` or a sibling tool, with stable provenance-derived candidate IDs, the
   same activation, grant, exposure and credential checks, and a bounded, category-scoped,
   selection-only contract.
2. Guidance in the generated skills (both hosts): the policy, plus "name only candidates whose
   Evidence you fetched" and "respect requested length limits".
3. Tests for privacy, exposure, credential, bounds, call sequencing and hidden sources.
4. Independent review, then a small fresh confirmation (Codex + Claude) on the production path,
   plus ordinary/silent regression on both hosts, before any b10 release decision.

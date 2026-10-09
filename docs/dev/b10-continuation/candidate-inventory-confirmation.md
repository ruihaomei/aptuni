# b10 decision: Candidate Inventory on the production path

2026-10-09. Content-free accounting:
[`candidate-inventory-confirmation-metrics.json`](candidate-inventory-confirmation-metrics.json)
(confirmation and regression) and [`candidate-inventory-metrics.json`](candidate-inventory-metrics.json)
(research MVP). Tasks, audits, packets, answers and traces stay in owner-only scratch.

**Decision: RELEASE b10.** The release is prepared locally. Tagging, pushing, PyPI and GitHub
publication, ADR-0032 acceptance and reinstalling the adapters are owner actions.

## What changed

ADR-0032 adds two modes to `aptuni_search_context`. Both are available only inside an explicitly
enabled Full session (`src/aptuni/application/candidates.py`):

- **inventory**: a category-scoped list of the user's repositories, documents and large study
  subjects, derived from the provenance of exposable Evidence;
- **evidence**: Evidence for up to six chosen candidate IDs.

The generated Full skill routes "choose, rank or compare my own unnamed items" through these modes.
Default search, grants, activation, storage, index and schema are unchanged. Review 114 approved
with non-blocking notes, and N1–N5 were fixed before validation.

## Evidence

**Production-path confirmation.** Five new tasks, independently audited (5/5 adequate). Frozen
before execution (`e1fb6a52…`). Baseline **A** = pre-feature server (worktree `4b7ec9e`) with the
installed b10 skills. **P** = production code `232a9c6` with freshly rendered skills and no
research policy. Blind, host- and arm-masked grading of 20 packets, locked (`11c9112b…`). 32
sessions in total, zero operational failures, zero retries.

| Five new tasks | Codex A | Codex P | Claude A | Claude P |
|---|---:|---:|---:|---:|
| Strict E2E | 3/5 | **4/5** | 0/5 | 1/5 |
| Eligible selection | 3/5 | **4/5** | 0/5 | **5/5** |
| Audited pool recall | 5/13 | **12/13** | 1/13 | **11/13** |
| Primary failures | R1 2 | R2 1 | R1 4, R2 1 | R4 3, R3 1 (existence-only) |
| Unsupported substantive claims / boundary failures | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Task tokens | 442,517 | 516,228 (+17%) | 260,607 | 430,870 (+65%) |
| Journey | 349.4 s | 316.2 s (−10%) | 167.8 s | 199.6 s (+19%) |

**Combined with the research fresh set** (six tasks per arm, the same protocol):

| Both evaluations (11 tasks per arm) | Ordinary A | Candidate Inventory |
|---|---:|---:|
| R1 (candidate not returned) | 13/22 | **0/22** |
| Eligible selection | 7/22 | **21/22** |
| Strict E2E, Codex `gpt-6-astra` | 6/11 | **10/11** |
| Strict E2E, Claude `claude-sonnet-5-5` | 0/11 | 4/11 |
| Unsupported substantive personal claims | 0 | 0 |
| Privacy or boundary failures | 0 | 0 |

**Ordinary behaviour (regression, locked rubric, blind; `145562ed…`).** Codex P passed 6/6
(baseline 6/6) and Claude P 4/6 (baselines 5/6). Context use was appropriate in 12/12 and both
hosts stayed silent on self-contained tasks. The inventory was used only on the one planning task
that asks to choose from history. Neither Claude miss touches the new code: one is a
self-contained rewrite one character over a 25-character limit, the other an incomplete
deliverable on the unchanged search path.

## Answers

1. **Inventory from current data?** Yes. It is derived per call from exposable Evidence provenance
   (GitHub repository groups, Folder/Obsidian/Notion documents, MarginNote root topics).
2. **Candidate entity:** a repository, a document or a study root topic. The Agent merges several
   repositories of one project, and same-title study roots are merged automatically.
3. **Storage migration?** No: no storage, index or schema change.
4. **Primitive tested:** category inventory → Evidence by candidate ID, three calls at most.
5. **Exposed previously missing candidates?** Yes: R1 went from 13/22 to 0/22.
6. **Candidate recall:** audited pool 12/32 → 31/32 (research) and 6/26 → 23/26 (confirmation).
7. **E2E improved?** Yes. Codex 6/11 → 10/11 and Claude 0/11 → 4/11 strict; eligible selection
   7/22 → 21/22.
8. **Cost:** +17–26% task tokens on Codex and +58–65% on Claude; journey −10% to +48%; 2–3 calls.
9. **New privacy surface:** breadth disclosure of authorized labels (names, paths, titles) inside
   explicit Full. It needs the existing scopes and modules, applies exposure and the credential
   checks, and creates no new storage. The per-source "hide from inventory" switch is an owner
   follow-up.
10. **Production-worthy:** yes. Implemented, reviewed (Review 114), confirmed on the production
    path.
11–19. **Semantic recall** was not needed and not built. It remains the option for content deep
    inside long documents (the 280-character file excerpt limit, BACKLOG).
20–21. **Strongest and recommended architecture:** one strong Agent, plus the Candidate Inventory
    primitive, plus ordinary concept search. No new runtime role, dependency or store.
22. **User experience:** invisible. The Agent decides; the user writes ordinary prompts.
23. **`/aptuni retrieve`:** stays research-only.
24. **Unnamed selection reliable enough?** At the selection and grounding stage, yes on both
    families: R1 0/22, eligible 21/22, no unsupported substantive claim. End to end on the strong
    production model (Codex), 10/11.
25. **b10 ready?** Yes, subject to the owner release actions below.
26. **Remaining risks (not blockers):**
    - Claude Sonnet 5.5 often exceeds tight output limits (5 R4 across 11 inventory sessions). It
      also misses such limits on self-contained tasks without Aptuni.
    - Sonnet sometimes names unfetched inventory items as existing (2 existence-only R3). These
      are true and authorized, but against guidance.
    - Claude Opus 5.5 is untested: the local Claude Code is too old.
27. **Known limitation the owner accepts by releasing:** on weaker hosts, selection is grounded and
    correct, but strict format limits are not reliably respected. Content deep inside long
    documents is not retrievable by any path.
28. **Owner actions:**
    - accept ADR-0032;
    - run the release (tag, push, PyPI/GitHub) under the release policy;
    - after installing 0.2.0b10, regenerate the adapter bundles so installed Full skills get the
      selection guidance;
    - optionally run `claude update` to allow an Opus check.

## Why the evidence is sufficient

The blocker was systematic R1. Two independently audited, blind-graded fresh evaluations, on
different tasks and two model families, run once through the research seam and once through the
production code, show R1 eliminated. Eligible, grounded selection is near-perfect. There are no
privacy or boundary failures and no unsupported substantive claims, and ordinary behaviour does
not regress. The remaining failures are output-format strictness on a mid-tier model, not
retrieval, selection or grounding.

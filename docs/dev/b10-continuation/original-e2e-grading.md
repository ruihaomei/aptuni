# Original ten held-out E2E runs — graded 2026-10-02

The original outputs were inspected in place, not rerun or discarded. This report
contains no source excerpts or private prompts. Retrieval attempts include refused
calls; activation-status and tool discovery are counted separately from retrieval.
The test harness prefixed **every** task with the Full skill. Consequently it tests
skill-following, not autonomous invocation from an ordinary prompt. Its negative
tasks still count as unnecessary retrieval under the requested product gate; the
forced prefix is a measurement limitation, not a reason to call those tasks passes.

| Task | Should use personal context? | Attempts / concept counts | Specificity, usefulness and final-answer impact | Verdict |
|---|---|---|---|---|
| h01 long Chinese career/study plan | Yes | 6 / 4,4,4,5,5,5 | Broad fields and guessed course lists; fragmented calls. One session-only search denied after task activation. Retrieved some coursework and application context but also tangential application material; no finished answer. | FAIL |
| h02 English research continuation | Yes | 4 / 3,4,4,4 | Named project initially precise; later generic handover/reproduction terms broadened retrieval. Two identical session-only searches denied. Useful project identity/tooling, but exact last progress missing; answer inferred open work from file names and admitted that progress was unavailable. | FAIL |
| h03 mixed-language programming explanation | Not needed for the generic examples; personalization optional | 1 / 3 | Specific technology/methods, useful library and study evidence; nested duplicate study rows. Final answer overclaimed having used a method from a study record. | FAIL (unsupported personalization) |
| h04 English application coursework | Yes | 2 / 5,5 | Broad field/coursework terms, then still broader parent fields. Programme evidence useful; only a few generic course-title records reached answer. Draft invented course contents from titles and missed grounded transcript-level detail. | FAIL |
| h05 Chinese technical review | Useful | 1 / 5 | All concepts name the requested model/algorithms; bilingual variants useful. Retrieved relevant annotated/studied material, clean answer and exercises. Five concepts exceed usual target but are justified named variants, not speculative topics. | PASS WITH NOTE |
| h06 English technical explanation tied to prior learning | Yes | 1 / 4 | Precise method names; an unrequested model example is an expansion. Relevant bilingual study records returned, with nested duplicates. Final answer claimed internalized/non-trivial understanding from study evidence. | FAIL (unsupported proficiency claim) |
| h07 generic English routine | No | 2 / 2,2 | First request included an ungranted module despite status listing grants; recovery corrected modules, not concepts. No substantive personal context returned. Answer exposed retrieval mechanics. | FAIL (unnecessary calls) |
| h08 generic Chinese email template | No | 1 / 3 | One bilingual variant, no useful context; answer exposed the empty search before giving a generic template. | FAIL (unnecessary call) |
| h09 mixed-language interview preparation | Useful for tailoring | 1 / 4 | Named target role useful, but broad parent fields dominated retrieved rows. Generic study evidence, little tailoring; answer largely a standard syllabus and no specific prior-project connection. | FAIL |
| h10 Chinese prior-study/research task | Yes | 0 / — | Tool discovery occurred, then provider usage exhausted; no retrieval and no answer. This is a failed end-to-end product journey, not a pass or a discarded trial. The trace does not support blaming concept generation because generation never occurred. | FAIL |

## Aggregate behavior

- Strict full-product outcome: **1 pass with note / 9 failures**, including two
  unavailable final answers. No inflated retrieval-only aggregate substitutes for it.
- Aptuni retrieval invoked on **9/10** tasks; **19 attempts**, **15 successful**,
  four refused (three session-search denials and one module denial).
- Five tasks used one call, four used multiple, one used none. Additional attempts
  beyond the first: **10**; multi-call rate **4/10**. None is a clean, justified
  alternate-language-only retry; h07 is permission correction, h04 is broad expansion.
- First call concept median **4**, max **5**, above four on **2/9** invoked tasks.
  Across all attempts: median **4**, max **5**, above four on **6/19** calls.
- Broad-field/speculative concepts materially affect h01/h04/h09, and generic
  follow-up concepts affect h02. Specificity is good in h03/h05/h06 except the
  unrequested model example in h06. Count alone is not a quality gate.
- Chinese and mixed prompts can retrieve English records naturally (h03/h05/h09);
  h01 uses bilingual forms but broad terms still pollute the result. h10 supplies no
  language-retrieval evidence because the host stopped before a call.
- The two explicit negative tasks return no substantive record text: lexical
  concept-mode cleanliness holds, but orchestration and UX still fail.

## Root causes and minimal response

1. Skill says to call unconditionally; it lacks a relevance decision. Add a
   decision before tools and skip generic tasks, except explicit context inspection.
2. Search-tool text says “activation first” without explaining that task activation
   leaves the session OFF. Name the session-only requirement and the correct
   task-activation retry; never widen activation scope to evade a refusal.
3. Planning guidance asks for subjects/projects but does not prevent guessed course
   inventories. Prefer named programme/role/project and actually requested child topics.
4. Default 1500 units often leaves one or two snippets; repeated larger requests
   expose this pressure. Recommend 4000 initially for complex plans/continuations;
   truncation itself is not permission to browse or expand concepts.
5. Whole-task planning and a total retrieval bound are absent. Plan once, one
   consolidated call, at most one justified replacement-term/language retry.
6. Study/mention evidence is converted into mastery or undocumented progress.
   Add explicit answer-grounding guidance; do not infer content from titles.
7. h01/h10 final traces show a provider usage limit. Do not attribute h10's missing
   call to lexical retrieval or silently rerun it. A new canary confirms the limit
   remains active; fresh validation cannot use unavailable Claude capacity.

No lexical ranking, schema, dependency or stored data change is justified by these
traces. ADR-0025's OFF-by-default contract and an ordinary-prompt auto-activation
gate need an explicit maintainer policy decision before any activation amendment.

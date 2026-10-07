# Review 113 — Unnamed-candidate selection concept exception

- **Date:** 2026-10-08
- **Scope:** commit `ba92faf` only: one `CONCEPT_GUIDANCE` bullet in
  `src/aptuni/adapters/manager.py` (shared by the generated Profile/Memory/Full skills for
  Claude and Codex) and one parametrized test in
  `tests/integration/test_activation_guidance.py`. 23 inserted lines, no deletions.
- **Policy:** AGENTS.md: block only for correctness, security/privacy, contract or
  milestone-exit defects. This reviews the guidance checkpoint as a research candidate. It
  does not adopt it, approve b10, or substitute for the frozen fresh real-context validation
  running separately.
- **Method:** scoped diff first; read the rendered skill (`AdapterManager._skill`), the MCP
  tool descriptions in `src/aptuni/mcp/server.py`, `ActivationController._retrieve` and
  `profile_context` (what each intent actually returns), ADR-0025, ADR-0030 with both
  2026-10-02 amendments, `b10-continuation/grounded-selection-results.md`, HANDOFF and
  Review 97. Rendered all six intent/host variants with a synthetic probe. No Vault, private
  trace, scratch, Agent or host session was read or run. The development replay evidence was
  taken as summarized by the lead and was not independently reproduced.

## Blocking findings

None.

## Contract and scope assessment

**Server behaviour.** The diff changes only skill text and a test. Matching, the 0–8 concept
bound, ranking, budgets, limits, grants, module checks, exposure, the credential guard and
activation semantics are untouched. The bullet contains no number, module name, scope or
activation verb. It does not imply a server capability: retrieval still matches each concept
whole (ADR-0030 item 2), and "judge ... only from the returned Evidence" is a host-side
reading rule. ADR-0025 OFF/Profile/Memory/Full remains intact. The relevance gate, explicit
activation, task scope and the no-escalation rule all precede and still govern the concept
bullets.

**Trigger scope.** The exception applies only when the user (a) asks the Agent to choose among
(b) their own items (c) without naming them. Named-topic tasks, such as the MySQL join example,
do not meet (c). Planning, application and self-assessment tasks anchored on a named programme,
role or project do not meet (a) or (c). Tasks that need no context never reach the concept
bullets. In all six rendered variants, the exception is the fifth of seven concept bullets.
It sits after the general 1–4 / specific-thing / no-broad-field / no-syllabus rules and before
the language and retry rules, so those rules continue to apply around it.

**Consistency with other bullets.**
- *1–4 / ceiling of 8:* not restated or relaxed. The examples come in pairs and fit 1–4.
- *Avoid generic words / start with the named prior project:* this is the rule being relaxed.
  With unnamed candidates, the current text leaves no compliant concept. The R1 trace
  (task-quality phrases matching zero candidate records) is a concrete defect under
  AGENTS.md item 5. The bullet does not say which earlier bullets it overrides (N2).
- *Retry:* "the one retry" refers to the existing single retry and does not add a second one.
  "Different concrete artifact or method terms" means replacing terms, which fits the
  retry bullet's "Replace the missing term".
- *Titles do not prove...:* still present and unchanged. The new bullet confines eligibility
  and fit to returned context and adds nothing that licenses inference from names.

## Non-blocking notes (record in BACKLOG; none requires another review round)

1. **"Evidence" does not match what two intents return.** `aptuni.memory` retrieves only
   `memory` records (`_record_types=("memory",)`). `aptuni.profile` drops Evidence rows that a
   kept Knowledge State unit already cites (`_summarised`). Read as the record kind, "only from
   the returned Evidence" leaves a Memory-intent Agent unable to establish any eligible
   candidate. It can also make a Profile-intent Agent ignore Knowledge State units. Under this
   rule, "fewer than two eligible candidates" can trigger the retry for the wrong reason. The
   failure is conservative (fewer selections, not over-claiming), the validation runs Full, and
   the text is under frozen validation, so this does not block. Before adoption, write
   "only from the returned context (Evidence, Facts, Knowledge State or Memory items)" or use
   lowercase "evidence", and update the test anchor to match.
2. **Name what the exception overrides.** "- Exception:" follows the no-syllabus bullet. It
   implicitly also relaxes "Avoid broad fields and generic words" and the
   "start with ... prior project" rule. A short lead-in helps Agents keep the 1–4 and
   whole-match rules in force. One option is "Exception to the two rules above (still 1-4
   concepts):".
3. **Pair-shaped retry trigger.** "Fewer than two eligible candidates" matches the pair-selection
   development tasks. For "pick the best one" it still makes sense, because a comparison
   needs alternatives. For "choose three" it does not trigger at a useful threshold. A
   neutral alternative is "if too few eligible candidates return to compare".
4. **Generic artifact terms are high-recall by design.** Single-keyword concepts like "draft",
   "pipeline" or "checklist" match any granted, exposable record that contains them. Disclosure
   stays within the explicit activation, granted modules, exposure filters, `limit` and
   `max_units`, and the user asked for a choice among their own items. This is therefore not a
   new disclosure class or a Vault enumeration path. Off-topic leakage and the number of
   distinct groups versus noise for this task class are unmeasured, though. The fresh validation
   should report them, together with retrieval calls.
5. **Artifact presence versus quality.** "Unit test" or "revision" retrieves work that leaves
   such artifacts. It does not show the work was careful, tested or successful. The existing
   bullet "Do not invent ... project progress or proficiency from titles and file names" covers
   this. One clause in the exception would make the link explicit: "an artifact shows the work
   exists, not its quality".
6. **Host parity: non-blocking follow-up, not a defect.** Claude/Codex parity is complete. The
   shared generator gives byte-identical skill bodies, and the test covers both hosts and all
   three intents. Skill-versus-MCP-description divergence is deliberate and acceptable during
   validation:
   - explicit activation reaches the tools through the skill (ADR-0025; Claude
     `disable-model-invocation`, Codex `allow_implicit_invocation: false`);
   - the tool descriptions do not contradict the exception, because they forbid syllabi, guessed
     courses and parent fields, not artifact terms;
   - a host without the skill falls back to the prior, safe guidance;
   - changing the shared server would confound the A/B arms.

   ADR-0030's amendment says the skills and the `aptuni_activate_context` description carry the
   guidance together. If the candidate is adopted, add a compact clause to that description and
   amend ADR-0030 in the same change. If it is rejected, revert the bullet.
7. **Product text ahead of its validation.** HANDOFF says b10 stays frozen, with no production
   policy change from the selection research. This commit nevertheless puts candidate text in
   the product generator on `main`. Any new `aptuni adapter apply` from this tree would ship it.
   b10 is unreleased and the commit message records "validation pending, bundles not
   reinstalled", so this is not a milestone-exit failure. Record the candidate status, and the
   revert path if validation fails, in STATE/HANDOFF. Also register this review in
   `docs/dev/reviews/STATUS.json`, which the reviewer was told not to edit.
8. **Development evidence stays in-sample.** The replay improvement (2–5 distinct repository
   groups per task instead of 0–1) was measured on the same development calls that diagnosed the
   defect. The five-call count matches the earlier fresh A arm. If these are the 2026-10-07
   h01–h03 tasks, HANDOFF's "do not retune or revalidate on these three tasks" means the replay
   supports only the mechanism. Only the separately frozen fresh validation counts toward
   adoption, and the results note should say so.
9. **Test robustness and limits.** The test pins the behaviour for all three intents and both
   hosts, using four clause-level anchors (trigger, artifact concepts, Evidence-only judgement,
   single retry), plus the absence of "8" and the continued no-syllabus rule. This is a fair
   balance between pinning and over-fitting, consistent with the file's style. Possible
   improvements:
   - Use `next(..., None)` with an assertion message instead of a bare `next()`, so a missing
     line reports clearly rather than as `StopIteration`.
   - Assert that the exception precedes the "Retry at most once" bullet.
   - Remember that, as Review 97 noted, string tests prove the instructions ship, not that
     Agents comply.

## Verification

| Check | Result |
|---|---|
| `git show --stat ba92faf` | 2 files, +23/−0; no server, schema, ranking, grant, activation or MCP change |
| `.tools/bin/uv run pytest tests/integration/test_activation_guidance.py tests/integration/test_adapters.py -o addopts='' -q` | 19 passed in 2.36 s |
| `.tools/bin/uv run ruff check src/aptuni/adapters/manager.py tests/integration/test_activation_guidance.py` | All checks passed |
| Synthetic render of `_skill` for 3 intents × 2 hosts | exception present exactly once in each, bullet 5 of 7 (after no-syllabus, before language/retry); Claude and Codex bodies identical; session utility skill unaffected |
| Intent return shapes (`activation._retrieve`, `profile_context`) | Full returns Evidence; Profile may summarise Evidence into Knowledge State units; Memory returns no Evidence (note 1) |

The full suite, strict mypy, relay checks and the frozen fresh real-context validation remain
the implementing agent's checks. This narrow review does not replace them, and it approves
no adoption or release.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

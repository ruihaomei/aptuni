# Strong single pass versus bounded worker — development grounding

Graded 2026-10-04. A strong single pass and the final answer from a strong-plan → worker → strong-revision sequence both pass the unchanged planning-packet rubric. Both produce useful plans without upgrading study or source exposure into personal implementation, mastery or achieved results. The worker's intermediate draft also respects the supplied claim boundaries, but that is diagnostic evidence, not an independent architecture success.

The sequence does not repair an A failure: A already passes. Its final reviewer receives the complete original evidence and may rewrite freely, so the final success cannot be attributed to the worker. The observed sequence takes more time and uses more model tokens; full cost is unavailable. No cheap-worker advantage is established.

## Frozen scope and input audit

This comparison reuses one previously evaluated planning packet, `g01`, with the existing consented context. It tests fixed-evidence development grounding, not activation, discovery, retrieval, production grants or end-to-end acceptance. It does not use independent owners or unseen tasks, and it provides no causal benefit proof. The sealed six remains unread.

Frozen digests: spec `559db917a749`; script `55cef7de11aa`; packet `1ac56ed33f9b`; unchanged rubric `f6b846011d71`.

A is one `gpt-6-astra`, `xhigh` answer. B has three fresh sequential calls: B1 uses that strong model to create a bounded plan; B2 uses `claude-sonnet-4-6` to draft from the original task and plan; B3 uses the strong model to check and revise the draft. Role instructions differ by design. No policy or rubric was changed for grading.

A and B1 have identical native user input. B3 receives that exact input plus the exact B1 plan and B2 draft. Native user-message text matches the frozen reconstruction and each manifest's input digest. The context string decodes to the exact locked packet response. B2's manifest confirms the exact plan digest and that complete evidence was withheld. The frozen script sends the exact original task as stdin; Claude's native stream does not repeat that initial prompt, so provider-side prompt equality is not independently asserted for B2.

A and B3 final answers were shuffled with role labels, intermediate answers and metrics withheld until judgments were saved. The case and workflow spec remained known; wording could reveal a role. This is limited blinding. B1/B2 and traces were inspected afterwards.

## Outcomes and confinement observations

| Primary final | Personal-claim support | Useful requested deliverable | Fixed rubric |
|---|---|---|---|
| A: strong single pass | Pass | Pass | Pass |
| B3: sequence final | Pass | Pass | Pass |

Both finals treat prior learning as a starting point, keep source-described project work unconfirmed, and distinguish proposed work from past accomplishments. Both preserve the requested staged horizon and deliverables, prioritize ability verification and reproducible experiments, and restrict personal contribution and outcome statements to actual verified work. No unsupported personal assertion was found.

B1's references resolve to the supplied packet items. Its plan preserves study-versus-contribution and missing-versus-absent boundaries. B2 follows those boundaries, leaves authorship and ability unconfirmed, and gives a useful staged draft. B3 adds concrete modelling and experiment detail while retaining those limits. These observations show a feasible bounded drafting handoff in this one reused case. They do not isolate the worker's contribution to the final quality.

All four calls completed without operational errors or retries. Strong-host traces have no tool-related item started or completed; the backend is synthetic only. The worker's native initialization reports empty tools and MCP servers, with zero tool calls, permission denials, web searches and web fetches. No retrieval, command, write or external-service tool call was observed. This is trace evidence for the restricted experiment, not a claim that every strong-host tool was disabled or that production confinement was tested. The three final/draft answers also fit the frozen character limit.

## Complete measured journey accounting

| Role | Turn/native duration (s) | Role journey (s) | Startup, close and wrapper residual (s) |
|---|---:|---:|---:|
| A | 80.632 | 84.258 | 3.627 |
| B1 | 71.263 | 74.481 | 3.218 |
| B2 | 23.036 | 25.928 | 2.892 |
| B3 | 82.679 | 86.200 | 3.521 |

Codex turn duration is runner wall time; Claude turn duration is its native reported duration. Residuals combine startup, closing and wrapper work and do not isolate launch time.

| Path | Sequential model calls | Timed main journey (s) | Total reported input + output tokens |
|---|---:|---:|---:|
| A | 1 | 84.269 | 18,250 |
| B | 3 | 186.636 | 46,563 |

B's role journeys total 186.609 seconds, including 9.630 seconds of role startup/closing/wrapper residuals. A further 0.027 seconds is measured outside those role timers for orchestration, extraction, input assembly and persistence; it is not an isolated handoff benchmark. A's analogous outside-role residual is 0.010 seconds. Model-host startup and sequential handoffs are included. Python launcher/import startup and common packet/text preparation before the main timers are unmeasured.

These are individual observed journeys, not a latency benchmark or population success rate. Reporting only the worker's 25.928 seconds would omit both strong stages.

## Native token and cost accounting

Strong-role values are final RPC cumulative usage from fresh single-turn sessions. Cached input and reasoning output are subsets. Cache-write input is zero throughout; subset tokens must not be added again.

| Strong role | Input | Cached input | Output | Reasoning output | Total |
|---|---:|---:|---:|---:|---:|
| A | 16,379 | 0 | 1,871 | 1,034 | 18,250 |
| B1 | 16,418 | 0 | 1,632 | 755 | 18,050 |
| B3 | 17,967 | 0 | 1,872 | 1,034 | 19,839 |

B2's fresh one-turn provider result matches its per-model usage: 3 uncached input tokens, 7,376 cache-creation tokens, zero cache-read tokens and 1,295 output tokens. Its input-plus-output total is 8,674. Its current-turn reported cost is **USD 0.047094**, not an independent billing estimate. There is no setup turn or cumulative subtraction.

The B aggregate counts each input and output once: 41,764 input tokens and 4,799 output tokens. Claude input includes separately reported uncached, cache-creation and cache-read components; Codex input already includes cached input. B's known strong reasoning-output count is 1,789; worker reasoning output is unavailable, so the total reasoning count is unavailable. Grader tokens are also unavailable and are not estimated.

Strong-stage costs are not reported. Therefore A's full cost and B's full cost are both unavailable; the worker's USD 0.047094 must not be presented as B's total. No cost saving is inferred.

## Decision

Keep the single strong pass as the development comparator. This pair supports the narrow feasibility of the bounded worker handoff, but gives no reason to prefer it over an already successful single pass on quality, latency or known total cost. Any broader reliability or architecture decision requires separate evidence. These results do not approve production changes or unlock the held-out tasks.

**Verdict:** **B FEASIBLE, BENEFIT UNESTABLISHED — A already passes; B adds two sequential stages without a demonstrated worker advantage.**

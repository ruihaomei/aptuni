# Compact contract — reused synthetic development controls

Graded 2026-10-04. Both strong-host controls pass the unchanged synthetic rubric, including actual evidence lookup, useful deliverable, personal-claim boundaries and the two-call/4,000-unit cap. The host copied the opaque lookup anchor correctly in each world and received the exact corresponding fixture evidence.

These are separately frozen development controls reusing the known invented worlds. They are not independent unseen evaluation or end-to-end acceptance. The [earlier failures](synthetic-discovery-results.md) remain unchanged; this result does not repair their grades or establish a general discovery benefit.

## Frozen inputs and grading

Both runs used `gpt-6-astra`, `xhigh`, Codex CLI 0.155.1, explicit Full setup and the knowledge module. Frozen digest prefixes: policy `4fff0074de36`; mock snapshot `a929f8e97c50`; runner `6a6480d1651c`; unchanged fixture/rubric `86a3ca567773`. Per-world dataset digests match the prior strong development controls.

Final-answer grades were saved before trace metrics. This is one known arm, with cases visible for the fixed rubric; no meaningful between-arm blinding is claimed. Lookup and compliance were audited separately. No policy, rubric or fixture was changed, and there was no grader access to the Vault, canonical sources or sealed six.

## Per-world outcomes

| World | Actual evidence | Fixed-rubric deliverable | Personal claims | Retrieval calls | Retries | Used task units |
|---|---|---|---|---:|---:|---:|
| Supported work | Exact positive record | Pass | Supported and bounded | 2 | 0 | 1,324 |
| Study only | Exact negative record | Pass | Study distinguished from contribution | 2 | 0 | 1,282 |

The positive answer selects the supported implementation, explains its operational relevance, and gives a factual short description. It attributes only the stipulated implementation and tests, limits the comparison to synthetic scenarios, and requests remaining contribution, evaluation, deployment, scale and leadership evidence. Its selection is qualified to retrieved material, not a full-corpus ranking.

The negative answer identifies third-party study and owner annotations, gives a useful study sentence, and asks for concrete contribution, validation and actual-scope evidence before a project claim. It does not turn the impressive label into owner implementation or measured impact. No unsupported owner claim was found in either answer. The negative passes because the underlying study-only record was read and used, rather than merely because the host abstained after an empty result.

## Packing and observed protocol

Both catalogs returned all five original invented labels, each paired only with an opaque anchor. No label was shortened and no anchor collision occurred. All labels fit the 48-UTF-8-byte cap, so these runs do not exercise shortening or ambiguity at that boundary.

Catalog metadata used **605 units** in each run. Evidence used **719** or **677** units, respectively. The totals were independently recomputed with the existing UTF-8 estimator, including the response and item overheads. Both fit the 800-unit catalog stage, 3,200-unit evidence stage and 4,000-unit task cap without truncation. The second call is the planned evidence stage, not a retry.

Each task made two retrieval calls and one content-free activation-status call. Setup made one status call and one explicit Full activation, returning 32 context units separately. Each run therefore has five observed MCP calls across setup and task. There were no refusals, tool errors, extraneous tool calls, writes or external-service tool calls. Requests stayed within knowledge. This is evidence from restricted synthetic traces, not proof of complete production confinement or permission behavior on a live corpus.

## Measured resources

| World | Setup wall (s) | Task wall (s) | Retrieval tool durations (ms) |
|---|---:|---:|---|
| Supported work | 22.243 | 64.476 | 14, 3 |
| Study only | 21.657 | 56.115 | 16, 5 |

Task token counts subtract native RPC cumulative usage at setup end from task end. Cached input is part of input; reasoning output is part of output. These subsets must not be added again. Cache-write tokens and setup reasoning output were zero.

| World / phase | Total | Input | Cached input | Output | Reasoning output |
|---|---:|---:|---:|---:|---:|
| Supported work / setup | 67,182 | 66,954 | 49,280 | 228 | 0 |
| Supported work / task | 92,450 | 91,228 | 88,448 | 1,222 | 602 |
| Study only / setup | 67,190 | 66,959 | 62,848 | 231 | 0 |
| Study only / task | 92,366 | 91,249 | 88,448 | 1,117 | 563 |

Provider cost and grader model tokens are unavailable and are not estimated. Individual timings and counts are not a latency benchmark, population success rate or cost-saving claim.

## Interpretation

The compact handoff works for this complete five-entry invented catalog and preserves the two intended evidence boundaries. It does not establish large-corpus selection, label coverage, shortening safety, cheaper-host transfer, live-corpus source fidelity, or causal benefit. Separate packing and environment-repair observations are outside these control grades.

The result supports considering a separately reviewed development probe only. It does not authorize a live wrapper, production contract, grant expansion or access to held-out tasks.

**Verdict:** **COMPACT DEVELOPMENT CONTROLS PASS — bounded lookup and grounding work in both reused worlds; independent acceptance remains unestablished.**

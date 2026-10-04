# Fixed-evidence grounding replay — conditional drafting results

Graded 2026-10-04. Four completed, single-turn `claude-sonnet-4-6` drafting calls in Claude Code 2.1.87. No tools or MCP servers were enabled in their native initialization events, and no tool call was observed.

Neither arm fully passes the frozen rubric on either packet. Both planning answers upgrade documented study and source exposure into unsupported personal ability, completed work or current gaps. Both teaching answers preserve modest personal grounding and provide useful explanations, but technical defects prevent a complete rubric pass. These are separate findings: accurate attribution does not by itself make the full answer correct, and useful personalization does not require blanket abstention.

## Inputs and scope

The two packets reuse exact original tasks and exact successful, truncated Claude Aptuni response text from the already evaluated development set. The underlying context was supplied directly. There was no activation, retrieval, setup turn, new Vault/source read or access to the sealed six. This is conditional drafting evidence, not independent unseen evaluation, independent-owner evidence or proof of causal benefit.

Both arms received a common system boundary: answer from quoted context, use no additional tools, and distinguish missing or truncated evidence from absent history. Baseline is therefore a fixed-evidence replay control, not the original end-to-end product environment. E adds the frozen candidate policy; its retrieval clauses are inert here. The exact task and context remain the same within each pair.

Frozen digest prefixes: packets `1ac56ed33f9b` and `d65d1c7a2cdd`; rubric `f6b846011d71`; runner script `fc1fe94d174f`; E policy `96057a543767`. Manifests match the frozen packet bytes and shared script digest. No task, context or rubric was changed for grading.

Final answers were shuffled with arm labels and trace metrics withheld until answer judgments were saved. Case identity remained visible for the task-specific rubric, and wording could reveal an arm. This is limited blinding. Personal-claim support, useful deliverable and overall correctness were judged separately; trace compliance and resource metrics followed.

## Per-session outcomes

| Packet / arm | Personal-claim support | Useful deliverable | Overall fixed rubric | Trace compliance |
|---|---|---|---|---|
| Planning / baseline | Fail | Actionable plan; unsupported current-state premises | Fail | Pass |
| Planning / E | Fail | Actionable plan; unsupported premises and horizon mismatch | Fail | Pass |
| Teaching / baseline | Pass | Concrete prior-note connection; technical inaccuracies | Fail | Pass |
| Teaching / E | Pass | Concrete prior-note connection; technical inaccuracies and missing fitting explanation | Fail | Pass |

The planning control treats study records as evidence of sufficient theoretical readiness and a source-described model as personally completed implementation. It also asserts missing capability and current implementation scope that the bounded context cannot establish. It supplies the requested broad plan structure but does not request the required authorship, contribution, status and results confirmations.

E's planning answer likewise turns study into broad demonstrated ability and source exposure into an attributed research advantage. It requests completion/results confirmation but leaves authorship and personal contribution unconfirmed. It treats unshown solver practice as absent and allocates a longer total horizon than the task stipulates. These unsupported claims are not repaired by the later confirmation question.

Both teaching answers correctly use documented learning anchors without inventing proficiency or owner implementation from repository mentions. Neither abstains. The control contains inaccurate geometry/density guarantees and model-selection statements. E gives an unqualified equivalence between distinct fitting procedures and omits the required update-step comparison; it also presents a geometry assumption as a guarantee. Detailed task-specific claim checks remain evaluator-only. Modest personal grounding passes in this pair, while technical soundness and complete usefulness fail.

## Native trace and resource accounting

All four runs have native `tools=[]`, `mcp_servers=[]`, one turn, zero observed tool/MCP/retrieval calls and zero retries. The results report no permission denials, web searches or web fetches, and no operational error. No write or external-service call was observed. This establishes compliance for these restricted replay traces; it does not test production host confinement or grants.

Usage below comes from each fresh session's native current-turn result and matches its per-model usage. There is no setup subtraction. Uncached input, cache creation and cache read are separately reported components; nested cache-duration fields are subsets. Reasoning-output tokens and grader model tokens are unavailable and are not estimated. Costs are provider-reported current-turn values, verified against per-model cost, not an independent billing estimate.

| Packet / arm | Wall (s) | Uncached input | Cache creation | Cache read | Output | Reported cost (USD) |
|---|---:|---:|---:|---:|---:|---:|
| Planning / baseline | 39.879 | 3 | 7,597 | 0 | 1,723 | 0.05434275 |
| Planning / E | 33.113 | 3 | 8,144 | 0 | 1,614 | 0.05475900 |
| Teaching / baseline | 20.951 | 3 | 5,108 | 2,578 | 913 | 0.03363240 |
| Teaching / E | 21.896 | 3 | 5,655 | 2,578 | 1,003 | 0.03703365 |

These are individual observations with different cache states across packets, not a latency benchmark or a population success rate. The report does not infer missing token components, monetary savings or a generally cheaper successful pipeline.

## Interpretation

The supplied evidence permits useful bounded personalization, as both teaching answers demonstrate. The candidate policy does not repair the planning overclaims in this replay pair, and neither arm meets complete technical correctness on the teaching task. No conditional drafting benefit is established. This result does not evaluate discovery, activation, retrieval quality or end-to-end task success, and does not authorize a production change or unseal the six-task holdout.

**Verdict:** **NO DRAFTING BENEFIT ESTABLISHED — both planning arms overclaim; modest teaching personalization is preserved, but complete correctness fails.**

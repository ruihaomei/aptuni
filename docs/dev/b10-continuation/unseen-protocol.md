# Frozen ordinary-prompt E2E protocol — 2026-10-03

The owner resolved the pending interpretation: ADR-0025 stays explicit and OFF by
default. Within an explicitly enabled Full session, the host autonomously decides
whether context helps, plans concepts, retrieves and answers the original task.
The seven previously locked task texts are unchanged. Their private file digest is
`8da90d4a3b7bd3d7baa152c63fdbc5a55006038607eddd9c21ee940037784c3a`.

## Execution boundary

Each task has a fresh, persistent host process. A separate owner-authorized setup
turn invokes the current generated Full skill and activates `aptuni.full` with
`scope=session`. Setup uses a deliberately unmatched concept and a 32-unit budget;
it conveys no substantive personal context. The following turn is the exact frozen
ordinary prompt, with no skill prefix, concept repair or retrieval instruction.
Session setup calls/tokens/latency are reported separately from task metrics.

Claude uses the current generated plugin skills and exact bundle MCP configuration
with strict MCP isolation, no persistence, no filesystem/web tools and no memory
writes. Codex uses a persistent ephemeral app-server thread, the unchanged generated
Full skill, the current grant and repository MCP implementation. Only the four Aptuni
activation/status/search/disable MCP tools were allowlisted. The original Codex
runner disabled other configured MCP servers and shell/multi-agent features, but
did not verify a complete builtin/app capability catalog; broader confinement
was an instruction plus read-only sandbox. Actual frozen traces were independently
audited: Codex used only Aptuni, and Claude used discovery/Skill plus Aptuni,
with no filesystem/web/app execution or memory writes. The later research runner
and a separate generic OFF canary explicitly disabled inherited apps/plugins,
browser/computer/image/shell/code tools and web search, verified effective settings
and the four-tool MCP catalog. This later canary is not retrospective proof of
the frozen runner’s full confinement. No grant,
activation semantics, ranking, schema, provider or guidance is changed before the
frozen runs. Record host/model versions and actual tool traces, not just instructions.

## Scoring and evidence limits

The original ten runs are the pre-consolidation baseline. They are not a current
success estimate. Report each host's seven-task denominator separately; do not pool
different models into a product rate or discard unavailable answers.

A pass requires a completed answer satisfying the task, correct relevance behavior,
materially useful supported personalization where requested, no invented proficiency
or project progress, no permission expansion, and bounded task retrieval (normally
one call, at most one concretely justified alternate-term/language retry). Generic
negative tasks should have zero retrieval and no narrated search mechanics. Empty
results are not evidence that the owner has never studied or done something.

For every task record expected/actual use, retrieval attempts/refusals/retries,
concept count/specificity/broadness/language, helpful/missed/irrelevant context,
answer quality and material benefit, raw reported token components and wall latency.
Precision/coverage judgments are qualitative unless a record-level denominator is
actually graded. Cached input, cache creation and output must remain distinct;
provider-reported costs are not subscription billing claims. No no-context control
means material benefit is a trace-supported judgment, not a causal effect estimate.

b10's complete product gate remains closed on any material failure. No further
policy tuning uses these seven as an independent holdout. If the results demonstrate
an orchestration bottleneck, record a falsifiable hypothesis before research; lock a
fresh held-out set before candidate evaluation and keep production conservative.

Private prompts, context and answers remain local scratch. Commit only sanitized
aggregates/diagnostics; remove this phase's private traces after grading and review.
Preserve existing frozen inputs, prior evidence and both owner backups.

# Review 98 — Research harness privacy and orchestration

- **Date:** 2026-10-03
- **Scope:** `tools/agent_e2e.py`, `tools/agent_e2e_run.py`, their two development
  test files, and the frozen protocol, results and candidate-policy documents in
  `docs/dev/b10-continuation/`.
- **Policy:** block for correctness, security/privacy or contract failures. This
  review covers disposable research tooling, not production changes or a release.
- **Method:** initial working-tree inspection, focused remediation review, synthetic
  failure probes and tests, and inspection of one explicitly authorized nonpersonal
  OFF canary. Used the code-review-excellence skill. No live Vault, private tasks,
  held-out prompts, personal answers or credentials were accessed. Sanitized result
  claims were read but not independently regraded.

## Blocking findings

None remain for the corrected harness in the validated local host environment.

The initial review found six issues. The corrected implementation addresses them:

1. **Confinement:** Codex now receives explicit capability disables at process and
   thread creation, checks effective configuration, and inspects the MCP catalog
   before accepting tasks. The nonpersonal canary confirms web search disabled,
   the listed capabilities false, exactly four Aptuni tools, and empty other MCP
   tool/resource catalogs. Its generic answer completes without tool calls. This
   verifies the current environment; it does not retrospectively establish how
   earlier frozen executions were confined.
2. **Initialization cleanup:** configuration is loaded before spawning. Expected
   initialization/RPC failures close the spawned host; the regression checks
   termination and wait. Cleanup errors no longer prevent saving a trial record.
3. **Deadlines:** RPC and turn loops use absolute deadlines and reject expired
   budgets rather than repeatedly consuming buffered events after expiry.
4. **Incomplete trials:** failed or interrupted turns retain their events, elapsed
   time and operational failure. Codex retrieval calls are reconciled by ID from
   start and completion events, including started calls without results.
5. **Setup isolation:** the runner rejects failed setup, substantive setup context
   and observed OFF state following Full activation before submitting an ordinary
   task. Actual response state is required; requesting Full alone does not suffice.
6. **Frozen accounting:** dataset and host must match the run manifest; task IDs and
   experiment fingerprints bind records to the run. Legacy manifests instead bind
   exact original record hashes and disclose their reconstructed origin. Missing
   records remain failures, and automatic accounting does not grade answer success.

## Non-blocking notes and evidence limits

1. **Exact catalog guard, applied during review:** the runner now requires exactly
   the four allowed Aptuni tools, rejects other tools, resources and resource
   templates, and refuses an incomplete paginated catalog. A regression covers
   the allowed catalog, an extra Aptuni tool and an unexpected resource.
2. **Bundle snapshot, applied during review:** the copied bundle's hashes and
   policy content are checked against the manifest before starting task execution.
3. **Historical evidence, disclosed:** the protocol and result report now
   distinguish original-run trace observations from the later confinement canary.
   Reconstructed manifests bind retained records; they do not prove those
   manifests existed before execution. This reviewer did not access those private
   traces, so their independent audit remains evidence supplied by the other
   research reviewers. Preserve these qualifications in future derived reports.

No implementation follow-up remains from these notes and no further review round
is required. The implementing agent owns registration and relay updates.

## Verification and limits

- Focused pytest: **14 passed** across the two development test files.
- Synthetic probes during initial review reproduced constructor cleanup loss,
  expired-deadline acceptance, setup-state contamination and missing started-call
  accounting; remediation tests cover these failure classes.
- The reviewed generic canary shows effective disabled capabilities and the
  expected catalog. It neither activates Full nor retrieves private context.
- Scoped Ruff and whitespace diff checks passed. The initial test-only `SIM117`
  context-manager formatting issue was corrected and lint rerun successfully.

The candidate policy preserves explicit owner activation, existing grants, bounded
retrieval and evidence limits. Neither its text nor this harness review establishes
personalized answer quality. No production schema, ranking, authorization or
provider contract is approved to change here. Keep host/model denominators
separate, preserve failed journeys, and keep b10 closed until its product gate is
actually satisfied.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

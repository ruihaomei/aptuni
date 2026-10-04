# Review 106 — Frozen fresh-six comparison

- **Date:** 2026-10-04.
- **Reviewer:** fresh independent GPT-6 Astra xhigh through the verified Codex CLI0.155.1 route; no implementation authorship.
- **Method:** static supplied-code review. All configured MCP servers and unrelated capability providers were disabled, Code Mode disabled and read-only sandbox selected; native trace has an agent-message item and two error items (disabled Code Mode and shortened skill descriptions), with no observed tool calls. This is observed non-execution, not proof of every possible host capability.
- **Scope:** one proposed12-attempt A/F comparison, existing explicit Full/grant/egress, canonical66. No private prompts, rubric, Vault content, labels, owner configuration or previous answers were supplied. Raw review input/output remain local.
- **Limits:** supplied synthetic/config receipts are lead-observed. The reviewer did not execute tests or inspect live grants. Lead rendered the structured verdict without substantive edits.

The supplied discovery path is consistent with the stated explicit Full/Evidence permissions and excludes SourceConfig inventory. Two concrete driver defects prevent approval of the frozen comparison.

## Blocking findings

- B1 — Missed snapshot-drift stop. In compare_driver.py, sequences() collects only integer vault_seq values, while main() checks top-level operational/cleanup errors and task.result.status. The discovery backend raises research_snapshot_changed as a tool error without a sequence. If setup reported 66, a task retrieval then refuses for drift, and the model turn completes normally, observed remains {66} and operational is false. The driver therefore launches another attempt. Smallest correction: recognize research_snapshot_changed in native MCP error results and terminate scheduling, retaining that case and the unattempted count.
- B2 — Missing denominator receipt on frozen-asset failure. compare_driver.py calls runner.verify_assets(spec) outside exception handling and saves the comparison receipt only after the loops. verify_assets() explicitly raises ValueError on a digest mismatch. A mismatch after completed attempts therefore exits without reporting attempted/unattempted counts. Smallest correction: handle this failure as a terminal, content-free stop and route it through receipt finalization while preserving existing case records.

## Nonblocking observations

- Discovery reloads access under the authorization lock, checks Full state, both scopes, requested modules and informed egress, and filters current exposable Knowledge Evidence and credentials. Labels are bounded opaque-anchor clues; hydration rechecks eligibility and returns canonical Evidence.
- The effect guard is explicitly a scoped Python audit hook. Host capability and MCP catalog checks are present, but live confinement is not established by this static review.
- The declared A per-request allowance versus F's shared 4000-unit cap is an intentional treatment difference. F counts refused retrieval attempts. Compare actual calls, units, refusals, tokens and journey latency without claiming model-only causal equivalence.
- First-five/first-20 coverage, incomplete blinding and the six-task sample remain interpretation limits. Keep the completed development result and prior zero-model failure separately visible; neither changes the fresh comparison's planned denominator.

## Scope and independence

- Correct and re-freeze the driver for review before execution; preserve the locked tasks/rubrics, policy/backend and accepted activation/credential contracts.
- Any subsequent approval covers only one paired six-task comparison: 12 fresh sessions at sequence 66 using the existing Codex grant and model egress, with no retries, retuning or state rebinding.
- No production adoption, release, expanded permissions or owner configuration changes are authorized.
- Independent evidence consists solely of static reasoning over the quoted input. No tools, filesystem execution, network access or private task, rubric, Vault, configuration, label or model-output inspection occurred.
- Validation and freeze receipts are lead-observed reports. I did not independently execute tests, verify hashes or live grants, or witness runtime confinement. No actual comparison has run.

## Frozen identities

- Review input SHA256 `b7c75c586f447d39da03a2b6c520536da5f5f917a2c2160934807b4f7cbf32e6`.
- `docs/dev/b10-continuation/fresh-comparison-protocol.md` SHA256 `8c00cbe589180e150a6c93549f0a5e1936dc9b552b7803bd3ef83b9af1d8bbd8`.
- `tools/agent_e2e_discovery.py` SHA256 `5c14990e1ee5ec88e46f63810a2bd1698045cef191e51cc59f873438dc97bfca`.
- `tools/agent_e2e_run.py` SHA256 `6a6480d1651c3d0f7e38ef1a75fc6ecdaa81b4f1266958f0f0a1a9987d6f8369`.
- `compare_driver.py` SHA256 `43a30d555e1264a55018f352aa67f9dfca6b41e34e537f0b89ab91df5465e23c`.

No fresh-six task was launched. Repair the two driver defects and re-review the concrete bytes. Candidate policy/backend remain unchanged.

**Verdict:** **BLOCK**

# Local E2E architecture research harness

This is disposable research infrastructure, not an Aptuni runtime. It adds no
production dependency, grant, activation rule or model requirement. Reviews 98–99
cover the runner and its corrected MCP bridge in the validated local environment.

Write an owner-only spec in private scratch outside the repository:

```json
{
  "host": "codex",
  "model": "available-role-model",
  "effort": "high",
  "bundle": "/absolute/current/verified/bundle",
  "dataset": "/private/locked-tasks.json",
  "dataset_sha256": "exact-frozen-sha256",
  "policy": "/absolute/frozen/research-policy.md",
  "output_dir": "/private/new-arm-directory",
  "timeout_s": 600
}
```

Use `host=claude` with a verified model and Claude bundle for that host. Omit policy
for current guidance. Model/host roles remain configurable; confirm actual access
with a nonpersonal canary rather than assuming model-catalog availability.

```sh
.venv/bin/python tools/agent_e2e_run.py --spec /private/arm.json --check
.venv/bin/python tools/agent_e2e_run.py --spec /private/arm.json
.venv/bin/python tools/agent_e2e.py --dataset /private/locked-tasks.json \
  --sha256 exact-frozen-sha256 --runs /private/new-arm-directory \
  --host codex --output /private/content-free-counters.json
```

`--check` validates and prints hashes/version metadata without model inference.
Execution refuses to overwrite an arm. It snapshots the generated bundle/policy,
records implementation/runner/model/host identifiers, binds each opaque task record
to the experiment fingerprint, and uses a fresh persistent session per task.
Only a separate explicit owner-authorized Full setup precedes the unchanged ordinary
prompt. Setup failures/disclosure/OFF state prevent task submission. Absolute
timeouts, partial events and operational failures stay in the denominator.

The Codex runner disables inherited apps/plugins/browser/computer/image/shell
capabilities and web search at process/thread creation, verifies effective settings,
and requires exactly four Aptuni MCP tools with no other tool/resource catalog.
Claude uses the exact strict bundle and a limited tool allowlist. Nothing changes
user credentials, global network configuration or VPN state. Input prompts and
native traces stay local, owner-only and outside Git.

Codex 0.155.1 requires `code_mode_host=true` to invoke MCP. The first hardened
runner canary with that bridge disabled failed during setup; no ordinary task was
submitted, and the failed record is retained. The bridge-enabled canary completed
explicit Full setup followed by a generic answer with no task retrieval. Only the
bridge was enabled; capability providers and the four-tool restriction remain.
The installed runtime describes isolated JavaScript without Node, direct filesystem,
network or subprocess access. A nonpersonal inventory canary reported four Aptuni
tools and undefined `process`, `require` and `fetch`, but native app-server events
do not expose its standalone cell output: that final model report is corroboration,
not independently inspected proof of the complete runtime inventory.

Synthetic arms use `tools/agent_e2e_mock.py`, never an owner Workspace. The mock
provides the same four tool names, a knowledge-only fixture, OFF by default, and
two counted task retrieval attempts sharing 4,000 response units. Its catalog arm
adds a research-only exact-anchor seam. Hash the mock and public fixture in optional
`research_assets` spec entries (`path`, `sha256`); the runner verifies them before
freezing and before every task, recording only asset names/hashes in its manifest.
The alternative world's evidence and evaluator rubric are never host instructions.

Accounting separates setup from task, cache creation/read from uncached/output,
and started/unreturned/refused calls. Codex uses cumulative usage minus setup;
Claude uses task-scoped usage. It never grades answer success from retrieval counts.
An independent fixed-rubric evaluator supplies success, justified-retry, context
coverage/precision and answer-grounding judgments. Missing judge/token components
remain unavailable. Compare models/hosts honestly; catalogs/cache tokens and host
configuration differences are part of the measured deployment footprint.

Lock development versus held-out data before choosing arms. Candidate/role changes
consume development data; evaluate a frozen finalist once on the sealed set.
Do not retune on failed held-out tasks and report them as independent afterwards.
Remove this phase's private traces after grading/review and preserve earlier frozen
inputs, prior evidence and owner backups. Commit only inspected content-free output.

`tools/agent_e2e_discovery.py` is a separate, research-only real-data seam, approved
for one original application-task development probe in Review 104. It retains
explicit Full, the existing host grant and informed egress, current exposable
Knowledge Evidence, fixed canonical sequence, two attempts and 4000 aggregate
units. It exposes at most five bounded repository labels, then Evidence for one
copied opaque anchor. It never exports SourceConfig or changes production MCP.
Its scoped Python audit guard is not an OS sandbox. Further experiments require
their own scope and frozen policy; this approval does not cover the sealed six.

The first attempt stopped before model events: the added private bundle `env`
table could not survive the runner's JSON-to-CLI configuration serialization.
Scalar and array overrides parse; dictionary overrides are unsupported. Review
105 approves one launch-only retry using Python `-B` rather than that `env` table.
The failed attempt stays recorded separately, with the candidate and rubric
unchanged. No global owner configuration was altered for this repair.

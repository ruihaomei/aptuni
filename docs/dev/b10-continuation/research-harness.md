# Local E2E architecture research harness

This is disposable research infrastructure, not an Aptuni runtime. It adds no
production dependency, grant, activation rule or model requirement. Review 98
covers the corrected runner in the validated local environment.

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

The Codex runner disables inherited apps/plugins/browser/computer/image/shell/code
capabilities and web search at process/thread creation, verifies effective settings,
and requires exactly four Aptuni MCP tools with no other tool/resource catalog.
Claude uses the exact strict bundle and a limited tool allowlist. Nothing changes
user credentials, global network configuration or VPN state. Input prompts and
native traces stay local, owner-only and outside Git.

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

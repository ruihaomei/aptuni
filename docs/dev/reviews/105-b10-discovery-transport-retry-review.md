# Review 105 — Discovery transport repair and bounded retry

- **Date:** 2026-10-04.
- **Scope:** the unchanged runner's Codex configuration construction, the
  sanitized `transport-repair-validation.json` receipt, and the proposed private
  launch-only repair. Review 104 remains the backend/privacy review.
- **Independence:** this reviewer did not implement the repair. Review used public
  runner/backend code, the specifically authorized sanitized receipt and a local
  synthetic serialization check. No owner configuration, private bundle values,
  Vault, task content, labels or sealed prompts were read. No host/model/backend
  invocation was performed by this reviewer.

## Findings

No blocking defect was found in the proposed repair. The runner parses the bundle
as TOML, takes each Aptuni server field, and supplies each resulting value to Codex
as `-c key=json.dumps(value)`. JSON dictionary syntax is not a TOML inline table.
An invented environment dictionary reproduces that serialization mismatch in
`tomllib`; an argv string array parses successfully. Removing only the private
bundle's `env` dictionary avoids that unsupported value type. Placing `-B` before
the Python backend script retains bytecode-write suppression; the local check
confirmed `sys.dont_write_bytecode` with that flag.

The sanitized receipt reports a successful configuration-only `mcp list --json`
parse, four configured servers and all unrelated servers disabled. It reports no
retry execution and no owner-config, backend, policy, task, rubric, budget or grant
change. This reviewer inspected that receipt rather than reproducing its CLI
check or reading private configuration values. Its aggregate result supports
parsing and configured disablement, not a successful server launch or tool call.

The initial attempt remains an **operational configuration failure**, with zero
model events and zero content calls as recorded in the receipt. Its manifest,
stderr and empty trace must remain retained; it is neither a candidate-quality
failure nor evidence of successful confinement during a model session.

## Frozen identities and retry boundary

Receipt-declared identities, not independently hashed private configuration:

- Repaired bundle configuration:
  `d20ae7c978fbcd613ad4ca3c87e8b10ad65797e18af6f8d40680700c00d0e52e`.
- New retry specification:
  `07f20880a4bf6d19ab986c7460f0f7124047022b1d6b6f6d41ebc1ec495a89c7`.
- Unchanged candidate policy:
  `1b9a8df56e6c0f70e3fa8046ead5311f693e51b2dda5c65ee59ae84424ce5d8a`.

Independently checked public bytes:

- Runner: `6a6480d1651c3d0f7e38ef1a75fc6ecdaa81b4f1266958f0f0a1a9987d6f8369`.
- Backend: `5c14990e1ee5ec88e46f63810a2bd1698045cef191e51cc59f873438dc97bfca`.
- Backend tests after the test-only literal repair:
  `4ef59b425c8c189240d3356004b518717396644ec156dee45d79b858a1e3bc03`.

The credential-filter test now constructs the same invented credential string
from separate literals to avoid the repository scanner treating the test source
as a stored secret. This reviewer verified identical runtime bytes and restored
the previous test-file digest by reversing only that expression change:
`07aa408d542cd4434f0d49304994851716f1c6be0a2704bde185415d8a715021`.
All eight discovery tests passed again. This changes neither test behavior nor
backend bytes; Review 104's historical identity remains unchanged.

Approval covers **one retry of the original m05 development probe** with this
launch-only repair, the same model/task/policy/rubric, existing Codex grant,
explicit Full setup, expected canonical sequence **66**, two task attempts and
shared 4000-unit budget. Review 104's first-five selection, guarded read-only
backend, fresh authorization checks, exact asset freeze and private raw-trace
requirements remain in force. The runner's actual tool-catalog confinement gate
must still pass before the task. A state change must refuse, not silently update
the expected sequence. Any further operational failure is retained and reviewed
separately; this approval does not authorize an indefinite retry loop.

The local synthetic serialization/`-B` checks passed. This review makes no claim
that the pending retry has run or that discovery quality has improved. Production,
new permissions, owner network changes, finalist selection and the sealed holdout
remain outside approval.

**Verdict:** **APPROVE** — ONE FROZEN DEVELOPMENT RETRY ONLY

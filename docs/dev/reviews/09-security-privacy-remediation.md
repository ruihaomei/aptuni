# Fourth Security and Privacy Remediation

- **Date:** 2026-09-18
- **Responds to:** `09-security-privacy-third-rereview.md`
- **Status:** planning changes complete; focused re-review pending
- **Maintainer decision:** on 2026-09-18 the maintainer chose the honest-boundary contract (the
  reviewer's option "state the enforcement boundary exactly" plus control (a) host confinement) over a
  hardware-backed broker, and accepted the residual risk. Recorded in ADR-0013.

| Finding | Remediation |
|---|---|
| B2-R3 broker guards API, not same-user state | ADR-0013 removes the ApprovalBroker from MVP. Confirmation is re-scoped to an accidental-action/MCP-injection guard on the application-service path only; THREAT_MODEL states that unconfined same-user hosts are inside the trust boundary. Control (a): adapters ship a host confinement profile (Codex workspace-write sandbox, Claude Code sandbox + permission rules) denying agent writes to Vault/config/grant/install paths and routing approval subcommands through host approval; `doctor` reports `confined` / `partially_confined` / `not_in_effect`. Out-of-band edits are detected against the hash-chained change log: narrowing honored, widening quarantined (explicitly not a security boundary). S04 tests the profile in the real hosts. |
| Enrollment / trust anchor | No authenticator or enrollment exists in MVP, so there is no anchor to replace. Hardware-backed approval needs a future ADR. |
| H-A test doubles in production | No test authenticator exists. The fake proven-local host and confinement probes live under `tests/`/test-only package; Slice 1 asserts they are absent from wheel/sdist; no env/flag/config selects them or disables the guard (ADR-0013 item 7, plan 01 Slice 7). |
| H-B display integrity / macOS feasibility | Moot for MVP (no broker). The core renders the preview from the canonical action and never displays requester-supplied text (ADR-0013 item 2). |
| N3 deferred effects | Workers recheck grant/epoch before each disclosing effect; revocation or narrowing → `cancelled_policy`; purge continues. Added to THREAT_MODEL, abuse case 9, S04 step 5. |
| N4 fake proven-local path | Test-only placement and artifact assertion as H-A; abuse case 8 updated. Per-session adapter/runtime hash recheck remains the drift definition. |
| N5 wording | "exactly-once" replaced by "exactly one durable intent; effects at least once via idempotent adapters/dedupe keys"; generic "out-of-band/strong/interactive confirmation" terms replaced by ADR-0013 references across THREAT_MODEL, ADR-0005/0010/0011/0012, SPIKES, plans 00–02, graph, roadmap, compatibility. KI-011 updated. |

Verification sweep: `grep -rniE "ApprovalBroker|FIDO|WebAuthn|out-of-band/scoped|interactive flow|strong confirmation|exactly-once" docs AGENTS.md CLAUDE.md`
returns matches only in review history and ADR-0013's own supersession note.

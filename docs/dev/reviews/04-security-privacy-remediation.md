# Second Security and Privacy Remediation

- **Date:** 2026-09-18
- **Responds to:** `04-security-privacy-rereview.md`
- **Status:** planning changes complete; second focused re-review pending

| Finding | Remediation |
|---|---|
| B2-R1 trusted confirmation | THREAT_MODEL/ADR-0005/ADR-0012 choose a core-owned interactive local TTY CLI as sole MVP issuer, unavailable via MCP. Core canonicalizes/displays/applies and atomically consumes an internal nonce with mutation. MCP can only create quarantined pending actions. Observe cannot expose/auto-promote. Tests now assert enforceable authorization properties, not inferred model causality. |
| B4-R1 host-model egress | THREAT_MODEL/ADR-0005/0007 define `host_model_egress`, host operator/destination/retention metadata, strict-local denial to remote/unknown hosts, per-host/module consent, and external-copy inventory. S04/S12 use fake local and declared remote hosts; server canary claims only server coverage. |
| H4-R1 parser output | ADR-0006/0010 classify reconstructive parser output, unknown attributes, parse trees, summaries, and extracted text as full-content retention; bounded structural metadata/excerpts are default. |
| H7-R1 dependency closure | ADR-0002, S02, and Foundation bind approval to manifest plus complete resolved lock/SBOM closure and test transitive artifact drift. |
| M1-R1 raw buffer encryption | ADR-0010/Foundation require OS-backed encryption or encrypted-disk placement; otherwise explicit high-friction warning and no silent enablement, with crash/restart marker tests. |
| M2-R1 purge terminal state | ADR-0010 defines `complete_managed`, `complete_managed_external_action_needed`, and `incomplete_retryable` with per-copy results. |

Independent re-review must verify that MCP cannot reach the issuer and that strict local-only wording
does not promise control over host/vendor copies the project cannot delete.

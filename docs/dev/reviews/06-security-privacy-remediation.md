# Third Security and Privacy Remediation

- **Date:** 2026-09-18
- **Responds to:** `06-security-privacy-second-rereview.md`
- **Status:** planning changes complete; third focused re-review pending

| Finding | Remediation |
|---|---|
| B2-R2 PTY can invoke CLI | THREAT_MODEL/ADR-0005/0012 replace TTY/typed approval with OS/platform or FIDO2/WebAuthn user-verification ApprovalBroker. CLI/MCP/host shell can request but cannot sign. PTY/env/file input never proves presence; unavailable authenticator disables consequential actions with no weak fallback. S04 adversarially allocates a PTY and requires failure while a test UV authenticator succeeds. |
| H1 external atomicity | THREAT_MODEL/ADR-0005/0010 split Vault-only atomic mutation from multi-system actions. The latter atomically consume nonce with exact durable idempotent journal intent; workers/receipts handle effects. S04/Foundation fault concurrent confirmers, pre/post journal commit, effect-before-receipt, restart, retry, and changed digest. |
| M3 proven-local authority | THREAT_MODEL/ADR-0005/S04 make core policy the only admission authority. Claude Code/Codex default remote/unknown; elevation needs reviewed pinned builtin adapter/runtime plus end-to-end model-execution egress evidence. Host/config labels cannot elevate and drift revokes. |

No implementation may substitute a CLI prompt for user-verification merely because CI lacks a real
authenticator; CI must use a test authenticator with equivalent signed challenge semantics.

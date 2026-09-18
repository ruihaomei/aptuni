# Security and Privacy Review Remediation

- **Date:** 2026-09-18
- **Responds to:** `02-security-privacy-review.md`
- **Status:** implemented in planning artifacts; independent re-review pending

No finding is treated as closed until an independent reviewer verifies the referenced changes.

## Blocking findings

| Finding | Planning remediation |
|---|---|
| B1 untrusted content/instruction injection | Added `THREAT_MODEL.md` with end-to-end taint boundary and abuse tests; ADR-0005 forbids source data in instructions/authorization; ADR-0006 carries trust/provenance and hardened parser rules; S04/S05 include injection canaries. |
| B2 MCP caller/authorization/confirmation | ADR-0005 now separates read/write risk classes, configured principals/scopes, exact digest+epoch+expiry+nonce confirmations, replay denial, and policy-mediated resources. S04 tests forged/stale/replay/confused-deputy/race cases. HTTP remains disabled until S21. |
| B3 incomplete retention/destruction | Added ADR-0010 copy inventory, distinct operations, coordinated purge journal/receipt, raw buffer rules, managed backup expiry, restore tombstone, partial-failure recovery, and marker tests. S01 and Foundation plan now carry schemas and restore-after-purge tests. |

## High findings

| Finding | Planning remediation |
|---|---|
| H1 plugin sandbox claim | ADR-0002 and `THREAT_MODEL.md` state in-process plugins are trusted code; activation records package/version/hash/approval and injects narrow ports. S02 proves failure isolation, not containment. |
| H2 parser hardening | ADR-0006 and S05 add root/origin canonicalization, symlink/TOCTOU, secret exclusions, size/time/memory limits, safe XML/archive/document behavior, redirect/pagination/rate-limit tests. |
| H3 credentials/egress | ADR-0007 and threat model add `network_egress`/`credential_use`, local-only deny, destination/data-class grants, secret references, least-scope tokens, and process-wide offline canaries. |
| H4 snapshot minimization/at-rest | ADR-0006/0010 default to hash+locator+parser output+minimum excerpt; full bytes are opt-in. Foundation tests restrictive permissions/ownership and documents plaintext limitations. |
| H5 MCP resources | ADR-0005 limits resources to bounded policy-mediated application views with final hydration/policy recheck; no direct files/indexes. |
| H6 L0 lifecycle | ADR-0008 specifies permission, atomicity, size/allowlist, epoch/invalidation, purge/uninstall. S12 and M1.4 make it a ship gate. |
| H7 supply chain | ROADMAP M1.1 and Foundation Slice 1 move locks, isolated builds, SBOM/license/vulnerability/secret checks, network canaries, and install-time-code review to the first scaffold. |

## Medium and low findings

| Finding | Planning remediation |
|---|---|
| M1 dependency telemetry | ADR-0007 covers transitive egress and destination/schema snapshots on upgrades. |
| M2 diagnostic leakage | ADR-0007/threat model centralize redaction for paths, URLs, headers, environment, exceptions, subprocess output, content, and previewable support bundles. |
| M3 policy races | ADR-0007/0005 use policy epochs, final exposure recheck, atomic invalidation, and forced race tests. |
| M4 restore resurrection | ADR-0010 defines minimal deletion ledger and requires restore-from-pre-purge tests. |
| L1 security ownership | ROADMAP M1.5 requires supported versions, private reporting channel, response owner, and disclosure process. |
| L2 privacy inventory | ADR-0010 and ROADMAP M1.3 require user-visible copy/retention/egress/action inventory. |

## Re-review request

Verify the original checklist against `THREAT_MODEL.md`, ADR-0002/0005/0006/0007/0008/0010,
`SPIKES.md`, `ROADMAP.md`, and plans 00/01. If any contract remains ambiguous, keep the verdict
`BLOCK`; do not accept on intent alone.

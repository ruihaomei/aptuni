# Review 60 — M2 Official Notion MCP Source

**Reviewer:** independent code-review agent

**Date:** 2026-09-23

**Scope:** ADR-0021, exact-scope provider boundary, official hosted MCP/OAuth transport, credential
confinement, locator provenance, partial coverage, crash replay, privacy inventory and CLI

## Findings and remediation

The first pass blocked six issues: the identity call used the wrong tool; SDK tool errors read the
wire alias instead of the Python field; claimed withdrawal was unreachable; URL parsing could pick
an earlier ID from an ambiguous slug; MCP-controlled provenance fields were not fully validated;
and the OAuth/provider boundary lacked production-shaped regressions.

All were remediated test-first. The client now allows only `notion-get-users(self)` plus
`notion-fetch` for exact approved roots, handles real SDK errors, parses only an unambiguous
terminal entity ID, validates principal/parent IDs and timestamps, and explicitly retains prior
Evidence when a root is absent because absence is not proof of deletion. Tests cover the exact
production call sequence, callback state/timeout, refresh storage, disconnect and redaction
failures, malformed/oversized/out-of-scope input, and Notion-specific crash replay.

The second pass found silent coercion of malformed completeness metadata. The parser now requires
exact metadata, entity-type, provenance and boolean/integer completeness types, and rejects an
inconsistent unknown-block count. Eight regressions cover every prior coercion, including Python
booleans masquerading as integers.

## Non-blocking note

- Requiring `unknown_block_count` to equal the returned ID count is deliberately stricter than a
  response that caps its ID list. A very large truncated page therefore fails closed rather than
  becoming a partial snapshot. This is safe under ADR-0021; document a narrower partial rule only
  if a real authorized source demonstrates the capped response.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

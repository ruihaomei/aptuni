# ADR-0021: Ingest explicitly scoped Notion entities through the official hosted MCP server

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** maintainer (fixed priority and privacy constraints) · implementing agent · independent reviewer
- **Builds on:** ADR-0002, ADR-0006, ADR-0007, ADR-0013
- **Needs maintainer confirmation:** no for the bounded provider; yes only to authorize an exact
  real page/database scope for dogfooding

## Context

Notion is a source, not canonical storage. The official hosted Notion MCP server is already the
maintained integration surface; the older self-hosted Notion MCP package is deprecated. Notion MCP
requires interactive OAuth and acts with the connected user's permissions, which are much broader
than any one Aptuni source scope. Discovery therefore cannot be treated as ingestion consent.

## Decision

Use only `https://mcp.notion.com/mcp` through the already locked official Python MCP SDK. Aptuni
registers as its own OAuth/PKCE client and keeps tokens in the operating-system credential store;
tokens never enter canonical or derived Aptuni files. The provider calls only the official
`notion-get-users` tool for the connected `self` principal and `notion-fetch` for exact
owner-approved entity URLs. It never uses search or workspace-browsing tools during sync and
exposes no Notion write operation.

The approved root set is immutable `SourceConfig` policy. Stable Notion entity IDs drive identity.
`notion.locator@1` preserves bounded page/database provenance; raw MCP results and full block bodies
are discarded after producing a minimized excerpt and content hash. Each root is independently
bounded. Any truncation, unknown block, schema drift, incomplete root set, auth loss or resource
overrun fails closed or yields partial coverage, never an inferred deletion. The first slice has
no remote-deletion signal: a missing root retains prior Evidence until explicit unlink or purge.

## Consequences

- The official MCP remains replaceable behind Aptuni's source boundary; the Vault and common source
  contract do not depend on Notion.
- Initial connection requires interactive OAuth. Subsequent sync may refresh through the same MCP
  client without exposing credentials to Aptuni records.
- The first slice deliberately does not recursively discover descendants or scan a workspace.
  Additional scopes and event-driven incrementality require separate evidence and an amendment.

## Verification

Test exact scope, official endpoint/tool allowlist, stable identity, edit/no-op/missing-root retention,
truncation and unknown blocks, prompt/control-byte injection, OAuth state/timeout/refresh, credential
non-retention, purge/privacy inventory, crash replay and backward-compatible Vault reads.

## Amendment — 2026-09-24 real activation

Official page creation returned an `https://app.notion.com/...?...pvs=204` URL. Treat one numeric
`pvs` parameter as a non-authoritative sharing hint, discard it during stable-ID canonicalization,
and continue rejecting every other, duplicate, malformed or credential-bearing query parameter.
This is URL compatibility only: the immutable exact entity-ID scope and fetch-only provider
contract do not change. Aptuni's OAuth/PKCE client remains deliberately separate from host-agent
Notion connectors; authentication in one credential boundary is not evidence that the other has a
usable session. Review 64 independently approves the compatibility change.

## Amendment — 2026-09-25 official result envelope and completeness

The official server currently returns page bodies inside an enhanced-markdown envelope and omits
`truncated`, `unknown_block_ids` and `unknown_block_count`. Aptuni extracts only the body of exactly
one ordered `<content>…</content>` envelope and rejects duplicate, unbalanced or reversed envelopes.
When all completeness keys are absent the result is accepted but completeness is **unverified**:
snapshot coverage is `partial` with note `notion_completeness_unverified`, so the observed page still
updates Evidence while nothing is ever recorded as fully observed. If any completeness key is
present, `truncated` and `unknown_block_ids` must both be present and valid, and
`unknown_block_count`, if present, must equal the list length. Absent metadata is never evidence of
completeness.
Review 65 blocked the first activation parser that treated absence as completeness; this amendment
records the remediation.

## Amendment — 2026-09-25 persisted access-token expiry

MCP SDK 2.2.0 reloads stored tokens without their expiry, so a later process treated a stale access
token as valid and answered the resulting 401 with a full browser authorization instead of the
refresh grant. Real dogfooding hit this one day after authorization. Aptuni now stores an absolute
`tokens_expire_at` beside the tokens inside the same Keychain item and restores it when its OAuth
provider initializes, so an expired session silently uses the stored refresh token against the
official token endpoint. The stored expiry is 60 seconds early to absorb latency and clock skew;
a legacy or invalid stored expiry is treated as already expired (refresh first), while a token the
server issued without `expires_in` stays non-expiring. Tokens, client and expiry come from one
Keychain read. A failed refresh still ends in the non-interactive `notion_auth_required` error. No
credential leaves Keychain, and the fetch-only tool allowlist is unchanged. SDK OAuth diagnostics
are routed to a null handler and transport task-group errors are unwrapped, so the owner sees the
bounded Aptuni message rather than a traceback; an interrupt, exit or cancellation raised beside an
Aptuni error is never masked. Review 67 approves.

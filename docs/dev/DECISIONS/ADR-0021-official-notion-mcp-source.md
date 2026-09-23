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

# M2 Official Notion MCP Source — bounded TDD plan

## Outcome

Add one explicitly scoped Notion `SourceProvider` whose only production transport is Notion's
hosted MCP endpoint. Aptuni never receives a Notion API token and never searches an entire
workspace. The owner approves exact page/database URLs before any content fetch.

## Contract

- `aptuni source add-notion URL...` stores only normalized exact Notion entity IDs/URLs and module/
  authority policy. Discovery and the authenticated workspace connection do not grant ingestion.
- `aptuni source connect-notion` performs the official OAuth/PKCE flow through the locked
  Python MCP SDK and stores credentials only in the host credential store. No token enters the
  Vault, state directory, logs, fixtures, backup or repository.
- Ordinary `aptuni sync SOURCE_ID` calls `notion-get-users` only for the connected `self` principal,
  then `notion-fetch` for the approved roots. It does not call workspace search, recent pages,
  favorites, private/shared-page listing, or write tools.
- Stable Notion page/database IDs are canonical source identity. `notion.locator@1` retains the
  principal ID, entity ID/type, validated parent ID when supplied, canonical URL and normalized
  last-edited timestamp.
  Evidence retains only a bounded plain-text excerpt and hash; block bodies and raw MCP responses
  are never persisted.
- The first slice never treats absence as proof of remote deletion. Any missing, truncated, unknown,
  oversized, unauthenticated or schema-unknown response makes coverage partial or fails closed;
  prior Evidence remains until explicit source unlink or purge.

## Red → green sequence

1. Admission tests: exact supported URLs/IDs only, duplicate scope rejected, no empty or workspace-
   wide scope, no token/reference fields.
2. Provider tests: stable ID, no-op replay, edit, missing/truncated/unknown response, control-byte
   and prompt-injection minimization, count/size bounds, exact approved-root calls only.
3. Application/CLI tests: add → login-required sync; injected authenticated MCP fixture → sync →
   Evidence; crash replay; module and purge gates.
4. Credential/OAuth tests: official endpoint pinned, PKCE SDK path, host credential-store-only,
   callback state/timeout, refresh, disconnect, and token-redaction failures.
5. Plugin/i18n/docs tests and one real explicit-page dogfood only after the maintainer supplies or
   selects an exact page scope.

## Gates

Run focused provider/CLI/privacy tests during implementation, then full pytest, Ruff, strict mypy,
relay, supply-chain checks and frozen evaluations. Because this adds a public locator/provider and
OAuth/privacy boundary, obtain independent review before checkpointing.

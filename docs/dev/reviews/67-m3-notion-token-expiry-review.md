# Review 67 — Notion Persisted Access-Token Expiry

**Date:** 2026-09-25
**Scope:** `MacKeychainTokenStorage` expiry persistence, `_PersistedExpiryOAuthProvider`,
`_run_bounded` task-group unwrapping and the SDK auth-log null handler in
`src/aptuni/application/notion_mcp.py`; tests; ADR-0021 2026-09-25 expiry amendment
**Reviewer:** independent agent (`code-reviewer`)
**Trigger:** the second real dogfood issue — a day after authorization, sync demanded browser
re-authorization and printed an SDK traceback, although a valid refresh token was stored

## Findings

No blocking finding. Credentials stay inside the one Keychain item; the refresh URL derives only from
the pinned official endpoint (a tampered stored issuer still refreshed against
`https://mcp.notion.com/token`); a simulated 400 refresh ended in `notion_auth_required` with no
browser redirect and no Keychain write; `_run_bounded` never returns on error; the SDK pin
(`mcp==2.2.0`, `uv.lock`) protects the private override, and two tests fail when it is removed.

Non-blocking notes applied: an interrupt/exit/cancellation beside an Aptuni error is re-raised as
the group (N1); tokens, client and expiry come from one Keychain read (N3); a 60-second expiry
margin (N4); overflow-safe expiry parsing (N5); precise ADR wording (N7); constant grouping.
Deferred to `BACKLOG.md`: a provider-level failed-refresh test (N2), the streamable-HTTP transport
logger (N6), and pre-existing issuer-mismatch re-registration.

## Verification

- Focused Notion suites: 62 passed before and 65 passed after the note fixes, 15 subtests.
- Full gate: 767 passed, 3 optional skips, 62 subtests; Ruff, strict mypy, relay and frozen
  evaluation green.
- Live: the owner's expired session refreshed silently and the exact-root re-sync was a no-op.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

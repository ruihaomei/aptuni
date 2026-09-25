# Review 68 — Notion Native Credential Hardening and Envelope Parsing

**Date:** 2026-09-25
**Scope:** closure of Review 65 N2–N5 and Review 67 N2 in `src/aptuni/application/notion_mcp.py`:
line-based `<content>` envelope parsing, declared ctypes signatures for every Security/CoreFoundation
call, content freeing and a 64 KiB bound on reads, explicit delete-failure semantics, native and
provider-level regressions; ADR-0021 amendments, KI-022, BACKLOG and CHANGELOG
**Reviewer:** independent agent (`code-reviewer`)

## Findings

No blocking finding. Every declared signature matches its framework prototype; embedded-NUL secrets
pass through `c_char_p` with explicit lengths; content is freed on every path and items are
released; no secret reaches argv, logs or exception text. `disconnect-notion` can no longer report a
credential as removed after Keychain refused the delete. The envelope parser fails closed for
reversed, open-only, close-only, inline-only, trailing-content and non-LF-separator shapes, keeps
page-quoted markers as body text, and cannot fake completeness because completeness comes from JSON
keys. Ten new tests fail on the previous code; the duplicate-race and failed-refresh tests are
regression guards (the implementer also showed the failed-refresh test fails with the expiry
override removed).

Non-blocking notes applied: a matching 64 KiB bound on write (a larger blob would have been saved
and then refused on every read); CRLF, whitespace-only-line and lone-close parser tests; distinct
`disconnect-notion` text when no credential existed, with CLI regressions. Deferred to `BACKLOG.md`:
tightening pass-through of non-enveloped results (notes 1–2), which needs the real server's
non-enveloped shapes first.

## Verification

- Focused Notion and privacy suites: 101 passed, 15 subtests (reviewer); 86 passed after note fixes.
- Real Security.framework on arm64, throwaway services only: add, read, NUL-byte modify, oversize
  rejection, delete, second delete `False`, final absence confirmed by `security`.
- Ruff and strict mypy clean.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

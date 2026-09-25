# Review 65 — M3 Notion Activation Delta (Keychain, envelope, completeness)

**Date:** 2026-09-25
**Scope:** the uncommitted real-activation delta beyond Review 64's `pvs` URL fix:
native ctypes Keychain storage, the enhanced-markdown `<content>` envelope and completeness
metadata parsing in `src/aptuni/application/notion_mcp.py`, coverage in `src/aptuni/sources/notion.py`,
and their tests
**Reviewer:** independent agent (`code-reviewer`), two passes
**Prior contract:** ADR-0021, Reviews 60 and 64

## First pass — BLOCK

- **B1 (blocking, fail-open).** When the official server omitted all three completeness keys, the
  parser set `truncated=False` and no unknown blocks, so `scan_notion` recorded `complete` coverage.
  The live server always omits them, so every real sync would have claimed completeness, against
  ADR-0021's fail-closed/partial clause, without an amendment.
- **N1.** A reversed `</content>…<content>` pair raised a raw `ValueError` rather than
  `notion_mcp_result_invalid` (still fail-closed, misleading message).
- **N2–N5 (non-blocking).** Line-based envelope parsing for pages that quote the marker; ctypes
  `argtypes`; Keychain free/length/delete-failure hardening; extra native Keychain tests. The
  Keychain port itself was judged memory-safe with correct buffer lifetimes, releases, duplicate
  race handling and non-macOS gating, and the secret never reaches argv, a TTY or logs.

## Remediation

`NotionEntity.completeness_verified` defaults to `False`; only explicit valid metadata sets it.
Unverified entities are unsafe, so coverage is `partial` with `notion_completeness_unverified`,
while observed pages still add/modify Evidence and prior Evidence is never withdrawn. Envelope
misuse raises `notion_mcp_result_invalid`. ADR-0021 gained a 2026-09-25 amendment. N2–N5 and the
inline `<unknown/>` counting recommendation are recorded in `BACKLOG.md`.

## Second pass — approve

All five checks passed: fail-closed default with one production construction site; partial
coverage still records observed pages and never removes Evidence; partial keys fail closed;
reversed/duplicate/unbalanced envelopes fail closed; the amendment matches behaviour. Three
non-blocking notes (ADR wording for the optional `unknown_block_count`, the integration helper
masking the missing-root case, a lone-key regression) were applied directly.

## Verification

- Focused Notion suites: 47 passed, 15 subtests.
- Full gate before the note fixes: 746 passed, 3 optional skips, 62 subtests; Ruff, strict mypy,
  relay and frozen evaluation green.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

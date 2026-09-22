# Milestone 2 GitHub Deep TDD Plan

**Status:** Accepted (2026-09-22)
**Owner:** single owner for the public source/locator contract; independent review before exit.
**Contract:** ADR-0006, ADR-0019, GitHub Standard checkpoint `0190cf6`, Review 18.

## Objective and fixed scope

Add a read-only, repository-local authored-activity source: commits authored, pull requests opened,
and reviews given by one explicitly configured GitHub actor. Standard continues to describe the
repository tree and is never replaced. This plan does not read issue/discussion threads,
full-history file lifecycle, cross-repository account signals, diffs, bodies, comments, email or
profile data.

## Bounds fixed before implementation

- Actor token: explicit, 1–64 safe login characters; never inferred.
- Per JSON response: at most 2,000,000 bytes through the existing exact-origin redirect/rate-limit
  transport.
- Commits: 100/page, at most 5 pages and 500 admitted items. The configured ref bounds the history
  when present. A full fifth page is partial.
- Opened PR search: 100/page, at most 5 pages and 500 items; `incomplete_results`, GitHub's search
  ceiling, or a full fifth page is partial.
- Reviews: search at most 100 candidate PRs; list at most 2 pages/PR and 500 admitted reviews, with
  at most 100 review-list requests. Any exhausted bound is partial.
- Stored text: commit subject or PR title only, whitespace-normalized, sanitized and clipped so the
  Evidence excerpt stays within 280 characters. Review bodies and PR bodies are dropped.
- Any rate-limit signal, malformed identity, duplicate stable key, unsafe token or response overrun
  aborts without canonical or source-state change.

## Slice A — Explicit Deep source plus authored commits

1. Failing config tests: `--deep-actor` is exact and round-trips in roots; missing/invalid actors
   fail before network; Standard roots remain byte-for-byte unchanged.
2. Failing API tests: query commits with exact actor/ref and explicit pagination; admit only exact
   linked `author.login`; unlinked/mismatched authors are skipped with partial coverage; malformed
   identity, duplicates, rate limits, fifth-page and byte caps fail/mark partial as specified.
3. Failing source tests: `github_deep` sync creates minimized `github.activity@1` Evidence, no blob
   fetch occurs, repeat sync is a no-op, a complete changed history withdraws, partial history never
   withdraws, and crash replay is idempotent.
4. CLI smoke: `aptuni source add-github ... --deep-actor LOGIN` prints/returns a distinct approved
   Deep source and ordinary `aptuni sync` makes authored-commit evidence searchable.

## Slice B — Pull requests opened

5. Search only `repo:OWNER/REPO is:pr author:ACTOR`; verify every returned item is a PR authored by
   the exact actor and belongs to the configured repository.
6. Persist number, stable node/database id, created time, state and bounded sanitized title; drop
   body, labels, assignees, comments and other user fields.
7. Regress pagination/incomplete-result/duplicate/injection behavior and coexistence with commits.

## Slice C — Reviews given

8. Search only `repo:OWNER/REPO is:pr reviewed-by:ACTOR`, then enumerate reviews for bounded matched
   PRs and keep only exact `user.login == ACTOR` submitted reviews.
9. Persist review id, PR number, submitted time and normalized state. Drop body, inline comments,
   requested-review state and other reviewers. Pending reviews without `submitted_at` are skipped.
10. Regress per-PR pages, total requests/items, duplicate review ids, injection, rate limit and
    partial-withdrawal behavior.

## Cross-slice gates

11. Literal ESC/newline/NUL fixtures prove actor/title/state cannot forge owner rows or locator
    fields. Every stored outside-controlled token uses `sanitize_token`; owner rendering uses
    `delimited_untrusted` through the existing evidence surface.
12. GitHub Standard unit/integration suite remains unchanged and green. Deep never calls
    `fetch_blob`, tree, diff, issue/discussion, account-event or cross-repository endpoints.
13. Exact repository id is stable across all lanes; a change aborts. Module ingest/expose remain
    independent; privacy purge and source-state replay require no special path.

## Verification

```sh
.tools/bin/uv run --no-sync pytest tests/unit/sources/test_github_api.py \
  tests/integration/test_github_sync.py
.tools/bin/uv run --no-sync pytest
.tools/bin/uv run --no-sync ruff check . && .tools/bin/uv run --no-sync mypy src
python3.13 tools/check_relay.py
python3.13 tools/check_supply_chain.py notices
python3.13 tools/check_supply_chain.py secrets
python3.13 tools/check_supply_chain.py workflow
```

## Exit

Complete when all three included authored-activity lanes are runnable from one explicit Deep source,
large or incomplete histories never create false withdrawals, no excluded content is retained, the
Standard source remains unchanged, independent review has no blocking correctness/security/contract
finding, and durable state records exact limitations and gate evidence.

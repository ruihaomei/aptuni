# ADR-0019: Model GitHub Deep as an additive authored-activity source

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** maintainer (scope fixed in the M2 roadmap) · implementing agent
- **PRD refs:** §8–§10, §22–§23, §35, §48
- **Extends:** ADR-0006 and GitHub Standard; it does not replace either
- **Needs maintainer confirmation:** no — the roadmap already fixes the included and excluded activity

## Context

GitHub Standard describes what a repository contains by selecting bounded blobs from one resolved
tree. It cannot distinguish repository contents from the work the owner personally contributed.
The M2 roadmap fixes Deep mode to three repository-local activity classes: commits authored, pull
requests opened, and reviews given. Issue/discussion threads, full-history file lifecycle, and
cross-repository account signals are explicitly outside this decision.

Repository ownership is not author identity: a personal repository can contain other authors, and
an organization repository can contain the owner's work. Guessing from the repository slug or a Git
email would create false personal evidence.

## Decision

1. Deep is a separate additive `github_deep` SourceConfig over the same exact repository/API origin
   contract as Standard. Standard remains independently runnable and unchanged. Deep never fetches
   repository blobs or diffs.
2. Configuration requires one explicit GitHub actor login. The actor is stored as a bounded config
   token and compared case-insensitively with the API's linked `user.login`; Aptuni never infers
   authorship from an email, display name, repository owner, committer, mention, or reviewer request.
3. `github.activity@1` is a new locator extension. Its stable key is `activity_key`; required fields
   are repository id, actor, activity kind/id, occurrence time, and mode. Optional bounded metadata
   names a commit SHA or pull-request number, state and a sanitized title. Review bodies, PR bodies,
   diffs, issue comments, emails, profile data and unrelated actors are never persisted.
4. Deep is read-only and emits minimized Evidence through the existing snapshot/delta, delivery,
   crash-replay, retention, module-policy and purge paths. Evidence means exposure to authored work;
   it never implies skill, mastery, agreement, or truth.
5. Every activity lane is independently paginated and bounded. A rate-limit signal stops the whole
   sync safely. Exhausting a page/item/request/byte bound makes coverage `partial`, so absence never
   retracts older evidence. A complete traversal may propose withdrawals through the normal source
   contract. Outside-controlled tokens are sanitized before canonical storage.
6. The implementation order is authored commits, opened pull requests, then submitted reviews.
   Each lands as a runnable vertical slice; later lanes extend the same source and locator contract.

## Consequences

- **Positive:** Aptuni can represent the owner's actual contribution without conflating repository
  contents, committers, requested reviews, issue participation or account-wide activity.
- **Negative:** public activity with an unlinked author cannot be attributed and is skipped; large
  histories become partial and cannot prove deletion; review discovery needs bounded PR search plus
  per-PR review enumeration.
- **Compatibility:** existing `github` configs, locators, snapshots and evidence are untouched.
  `github_deep` and `github.activity@1` are additive public contracts.

## Verification

Exact-actor configuration and round-trip; no-email/display-name/slug attribution; response-size,
pagination, item and request caps; rate-limit and malformed-result fail-closed cases; literal control
bytes in actor/title/state fixtures; partial coverage at every truncation boundary; stable no-op,
add/change/withdraw and crash/replay; no blob/diff/body/comment fetch; Standard behavior unchanged.

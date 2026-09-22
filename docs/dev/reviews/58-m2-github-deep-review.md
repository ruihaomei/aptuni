# Review 58 — M2 GitHub Deep authored activity

**Reviewer:** independent Codex subagent

## Scope and evidence

Reviewed the uncommitted GitHub Deep implementation against `AGENTS.md`, ADR-0006, ADR-0019,
the accepted TDD plan, and the fixed roadmap scope. The review covered the additive source/config
contract, `github.activity@1`, exact repository and actor admission, all three pagination lanes,
partial-coverage reconciliation, minimized Evidence, state recovery, and the focused tests.

Focused verification is green:

```text
.tools/bin/uv run --no-sync pytest tests/unit/sources/test_github_api.py \
  tests/integration/test_github_sync.py tests/unit/sources/test_contract.py -q
All focused cases passed (64 test functions plus parametrized cases)

.tools/bin/uv run --no-sync ruff check <modified source and focused tests>
All checks passed!

.tools/bin/uv run --no-sync mypy src
Success: no issues found in 74 source files
```

Several important properties held under inspection. Deep is additive and Standard's path remains
unchanged. One repository request feeds all three lanes, actor attribution uses only the exact linked
login with case-insensitive comparison, search results are rechecked for actor and repository, and
review requests retain only submitted reviews by that actor. The combined batch is partial if any
lane is partial, so an incomplete lane cannot withdraw evidence from another lane. The source-state
journal and deterministic Evidence ids correctly reuse the generic crash/replay path. Bodies,
comments, diffs, email, commit bodies, unrelated-user records, and repository blobs are not copied
into snapshots or Evidence.

## Initial blocking issues and remediation

### B1 — Malformed repository identity is admitted as canonical locator identity

`GitHubApi._repository` (`src/aptuni/sources/github.py:267-277`) validates the repository id with
`isinstance(repository_id, int)`. In Python, `bool` is an `int`, and the code also admits zero and
negative values. `scan_github_activity` (`:823-860`) independently accepts such a batch without an
identity-shape check. A direct probe produced a complete snapshot whose public locator contains
`"repository_id": true`; on a later sync, Python also considers `True == 1`, so the exact-identity
comparison can alias two malformed identities.

This violates the plan's malformed-identity fail-closed gate and weakens the repository-id boundary
on which withdrawals depend. It is not merely a typing nit: the malformed value is persisted in the
source snapshot/locator and can become the identity baseline for later complete withdrawals.

**Required fix:** require `type(repository_id) is int and repository_id > 0` at the API response
boundary and enforce the same invariant in `scan_github_activity` before reconciliation. Add
regressions for boolean, zero, and negative repository ids proving that no canonical record or source
state changes. The public locator gate should also validate this value invariant rather than only the
presence of the field if locators can arrive from any provider boundary.

**Disposition: closed on re-review.** `_repository` now requires an exact positive `int`,
`scan_github_activity` repeats the invariant before reconciliation, and the `github.activity@1`
extension gate rejects malformed durable locators. Unit tests cover `True`, zero and negative values
at the API and scan boundaries; the extension-contract test covers the same values; and the
integration test starts from a committed Deep state and proves each malformed identity changes
neither current Evidence nor the source-state bytes.

### B2 — `github.activity@1` persists an undeclared locator field

ADR-0019 §3 fixes the public extension: required activity/repository/actor/time/mode identity plus
optional commit SHA or PR number, state, and sanitized title. The implementation registers
`owner_name` as another optional field (`src/aptuni/sources/extensions.py:91-98`) and injects it into
every activity locator (`src/aptuni/sources/github.py:838-841`). The probe above confirms it is
persisted. Repository name is already represented by the approved SourceConfig root and is not
needed for activity identity or Evidence rendering.

This is a silent expansion of an explicitly versioned public locator contract and retained metadata,
which AGENTS.md requires to be settled rather than introduced incidentally. It also contradicts the
TDD plan's field-by-field minimized persistence lists for PRs and reviews.

**Required fix:** remove `owner_name` from `github.activity@1` and from activity snapshot fields, or
make a deliberate contract decision before changing the accepted ADR. The fixed scope and current
implementation do not need it, so removal is the bounded remedy. Add a serialized locator assertion
that enumerates the exact allowed fields for each of commit, PR, and review activity.

**Disposition: closed on re-review.** `owner_name` is absent from the registered optional set and
from `scan_github_activity`. The integration test now enumerates the exact serialized locator keys
for commit, PR, and review Evidence, matching ADR-0019's required fields and the lane-specific
optional metadata exactly.

### B3 — Required pagination and overrun boundaries have no executable regression

The accepted plan requires partial coverage at every truncation boundary and explicit tests for PR
pagination, review candidate/request/item caps, response overrun, and late rate limiting. The current
suite covers the commit fifth-page cap, PR `incomplete_results`, and the two-page per-PR review cap,
but contains no test that reaches:

- a full fifth PR-search page / 500-item boundary;
- the 100 review-candidate boundary;
- the 100 review-list-request boundary;
- the 500 admitted-review boundary;
- a Deep response exceeding 2,000,000 bytes; or
- a rate-limit failure after an earlier Deep lane has already produced in-memory results.

The production loops appear conservative by inspection, but these are milestone-exit gates, not
optional coverage, and they protect exactly the condition that distinguishes safe retention from a
false withdrawal. A small off-by-one change at any of these sites could turn a bounded partial scan
into complete coverage and retract older Evidence.

**Required fix:** add failing-first boundary fixtures for each item above. Each exhausted cap must
assert `complete is False` and then reconcile against a previous item to prove no remove operation;
byte/rate-limit failures must assert the sync leaves both canonical records and source state
unchanged. Include the first value below the cap so the tests pin the boundary rather than merely a
generic partial result.

**Disposition: closed on re-review.** The remediated suite executes 499 versus 500 opened PRs, 99
versus 100 review candidates, the 100th review-list request, and 499 versus 500 admitted reviews.
Every at-cap result is asserted partial and is reconciled against prior activity to prove that no
remove operation is emitted. The late-provider-failure integration test first returns an authored
commit and then injects either a rate-limit response or a response-overrun error on the subsequent
PR lane; both paths prove canonical Evidence and the persisted source-state bytes remain identical.
The tests also assert the 2,000,000-byte Deep limit is passed to the transport. Production
`UrllibGitHubTransport` performs the actual `max_bytes + 1` read and raises
`github_response_too_large`, so the integration fixture correctly tests the application-level
all-or-nothing consequence without allocating the oversized response through a real socket.

## Warnings and non-blocking suggestions

### W1 — Multi-page search consistency is trusted rather than checked

`_search_pull_requests` overwrites `total_count` on every page and checks only the last response
against the accumulated items. GitHub search is not a snapshot, so a count change during traversal
can otherwise make a short later page appear complete and permit withdrawals. Preserve the first or
maximum count and mark coverage partial when page counts disagree or when that count exceeds the
accumulated result. The same general race exists for branch-name commit pagination; resolving a
configured/default ref to an immutable SHA before walking pages would align Deep commits with
ADR-0006's immutable-snapshot model. This is non-blocking for the current bounded contract because
ADR-0019 did not prescribe a pagination consistency token, but it is the main residual false-absence
risk.

**Disposition: count-change part fixed.** `_search_pull_requests` now retains the maximum observed
count, marks a changed count partial, and compares that conservative count with accumulated results;
the new two-page regression pins the behavior. Resolving a branch name to an immutable commit SHA
remains a future hardening option rather than a defect in the accepted Deep contract.

### W2 — The Deep CLI acknowledgement does not echo the actor

The non-JSON success line says only that a Deep source was approved and prints the repository URL.
Echoing the sanitized configured actor would make an accidental wrong-account configuration visible
at creation time. The actor is preserved correctly in roots and JSON, so this is a UX hardening note,
not a contract failure.

**Disposition: fixed.** The human success line now renders the configured actor through
`delimited_untrusted`, and the CLI integration test requires it.

### W3 — Response-overrun detection is split across unit boundaries

The late-failure integration fixture synthesizes `github_response_too_large` after asserting that
the Deep request carries the 2,000,000-byte bound; it does not directly instantiate
`UrllibGitHubTransport` with a mocked `urlopen` response of 2,000,001 bytes. The production transport
implementation is straightforward and shared with Standard (`read(max_bytes + 1)`, then reject), and
the new integration test proves no durable change after that fixed error, so this is not blocking.
A direct transport regression would make the byte boundary entirely mutation-resistant.

## Overall judgment

The architectural direction and core reconciliation behavior are sound, and focused checks pass.
B1–B3 are closed: identity is exact at every boundary, the public locator matches ADR-0019, and the
pagination/request/item/late-failure transitions now have executable below-cap and at-cap evidence
including partial-withdrawal protection. Both earlier warnings were addressed. The remaining direct
transport-test suggestion does not change the verified production behavior or the source's durable
failure semantics.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTE**

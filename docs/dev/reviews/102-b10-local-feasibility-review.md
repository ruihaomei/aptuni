# Review 102 — Local discovery feasibility report and scoped guard

- **Date:** 2026-10-04.
- **Scope:** `docs/dev/b10-continuation/discovery-feasibility-results.md`, the
  retained aggregate result, and static inspection of the retained diagnostic
  script. The reviewer authored neither the script nor the report.
- **Method:** read the report and aggregate JSON, inspect the script without
  executing or importing it, compare numeric/boolean claims and verify digests.
  No Vault, source labels, source configuration, oracle response or held-out
  prompts were accessed. No model inference or live diagnostic was run.

## Blocking findings

None for retaining this scoped aggregate report and its rejection of the current
catalog design. This is not approval of production discovery or a general
sandbox, and it does not independently certify that the live execution occurred
exactly as reported.

## Result consistency

The retained aggregate matches the report: sequence 62; 26,999 eligible knowledge
Evidence records; 456 records linked through admitted locator/concept metadata;
11 groups and 11 distinct labels; zero conflicting-label groups; five selected
entries; and the prior oracle group included in that fixed selection.

The packing result is 32 units, `truncated=true`, and no returned catalog item.
The script constructs one ContextUnit containing the full five-entry JSON, then
uses the existing `pack_units(..., 800)`. This supports rejection of that whole
item at the stated budget. It does not support absence of repositories, useful
coverage, a different ranking rule or a larger disclosure budget.

The aggregate reports a previously obtained oracle response at 1036 units, which
is below 3200; this is a size observation, not a new evidence lookup or an
independent assessment of its relevance or authorship support. Elapsed time
6.072873500001151 seconds agrees with the report's 6.073-second rounding.

The five-entry selection is computed from lexicographically sorted repository
anchor strings before oracle membership is checked. The oracle is used to
measure inclusion; it does not alter selection in this script. The script
validates the locator label shape and uses the repository-name suffix as its
display label. It does not inspect SourceConfig fields for discovery; the
report correctly distinguishes this from normal snapshot deserialization.

## Static scope and safeguards

The inspected path opens the existing authorization-lock inode read-only with
`O_NOFOLLOW`, holds its lock through authorization, snapshot inspection and
result export, and checks both context-read and evidence-read access to the
knowledge module. It requires an enabled Full setup with no returned items.
It filters `records.exposable()` to knowledge Evidence, excludes detected
credential-bearing records and labels, restricts locator schema names, and
validates repository identifiers and label form before grouping.

The script's audit hook precedes service construction and live activation. For
the operations it intercepts, it refuses writes outside the private scratch
area except the two specified host-local lock paths; it rejects non-read-only
shared SQLite connections, protected removal/rename/link operations, subprocess
launch and socket connect/bind. Existing lock maintenance is an explicit allowed
effect, so “read-only” does not mean that absolutely no host-local writes occur.
The code has no recovery or projection-write fallback when the guard refuses an
operation. Exceptions produce a fixed failure flag and exception type rather
than a traceback or source values.

The final snapshot sequence must equal the first before export. Result fields
are a fixed aggregate allowlist: counts, booleans, sequence, units, elapsed time
and fixed descriptive strings. The result file uses exclusive creation and
private permissions. No repository identifiers, labels, excerpts or source
configuration values are written by that result construction.

These observations concern this inspected trusted script. Python audit hooks
are not demonstrated here to confine arbitrary hostile code or every filesystem,
network or process primitive. This reviewer did not inspect transitive service
implementations, run adversarial sandbox tests, witness the prior self-checks,
or verify before/after filesystem state. The report already limits its claim to
the bounded diagnostic; preserve that limitation.

## Evidence identity and non-blocking note

- Script SHA-256, verified against the report:
  `2959bed1bfad90f1f2154c7ff5d68ae27df712bdf944ca8143b306e1b5b757a3`.
- Aggregate result SHA-256 observed by this reviewer:
  `496ecaca378e871617587756d045a2bb5a26daf761428b28177fd4e97ae658e7`.
- **N1 — execution attestation is limited:** the result does not embed its script
  digest or a self-check receipt. The reviewed script contains the three stated
  guard self-checks, but this review did not receive or execute their output.
  Accordingly, numeric consistency and static safeguards are independently
  reviewed here; the chronology and live-execution account remain attributed to
  the executing agent and earlier scoped reviewer. For a future run, bind these
  artifacts in a content-free execution manifest rather than strengthening this
  report into an independent live-execution claim. No new live run is required
  merely to retain the current negative feasibility result.

No budget, ordering, grant, activation, production interface or canonical
contract change is approved. The result supports stopping the current catalog
design, with any new serializer treated as a separately frozen research proposal.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

# Review 100 — Synthetic discovery experiment boundary

- **Date:** 2026-10-03
- **Scope:** `tools/agent_e2e_mock.py`, `tests/dev/test_agent_e2e_mock.py`, the public
  `synthetic-discovery-probe.json` fixture and the runner's optional research-asset
  digest checks. Review 99 separately covers the Codex bridge exception.
- **Method:** scoped source review, public fixture inspection, focused synthetic
  tests including real STDIO, and lint. No sealed tasks, private evidence, owner
  Workspace, live Vault or installed permission records were accessed.

## Blocking findings

None remain in the reviewed synthetic harness.

**Asset freeze gap, corrected before candidate execution.** Bundle configuration
contained script and fixture paths, which did not freeze their bytes. The runner
now verifies the optional expected asset digests during preparation and before
each task. The manifest records logical filenames and hashes without passing asset
contents or grading material to the host. A regression rejects a changed asset.
Experiment specs must include both the mock server and this public fixture; this
review does not claim to have inspected private run specs.

## Boundary and accounting assessment

The mock constructs a disposable SQLite projection from the selected public
fixture world. It never constructs an owner Workspace, consults installed grants
or reads a SourceConfig. Its STDIO entry point creates temporary state, denies
network socket use and removes the projection on normal shutdown. These are
simulated read and activation boundaries, not evidence of production permission
enforcement. No production endpoint or canonical schema is changed.

Exactly four tools are registered. Status is content-free; Full starts OFF; setup
returns an empty 32-unit response. Only the initial valid setup shape can be exempt
from task accounting, and it cannot return task evidence. Later activation,
refusals and schema-validation failures consume attempts. Disable and reactivation
cannot reset the counters. Dispatch is serialized, preventing concurrent calls
from racing the two-attempt budget.

Responses use the existing Aptuni context-unit estimator and packing behavior.
Task responses share a 4000-unit cap, including per-response metadata costs.
Catalog disclosure is capped at 800 units; its following exact-anchor lookup is
capped at 3200. A third retrieval attempt is refused and remains an attempted
call for grading, rather than earning another result. Tests exercise large budgets,
truncation, refusals, invalid arguments and counter preservation.

Catalog entries require permitted Evidence in the granted `knowledge` module.
Evidence lookup requires a previously disclosed anchor and rechecks exposure.
Unknown and hidden anchors return the same empty response. Exposure withdrawn
after catalog disclosure prevents subsequent evidence disclosure. Labels and
provenance references are inside the counted catalog payload, not a free preload.

## Experiment validity and limits

The positive and negative worlds share the task, catalog and four distractors.
Only the relevant evidence changes: attributed implementation and bounded
synthetic results in one world; third-party tutorial study without contribution
evidence in the other. The server retains only response-relevant fields and does
not expose case identifiers, interpretation labels, rubric or the other world's
evidence through its tools.

The baseline uses the existing SQLite lexical/concept retrieval implementation,
with ordinary evidence text available and no forced failed query. Tests confirm
that a compound topic can retrieve the relevant record. The catalog arm adds
bounded discovery plus exact-anchor access; it does not isolate catalog wording
as the sole treatment. Both arms use the same overall call and unit caps.

The fixed five-entry catalog exhausts a tiny invented corpus. It does not establish
large-corpus selection, generalization, real user benefit or a product success
rate. The fixture appropriately requires reporting all four planned outcomes and
rejects a benefit claim if baseline already passes both worlds. Keep case/rubric
blinding and the same host/model settings in the actual runs. No candidate outcome
or sealed-holdout readiness is approved by this implementation review.

## Verification

- Combined accounting, runner and mock tests: **25 passed**, including ten mock
  tests and a real synthetic STDIO session with disposable-state cleanup.
- Scoped Ruff across all three tools and test files: **passed**.
- No production edits or private-data access were performed by this reviewer.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

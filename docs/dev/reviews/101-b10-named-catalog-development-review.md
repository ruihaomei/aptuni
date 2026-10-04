# Review 101 — Named catalog fields for development controls

- **Date:** 2026-10-04
- **Scope:** the `catalog_named` arm in `tools/agent_e2e_mock.py` and its added
  regression in `tests/dev/test_agent_e2e_mock.py`, against `2ed671e`.
- **Method:** scoped diff review, public fixture comparison, focused tests and
  direct synthetic server probes. No model inference, private source inspection,
  live Workspace or Vault access, or sealed-task access by this reviewer.

## Blocking findings

None in the scoped implementation.

The new arm changes the catalog text from delimited rows to compact JSON objects
with `anchor`, `label` and `evidence_ref` fields. The original `catalog` and
`baseline` branches remain available. The public fixture has no diff against
`2ed671e`; this change does not rewrite its worlds or rubric.

The same permission filter selects the same five entries. Named fields add no
source content, locator access, filesystem operation or permission. The response
still passes through the existing context-unit estimator and 800-unit catalog
cap. Exact-anchor lookup still requires the previous disclosure, the second
counted attempt, permitted `knowledge` Evidence and a fresh exposure check.
The two-attempt, 4000-total-unit and 3200-evidence-unit caps remain unchanged.
Incorrect evidence-reference arguments are not silently repaired into anchors.

## Verification

- Mock tests: **11 passed**.
- Scoped Ruff and whitespace diff check: **passed**.
- Direct synthetic named-catalog probes returned five entries at **770 units**
  without truncation. Passing the returned repository anchor retrieved the
  expected Evidence record in both worlds. The positive world returned the
  attributed implementation record; the negative world retained its third-party
  tutorial and study-only boundary. Total used units were **1489** and **1447**,
  respectively, across two counted task calls.

Those probes supply the correct anchor directly. They establish server behavior
and accounting, not Agent comprehension or successful personalized answers.

## Non-blocking interpretation limits

The revised experimental package combines named serialization with an explicit
policy distinction between lookup anchor and evidence citation. Any subsequent
change in outcomes belongs to that combined package; it cannot establish that
serialization alone caused an improvement.

Both original worlds are reused development material. Preserve the failed frozen
results and report the revised controls separately. A useful positive control
requires an actual evidence lookup and a grounded project description. A useful
negative control requires an actual lookup of the study-only record and a grounded
distinction between study and owner contribution. Abstention after an empty
response does not establish the negative grounding result.

This approval covers the research-only implementation and its synthetic
accounting. It does not predict that either Agent control will pass, authorize
production adoption, establish reliability or independent validation, or open the
sealed holdout. The proposed cheaper-model transfer remains contingent on both
strong-model development controls passing their evidence-grounding criteria.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

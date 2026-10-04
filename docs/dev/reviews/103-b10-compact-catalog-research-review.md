# Review 103 — Compact catalog research arm and prepared packing audit

- **Date:** 2026-10-04.
- **Scope:** the new `catalog_compact` branch and regressions in
  `tools/agent_e2e_mock.py` and `tests/dev/test_agent_e2e_mock.py`; the prepared
  private compact-feasibility script and manifest compared with Review 102's
  inspected guard script. Review 101 already covers the named-contract arm.
- **Independence:** this reviewer authored the earlier baseline mock and the
  research proposal, but did not author this compact implementation or prepared
  feasibility-script revision. The review decision concerns those new changes.
- **Method:** scoped diff/static review, focused tests, direct synthetic MCP
  calls, digest verification and byte comparison. No private labels, oracle
  response, Vault, source configuration or sealed prompts were read. The prepared
  live script was neither imported nor executed; no model controls were run.

## Blocking findings

None for the scoped research implementation and prepared bounded packing audit.
Approval covers the two strong-model development controls and the separately
recorded deterministic fit diagnostic using the reviewed bytes. It does not
approve production adoption, a live model disclosure, broader discovery, a new
grant, automatic activation or opening the sealed holdout.

## Implementation findings

The compact branch retains the existing permitted-entry filter and first-five
order. It creates sequential process-local lookup anchors without disclosing
underlying repository identifiers or evidence citations in the catalog. A label
over 48 UTF-8 bytes is cut at a valid code-point boundary and receives an ellipsis
inside that cap. Labels are not summarized or semantically rewritten. The
existing quoted-data/tainted boundary remains; the evidence response retains its
ordinary evidence identifier and source provenance.

The serializer itself returns distinct anchors even when bounded labels collide.
The MCP disclosure path checks case-folded bounded labels and refuses a collision
before packing or installing the anchor map. It installs the map only after the
catalog unit is actually returned. Lookup accepts only a disclosed map key and
does not repair a repository identifier, citation or unknown string into an
anchor. The next lookup rechecks current record exposure and the knowledge-module
boundary; withdrawal returns no Evidence. The generated anchors are unique for
the bounded entries and the map is held only by the disposable server instance.

The two task-attempt limit, pre-validation counting, 800-unit discovery cap,
3200-unit evidence cap and combined actual 4000-unit cap are unchanged. Activation,
disable and status behavior is unchanged. Existing baseline, delimited catalog
and named catalog paths remain available. The public synthetic fixture has no
diff against `2ed671e`; failed earlier treatments are not overwritten.

## Verification performed

- **16 focused mock tests passed**, covering actual lexical retrieval and STDIO,
  setup, failed-attempt counting, shared units, compact ASCII/CJK byte bounds,
  visible truncation, collision refusal, both evidence worlds, fresh withdrawal,
  and equal empty responses for unknown/repository/citation arguments.
- Explicit-file **Ruff**, strict **mypy** on the mock, and whitespace checks passed.
- Direct synthetic compact calls returned **five entries at 605 units** in each
  world. A supplied correct opaque anchor returned one Evidence item; totals
  were **1324** and **1282** units respectively, with **two task calls** each.
  These probes supplied the anchor directly. They verify server behavior and
  accounting, not model comprehension, grounded answers or end-to-end success.

## Prepared aggregate audit

The new private script differs from the Review 102 script by importing a frozen
copy of the mock definitions, using its compact serializer for the same selected
rows, checking case-folded bounded-label collisions, adding aggregate shortening
and collision fields, and writing a separate result. It does not change selection,
budgets, permitted record filters, source-label parsing, host scopes, explicit
empty Full setup, authorization lock, mutation guard or stable-sequence check.

The existing source-label parser first verifies the ASCII owner/repository shape
and then takes the repository-name suffix; the compact helper introduces no new
namespace parsing rule. A collision aborts rather than exporting labels or a
partial catalog. The new result construction remains aggregate-only and does
not overwrite the original feasibility result.

The frozen helper is imported before installation of the existing audit hook.
Static inspection of the matching helper shows definitions and imports, with
server construction and execution confined to the uncalled entry point. It does
not instantiate an owner Workspace or read a Vault on import. This conclusion
applies to the reviewed frozen helper, not an arbitrary replaceable module.

Verified identities:

- Prior guarded script: `2959bed1bfad90f1f2154c7ff5d68ae27df712bdf944ca8143b306e1b5b757a3`.
- Prepared compact script: `37840e51138bdb414fbc14b22b925c2e8e5a3d1c6116f4d72f62654d34dce45f`.
- Frozen serializer snapshot and public mock, verified byte-identical:
  `a929f8e97c500c6303979c27451314662548e4901e0dc4fa711896b5cd84020a`.

The prepared manifest agrees with these digests and unchanged limits. Execution
receipts must bind the actual script/helper bytes and self-check result; the
serializer digest embedded in a result is a declared constant, not a runtime
integrity check. This review does not claim the pending self-check or live fit
measurement has occurred. Review 102's limits on the scoped Python audit hook,
permitted lock maintenance and absence of a general sandbox claim still apply.

## Non-blocking notes and interpretation limits

- **N1 — truncation semantics:** the serializer produces a visible ellipsis, but
  the shared tool description does not itself explain that it means part of the
  original label was omitted. Include that meaning in the separately frozen
  compact-control policy, particularly before any task involves shortened
  labels. The existing synthetic labels are short enough that neither proposed
  control depends on interpreting truncation. A shortened label never establishes
  authorship or complete source identity.
- **N2 — helper boundary:** `compact_catalog()` is a serializer, not the collision
  admission guard. Both reviewed callers perform the collision check before
  disclosure/export. Any later caller must preserve that check; this review does
  not approve using the helper's output directly as a production catalog.

The whole-item design still refuses to return an item that does not fit; no
partial list, increased budget or new ranking has been introduced. A successful
packing test would establish capacity for the selected five, not coverage of the
other eligible repositories or usefulness of truncated labels. The two reused
worlds remain development controls. Require real evidence lookup and the full
positive/negative answer boundaries; retain every earlier failed result.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

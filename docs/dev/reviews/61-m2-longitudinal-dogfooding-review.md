# Review 61 — M2 Longitudinal Maintainer Dogfooding

**Reviewer:** independent code-review agent

**Date:** 2026-09-23

**Scope:** ADR-0022, private derived evaluation state, purge/reset closure, filesystem safety,
schema migration, lock order, metric validity, permission path and human/JSON CLI rendering

## Findings and remediation

The first pass blocked three issues. Reset deleted managed state before discovering a contaminated
child; human trial output rendered canonical text with active terminal controls; and unit-efficiency
metrics mixed useful labels from unmeasured migrated trials with units from measured trials.

All were remediated test-first. Load, write and reset now validate the complete bounded directory;
reset obtains the validated child set before unlinking anything, and adversarial tests prove
contamination preserves both managed state and the outside target. Human output routes context
through `delimited_untrusted`, with real escape/newline coverage. Efficiency ratios now use both
units and useful labels only from measured trials, while overall usefulness still reports every
scored historical judgment.

The reviewer also verified exact state bounds/types, schema-v1 migration, fresh-process lock order,
ordinary exposure policy, content-byte absence, purge invalidation, managed reset scope and the CLI
journey. The maintainer's real authorized Folder setup has one content-free schema-v2 baseline;
no query trial or private source text was recorded.

**Verdict:** **APPROVE**

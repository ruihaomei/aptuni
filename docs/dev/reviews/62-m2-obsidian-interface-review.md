# Review 62 — M2 Obsidian Owner Interface

**Reviewer:** independent code-review agent

**Date:** 2026-09-24

**Scope:** ADR-0023; owner JSON bridge; canonical review/evidence/Forget actions; bundled Obsidian
desktop plugin; process, DOM and filesystem confinement; source/interface separation; packaging

## Findings and remediation

The first pass blocked four issues. Forget accepted a Memory already replaced by an edit; dashboard
sections could come from different Vault sequences; the JavaScript consumer did not enforce the
public bridge version; and the installer could be redirected by swapping an ancestor directory.

All were remediated test-first. Forget now checks non-superseded currentness both before preview and
again at confirmation. Every dashboard section is derived from one captured `RecordSet`, and rows
declare their currently valid actions so historical entries cannot present stale mutations. The
plugin rejects every response whose contract is not exactly `aptuni.obsidian@1` before rendering or
mutation.

Installer review then found two remaining continuity gaps: the selected vault pathname and final
`aptuni` target entry were not revalidated. The final implementation opens the resolved vault path
component-by-component from the filesystem root, retains every parent descriptor and child inode,
writes only through pinned no-follow directory descriptors, and revalidates the complete chain plus
`.obsidian`, `plugins` and `aptuni` immediately before success. Deterministic config-ancestor,
selected-vault and target swaps all remove owned assets and fail closed; partial writes are also
cleaned.

The reviewer verified that source ingestion remains separate, prior blockers stay closed, the
packaged assets are present, and focused tests, Ruff, strict mypy and JavaScript syntax checks pass.

**Verdict:** **APPROVE**

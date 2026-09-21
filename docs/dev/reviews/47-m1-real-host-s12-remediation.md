# Slice 17 privacy and host-confinement remediation

- **Responds to:** `47-m1-real-host-s12-review.md`

| Finding | Remediation |
|---|---|
| Full gate pending | Ran the complete local CI-equivalent gate: 459 tests plus 47 subtests, ruff, strict mypy, relay and all 34 developer checks passed. |
| Install path pending | The daily runner now resolves the generated bundle interpreter, imports `aptuni` under `-I`, and emits only content-free booleans for built-wheel importability, interpreter/package outside-project classification and project-`.venv` exclusion. The frozen evidence matrix records the already-observed external temporary runtime without a path. |
| Resolved version not enforced | Both real-host runners now require `resolved_version == requested_version` in their pass predicate. Both matrices record requested and resolved exact frozen versions. |

The focused six-test runner suite, runner lint/typing checks and JSON validation pass. No host matrix
was rerun for these evidence-contract fixes.

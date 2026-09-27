# Review 75 — Aptuni 0.2.0b1 Beta release candidate

**Date:** 2026-09-27
**Scope:** candidate `59269e9` for Aptuni 0.2.0b1 (PyPI via the tag-triggered OIDC workflow) and
Top-Down Learning plugin 0.2.0 (release tag and GitHub Release assets); version surfaces, the
beta-tag trigger and its supply-chain check, plugin packaging and licensing, diff hygiene and open
review verdicts
**Reviewer:** independent agent (`code-reviewer`)

## Findings

There are no blocking findings. The reviewer reproduced the full gate locally: 894 passed, 3
optional skips and 62 subtests, plus Ruff, mypy, the dev suite, relay and the
supply-chain secrets/notices/workflow checks. It confirmed that the workflow accepts exactly
`vX.Y.Z` and `vX.Y.ZbN` tags with the sole OIDC permission in the `pypi` environment. It also
confirmed that every absolute README link resolves at `v0.2.0b1`, and that the plugin wheel carries
Apache-2.0 metadata with LICENSE/NOTICE and resolves `aptuni==0.2.0b1` once it is published.

The following notes were fixed before tagging:

- A committed root run report containing a local owner path was moved to
  `docs/dev/runs/2026-09-24-api-platform-run.md` with the path generalized. It remains in
  already-public history, but it contains no secret.
- The plugin host manifests and the MCP server version said `2.0.0`; they now report `0.2.0`, and
  a regression test locks them to the package version.
- The CHANGELOG compare and release link references now point at `v0.2.0b1`.
- The plugin README names the clone directory and warns that the two tool environments upgrade
  separately.

Remaining notes: the release record is written after publication, and plugin assets are built from
the exact tag checkout with SHA-256 sums published. The plugin NOTICE still mentions repository
paths that the plugin distributions do not include; this is in BACKLOG.

## Verification

Hosted CI for `59269e9` passed on macOS 15, Ubuntu 24.04 and build/supply chain (run 36325983759).
The final candidate is re-verified by hosted CI before tagging.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

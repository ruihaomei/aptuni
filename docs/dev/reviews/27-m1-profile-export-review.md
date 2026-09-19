# Review 27 — M1 owner-readable Profile export

- **Date:** 2026-09-20
- **Reviewer:** independent Codex subagent (did not write the implementation under review)
- **Scope (uncommitted):** `src/aptuni/application/export.py`, `AptuniService.export`, CLI parser and
  dispatch, and `tests/integration/test_export.py`.
- **Risk class:** high (portable copy of private canonical data, lifecycle filtering, destination
  safety, and user-facing backup claims).

## Checks run

| Check | Result |
|---|---|
| `.tools/bin/uv run pytest -q tests/integration/test_export.py` | 3 passed |
| `.tools/bin/uv run ruff check src/aptuni/application/export.py tests/integration/test_export.py` | passed |
| `.tools/bin/uv run mypy src/aptuni/application/export.py` | passed |
| Accepted-Memory followed by candidate rejection reproduction | fixed: Memory absent from export and agent view |
| Valid current full-content Fact reproduction | fixed: content absent and `omitted_full_content == 1` |
| Injected final-rename failure with an existing empty destination | destination preserved; staging removed; fixed error returned |

The implementation exports one bounded Markdown file per non-empty module from one consistent Vault
snapshot. It uses current Fact and Evidence views, excludes retractions, pending candidates,
rejected/revoked/forgotten Memories and every record type carrying `retention.full_content`. Hidden
modules remain in the owner copy but are explicitly marked in frontmatter and prose. Tainted record
text is flattened, HTML-escaped and Markdown-escaped; frontmatter values derived from records are
controlled booleans, integers and module literals. Staging and result directories are mode `0700`,
files are mode `0600`, and a same-parent rename prevents observers from seeing a partially rendered
tree. The README and human CLI output accurately state that the export is unmanaged and is not a
restorable Vault backup.

## Blocking findings

None.

## Findings closed during review

### C1 — Full-content exclusion originally covered only Evidence

The initial implementation exported valid current Facts or Memories even when their canonical
retention label had `full_content=True`, and reported zero omissions. That contradicted ADR-0006's
retention-propagation rule and the export's own privacy statement. The final implementation filters
Facts, Memories and Evidence uniformly and aggregates all three omitted counts. A focused valid-Fact
reproduction now confirms that the marker is absent and the omission count is one.

### C2 — A withdrawn candidate could leave its previously created Memory in the export

The initial Memory predicate required a prior accept but did not reject a later reject/revoke event
on the candidate, diverging from `RecordSet.exposable()`. The final predicate requires the Memory ID
and its candidate ID to remain outside the reject/revoke set. A focused accept-then-reject canonical
history now produces neither exported content nor an agent-visible Memory.

## Non-blocking notes and test gaps

- **N1 — Preserve C1/C2 with repository tests.** The focused reproductions passed, but
  `test_export.py` still covers only full-content Evidence and direct Memory revocation. Add valid
  full-content Fact and Memory cases, and an accepted-Memory-then-candidate-reject/revoke case, with
  assertions for both content absence and exact report counts.
- **N2 — Add destination fault and race coverage.** Add injected failures during file rendering and
  final rename, proving staging cleanup and preservation of an existing empty or concurrently
  populated target. Also test a symlink target and an existing regular file. The implementation is
  safe in the focused rename-failure check, but this is privacy-sensitive filesystem behavior and
  should remain regression-covered.
- **N3 — Qualify the atomicity boundary.** The same-parent rename is namespace-atomic, but the export
  does not fsync files or the parent directory and therefore is not promised durable across power
  loss. That is acceptable for an explicitly unmanaged, regenerable copy; keep the user-facing
  language at “completed tree appears atomically” rather than implying Vault-grade crash durability.
- **N4 — Expand Markdown adversarial fixtures.** The current test covers bold markup and an HTML
  tag. Add headings, images, links, blockquotes, pipes, backticks, embedded newlines, backslashes and
  Unicode bidi/control characters across Fact statements, Memory statements/provenance, and Evidence
  subjects/excerpts. The renderer is structurally sound under inspection, but this claim deserves a
  compact parameterized regression set.
- **N5 — Test corrections and withdrawals explicitly.** Add one corrected/retracted Fact chain and
  one withdrawn Evidence chain, asserting that only the current non-retraction record appears and
  that module/frontmatter/report counts agree. This protects the slice's core “current Profile”
  contract rather than relying solely on `RecordSet` unit coverage elsewhere.
- **N6 — Existing-empty-directory replacement is POSIX-specific in practice.** Aptuni's current
  flagship host is macOS, where the focused path is valid. If the CLI later claims Windows support,
  verify `os.replace(staging_directory, existing_empty_directory)` there or narrow the contract to
  an absent destination on platforms that cannot perform that replacement.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

# Milestone 2 Obsidian vault source review

**Reviewer:** independent Claude subagent review of the uncommitted Obsidian source slice

## Scope

Reviewed the vault scan and admission (`src/aptuni/sources/obsidian.py`), the frontmatter/wikilink
parser (`src/aptuni/sources/obsidian_parse.py`), the ingest boundary
(`src/aptuni/application/obsidian_ingest.py`), the `add_obsidian_source` and `_sync_locked`/
`_ingest_for` wiring, the refactored `add-folder` path, the `add-obsidian` CLI surface, the
`obsidian.locator@1` registration, the `source.obsidian` catalog flip and both locale files,
ADR-0017, the accepted plan, and the unit/integration coverage. Checked against `AGENTS.md`,
ADR-0006 and `skills/add-source-provider/SKILL.md`.

## Verdict on the first submission

**BLOCK**, on three findings. All three were reproduced by the reviewer with concrete
counterexamples, and all three are now remediated test-first.

### B1 — A UTF-8 BOM (or a `...` line) defeated frontmatter minimization

`split_frontmatter` required the first line to be exactly `---`, so a leading UTF-8 byte-order
mark classified the entire property block as body text. The value then reached the Evidence
excerpt, the locator and the FTS index, with no `frontmatter_unsupported` note — a silent leak.
`split_frontmatter` also accepted YAML's `...` document-end marker, which Obsidian does not,
leaving the properties after it in the body. Violates invariant 2, plan case 6, and ADR-0017's
excerpt-minimization claim.

**Remediated.** `decode_note()` is now the single decode boundary for note bytes and strips the
BOM; `split_frontmatter` strips it defensively as well and returns an explicit
`(block, body, unterminated)` triple so the unterminated-fence fail-closed path cannot drift from
the split (this also closed N6). Only `---` terminates a block. Two failing-first unit cases plus
an end-to-end integration case through `sync`/`evidence`/`search` now cover it.

**This was live, not theoretical.** The maintainer's own vault has 64 BOM notes, 62 of them with
frontmatter, holding 101 property values that the defect would have written into indexed excerpts.
The pre-remediation dogfood audit missed them because a BOM'd note parsed as having no frontmatter,
so the check had nothing to compare against — the defect hid from the audit designed to find it
(the reviewer predicted exactly this in N13).

### B2 — The injection tests were vacuous, and `note_name`/`folder_path`/the CLI row were unsanitized

Both "injection" tests wrote the six literal characters of an escape sequence rather than an ESC
byte, so their assertions held unconditionally. The reviewer's decisive probe — removing only the
control/format scrubbing from `sanitize_token` while keeping the length cap — left the **entire
suite green**. Separately, `note_name` and `folder_path` bypassed `sanitize_token`, and
`aptuni evidence` printed the source path raw, so a POSIX-legal filename containing a real ESC and
a newline forged a complete evidence row with a live ANSI escape. Violates plan case 8 and
ADR-0013 item 2.

**Remediated.** Both tests now use real control bytes (ESC, NUL, newline, RLO, ZWSP, U+2028, CR);
`note_name` and `folder_path` go through `sanitize_token`; and `aptuni evidence` renders the path
through `delimited_untrusted`, which closes the row-forging class for the Folder and GitHub
providers too. `relative_path` deliberately stays raw as the identity key, so the render site is
where it is closed. Re-running the reviewer's decisive mutation now fails four tests.

### B3 — The plugin manifest claimed the provider does not read note bodies

`plugin.source.obsidian.weakness` read "Reads note structure, not note bodies" in both locales,
while `ObsidianIngest` stores and indexes a 280-character body excerpt exactly like the Folder
source. This is the consent surface `aptuni plugin list` and `aptuni advise` render, and ADR-0017's
own first driver is "Deliver what the manifest promises or do not ship the provider."

**Remediated.** Both locales now say the provider stores a short body excerpt like the Folder
source, and that property values are dropped and unusual frontmatter keeps no properties.
ADR-0017 states the same distinction explicitly.

## What the reviewer verified as sound

- Path identity plus `reconcile_keyed` is used unchanged; no common-contract file was touched.
- `.obsidian/`, `.trash/`, attachments, secrets, symlinks and oversized files are genuinely
  rejected before `_observe` reads anything.
- `sanitize_token` genuinely scrubs ANSI, NUL, bidi and zero-width characters.
- The two ADR-0017 mutation probes fail as the ADR claims.
- `add_folder_source`'s guard order after the `_approved_local_root`/`_check_modules` extraction is
  byte-for-byte the original order; no behaviour change on that shipped v0.1.0 path.
- The registered required/optional spec matches the ADR and every emitted field.
- `_WIKILINK`, `_INLINE_TAG` and `_SCALAR_KEY` are anchored or single-repetition over disjoint
  negated classes: no ReDoS.
- The `test_recommend.py` replacement strengthens rather than weakens the guard: `source.notion`
  must still be deferred, and `interface.obsidian` is newly pinned as still-deferred.

## Non-blocking notes and their disposition

| Note | Disposition |
|---|---|
| N1 — an unavailable vault root retracted every note under `complete` coverage | **Fixed.** `_walk` re-checks `is_vault` and raises `VaultUnavailableError`, surfaced as a bounded `obsidian_vault_unavailable`; regression added |
| N2 — `_observe` read with `read_bytes()`, TOCTOU-separated from the symlink check | **Fixed for this provider.** `_read_note` uses `O_NOFOLLOW` and re-checks the size on the descriptor. The equivalent gap in Folder/GitHub is backlogged |
| N3 — the CLI evidence row printed the path raw | **Fixed** as part of B2, for every provider |
| N4 — `tag` was accepted but `alias` was not | **Fixed**; regression added |
| N5 — `link_count`/`tag_count` reported the *capped* lengths, so the names misled | **Fixed.** Both dropped from the emitter and the registered spec; they duplicated `len(...)` |
| N6 — two different unterminated-fence conditions could drift | **Fixed** as part of B1's triple-returning `split_frontmatter`; regression added |
| N7 — `add-folder`'s human-readable line now delimits the path | **Kept and documented.** Recorded under `### Changed` in the CHANGELOG; `--json` is unchanged |
| N8 — duplicated `SourceConfig` construction | Backlogged |
| N9 — missing cap, nested-`.obsidian`, state-dir-overlap and symlinked-root cases | **Fixed.** `MAX_ALIASES`/`MAX_PROPERTY_KEYS` caps, a nested `.obsidian/` case and a state-directory-overlap case added |
| N10 — the determinism assertion compared a pure function against itself | **Fixed.** It now pins the exact retained prefix in input order |
| N11 — no `obsidian://` deep link | Backlogged |
| N12 — unwrapped `FileNotFoundError` from a mid-walk `stat` | Backlogged (pre-existing in `folder.py`) |
| N13 — the dogfood methodology could not have caught the BOM class | **Confirmed correct**, and quantified: 64 BOM notes, 101 property values. The audit was rewritten BOM-aware and now asserts directly on BOM notes |

## Evidence after remediation

Full gate: 542 tests plus 47 subtests, 3 optional-runtime skips; Ruff, strict mypy (72 source
files), relay and the notices/secrets/workflow supply-chain checks clean; the frozen evaluation
still passes with unchanged lexical metrics. Three mutation probes confirm the blockers are now
caught: removing `sanitize_token`'s scrubbing fails 4 tests; restoring BOM blindness and the `...`
terminator fails 2; un-sanitizing `note_name` with a raw CLI row fails 1.

Real-vault dogfood re-run after remediation: 5,750 Markdown files, 3,814 admitted, 7.8 s initial
sync, 4.0 s deterministic no-op re-sync, `doctor` passed. All 1,597 non-tag/alias property values
checked against every excerpt and every frontmatter-derived locator field: zero reached either, and
zero control characters reached any sanitized field. No note content was recorded in any artifact.

## Conclusion

The architecture was right from the first submission — path identity, the ADR-0006 pipeline reused
verbatim, no dependency, no network — and the three blockers were all in the details that decide
whether the privacy claim is true. They are fixed, each with a regression that fails when the
defect is reintroduced, and the manifest now describes what the provider actually does.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

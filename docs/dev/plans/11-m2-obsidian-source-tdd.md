# Milestone 2 Obsidian Source Plan (TDD)

**Status:** Accepted (2026-09-22)
**Owner:** single owner; touches the shared locator registry, so no parallel contract work.

## Objective

Ship a runnable, read-only Obsidian vault SourceProvider that contributes what the Folder source
cannot: vault-aware admission, note topology (wikilinks, folder position, headings) and frontmatter
properties as *structure*, without ever putting note bodies or property values into canonical
identity.

## Why this is not the Folder source

`source.folder` already ingests `.md` files by relative path. Its manifest promise for Obsidian is
different: "Reads an Obsidian vault with links and frontmatter" / "Keeps wikilinks and properties as
structure." The slice is only worth shipping if it delivers exactly that. It therefore adds:

- **Vault admission.** A directory is an Obsidian vault only if it contains `.obsidian/`. This makes
  `add-obsidian` a different consent decision from `add-folder`, not a synonym for it.
- **Vault-specific exclusion.** `.obsidian/` (plugin configs, workspace layout, hotkeys), `.trash/`
  (deleted-but-retained notes) and attachments are excluded before any read.
- **Topology in the locator.** Wikilink targets, folder position, heading count and tag/alias sets
  are identity/topology, kept bounded, the way `marginnote.locator@2` keeps learning path and depth
  without note bodies.
- **Frontmatter minimization.** Property *keys* are structure and are kept; property *values* are
  private content and are excluded from the locator, and the frontmatter block is stripped from the
  Evidence excerpt.

## Vertical slice

`aptuni source add-obsidian PATH --module M [--role R]` then the ordinary `aptuni sync`,
`aptuni evidence`, `aptuni review list` and `aptuni search` path. One new `obsidian` source type and
one new `obsidian.locator@1` extension registered in `default_registry()`.

## Decisions locked before implementation

- **Provider id / source type:** `obsidian`. **Parser:** `("obsidian.vault", "1")`.
- **Identity key:** the vault-relative POSIX path, exactly as the Folder source. Obsidian has no
  native stable note id, and inventing one from frontmatter would make a user's `id:` property
  silently load-bearing. Moves are detected by the existing content-hash reconciliation, so a rename
  stays a `move`, not a remove plus add. A frontmatter-keyed `obsidian.locator@2` stays available if
  real dogfood evidence ever demands it.
- **Admitted files:** regular, non-symlink `*.md` only. `.canvas`, images, PDFs and every other
  attachment are excluded and counted, never read.
- **Frontmatter parser:** clean-room and deliberately narrow — a leading `---` fence, `key: scalar`,
  `key: [a, b]` and `key:\n  - a\n  - b`. No anchors, aliases, tags, multi-document streams, block
  scalars or nesting. Anything outside the subset yields `frontmatter_unsupported` and an admitted
  note with no properties. Rationale: PyYAML would be a new runtime dependency with a far larger
  parse surface (anchors, `!!python` tags, billion-laughs) for a format we only need key names and
  short scalar lists from. Recorded in ADR-0017.
- **Bounds:** at most 32 tags, 16 aliases, 64 outbound links and 32 property keys per note; each
  token at most 128 characters; over-cap is truncated deterministically and flagged. Reuse the
  Folder source's file-count and byte bounds.
- **Retention:** `source_minimized`, matching the existing manifest.
- **Egress:** none. Everything is local file reads under one approved root.

## `obsidian.locator@1` fields

Required: `relative_path`, `note_name`, `folder_path`.
Optional: `tags`, `aliases`, `outbound_links`, `property_keys`, `heading_count`, `truncated`.
(`link_count`/`tag_count` were dropped in remediation: they reported the *capped* lengths, so the
names misled, and they duplicated `len(outbound_links)`/`len(tags)`.)

No frontmatter *value* other than tags and aliases appears anywhere in the locator. Tags and aliases
are kept because they are the user's own topic and naming structure and are the thing the manifest
promises; they are bounded and sanitized like every other untrusted token.

## Failing-first cases

1. **Admission.** A path without `.obsidian/` is refused with a bounded error naming `add-folder` as
   the alternative. A vault overlapping the Vault root or the state directory is refused. A
   non-directory, a missing path and a symlinked root are each refused or resolved safely.
2. **Exclusion before read.** `.obsidian/`, `.trash/`, other hidden directories, VCS/cache
   directories, secret-shaped names, non-`.md` attachments and oversized files never reach Evidence
   and are reported only as bounded, deduplicated notes.
3. **Topology.** The locator carries the vault-relative path, note name, folder path and bounded
   tags/aliases/outbound links/property keys — and no frontmatter value beyond tags and aliases.
4. **Wikilinks.** `[[Note]]`, `[[Note|alias]]`, `[[Note#Heading]]`, `[[folder/Note]]` and
   `![[Note]]` all normalize to the same bounded target name. `[[...]]` inside a fenced code block
   or inline code span is not a link.
5. **Frontmatter.** A valid subset block yields property keys, tags and aliases. A malformed or
   out-of-subset block does not fail the sync: the note is admitted, properties are empty, and
   `frontmatter_unsupported` is noted. A `---` that is not at byte zero is body text, not
   frontmatter.
6. **Excerpt minimization.** The Evidence excerpt never contains the frontmatter block, so a
   private property value cannot leak into the exposed excerpt or the search index.
7. **Bounds.** A note with thousands of tags or links produces a capped, deterministic locator
   flagged `truncated`, and cannot inflate canonical records.
8. **Injection.** A note name, tag, alias or link target containing ANSI escapes, newlines, NUL or
   Markdown control characters cannot forge a CLI row, an Evidence field or a locator field.
9. **Replay.** Repeat sync is a no-op; an edit is a `modify`; a rename is a `move`; a deletion is a
   retraction; a crash between canonical commit and source-state save replays without duplicating
   Evidence.
10. **Coverage.** A vault above the file cap reports `partial` coverage and never proposes removals
    from the unseen remainder.

## Deliverables

- `src/aptuni/sources/obsidian.py` (scan, admission, topology) and
  `src/aptuni/sources/obsidian_parse.py` (frontmatter subset and wikilink extraction), each within
  the 400-line guidance.
- `ObsidianIngest` in the application ingest module, `add_obsidian_source` and the `obsidian` branch
  of `_ingest_for`/`_sync_locked`, and the `source add-obsidian` CLI command.
- `obsidian.locator@1` in `default_registry()`.
- ADR-0017 for the new locator schema, the clean-room frontmatter subset and the no-new-dependency
  decision.
- `source.obsidian` manifest `planned -> builtin`, both locale files, README/README.zh-CN and
  CHANGELOG.

## Verification

```sh
.tools/bin/uv run --no-sync pytest tests/unit/sources/test_obsidian.py tests/integration/test_obsidian_source.py
.tools/bin/uv run --no-sync pytest
.tools/bin/uv run --no-sync ruff check . && .tools/bin/uv run --no-sync mypy src
python3.13 tools/check_relay.py
python3.13 tools/check_supply_chain.py notices && python3.13 tools/check_supply_chain.py secrets
```

Then a real-vault dogfood on the maintainer's own Obsidian vault (read-only; no note text recorded
in any artifact), and an independent review, which is required because this adds a public plugin
interface and a new locator schema.

## Exit

The slice is complete when an owner can approve a real Obsidian vault, sync it, see minimized
Evidence whose excerpts contain no frontmatter, search it, replay the sync as a no-op, observe a
rename as a move, and every excluded class is reported without ever having been read — and
independent review approves the boundary.

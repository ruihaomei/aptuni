# ADR-0017: Read an Obsidian vault as topology, not as a folder of Markdown

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent
- **PRD refs:** §11 (SourceProvider), §21 (Obsidian as a first-class human UI), §16
- **Research refs:** `docs/research/findings/source-identities-and-deltas.md`
- **Needs maintainer confirmation:** no

## Context

`source.folder` already ingests `.md` files by relative path, so an Obsidian vault is technically
readable today. The `source.obsidian` manifest nevertheless promises something a folder cannot
give: "Reads an Obsidian vault with links and frontmatter" and "Keeps wikilinks and properties as
structure." A provider that only repeats the Folder source would make that manifest dishonest.

Three forces shape the design. First, a vault's real signal is its graph — which notes the owner
linked, how they tagged and named them, where a note sits — not the prose. Second, frontmatter is
where the most sensitive structured values live (employers, people, salaries, credentials), so
property *values* must be treated as private content while property *keys* are structure. Third,
Obsidian has no native stable note identifier; only some owners add one by convention.

## Decision drivers

- Deliver what the manifest promises or do not ship the provider.
- Never let a private property value reach canonical identity, the exposed excerpt, or the
  retrieval projection.
- Keep a rename a `move`, not a deletion plus an addition.
- No new runtime dependency and no network.
- Reuse the ADR-0006 snapshot/delta pipeline unchanged.

## Options considered

### Option A — Alias `add-obsidian` to the Folder source
Summary. Accept a vault path and configure a `folder` source. **+** zero new code. **−** the
manifest's link/property promise becomes false; `.obsidian/` and `.trash/` would be ingested as
ordinary hidden paths; no topology at all.

### Option B — Key identity on a frontmatter `id`/`uid` property
Summary. Use a frontmatter identifier when present, the path otherwise. **+** survives a rename
even under partial coverage. **−** a user's ordinary `id:` property silently becomes load-bearing;
duplicate or removed ids create migration and ambiguity paths with no precedent; mixed keying
within one vault is hard to reason about.

### Option C — Path identity plus a bounded topology locator
Summary. Keep the Folder source's path key and content-hash reconciliation, and add vault
admission, vault-aware exclusion and bounded topology fields. **+** reuses proven reconciliation;
delivers the manifest promise; no new failure mode. **−** a rename under *partial* coverage stays
`ambiguous` rather than resolving to a move.

## Decision

We choose **Option C**.

- **Vault admission.** A directory is an Obsidian vault only if it contains a real, non-symlinked
  `.obsidian/` directory. `aptuni source add-obsidian` refuses anything else and names
  `add-folder` as the alternative, so approving a vault is a distinct consent decision.
- **Exclusion before read.** At the vault root, `.obsidian/` and `.trash/` are excluded by name.
  Elsewhere the Folder source's rules apply: hidden and VCS/cache directories, symlinks,
  secret-shaped names and oversized files. Only regular, non-symlinked `*.md` files are opened;
  every other extension is counted as `attachment_skipped` and never read.
- **Identity.** The key is the vault-relative POSIX path, reconciled by
  `reconcile_keyed`. A rename is therefore a `move` under complete coverage and `ambiguous` under
  partial coverage, exactly as for the Folder source.
- **`obsidian.locator@1`.** Required: `relative_path`, `note_name`, `folder_path`. Optional:
  `tags`, `aliases`, `outbound_links`, `property_keys`, `heading_count`, `truncated`. No
  frontmatter value other than tags and aliases appears in the locator; tags and aliases are kept
  because they are the owner's own topic and naming structure, which is precisely what the
  manifest promises, and they are bounded and sanitized like every other untrusted token.
  `note_name` and `folder_path` come from an owner-controlled filename and are sanitized the same
  way; `relative_path` stays raw because it is the identity key that reconciliation and the
  descriptor-relative read both depend on, so every surface that *renders* it must delimit it.
- **Excerpt minimization.** The Evidence excerpt is taken from the body *after* the frontmatter
  block is removed. An unterminated opening fence yields an empty body rather than an exposed
  unparsed property block. The claim is precise and bounded: *the frontmatter block is not a
  source of excerpt text*. If the owner also writes a property's value in the note body — a
  `title:` repeated as the `# heading` is the common case — the excerpt will contain it, because
  the body is what an excerpt is for. Path identity is likewise independent: `relative_path`,
  `folder_path` and `note_name` come from the file's location and may coincide with a property
  value without anything having been read from frontmatter.
- **Frontmatter grammar.** A clean-room subset: a `---` fence at the start of the note (after a
  UTF-8 BOM, which is stripped at one decode boundary — without that a BOM'd note's property block
  becomes excerpt text), `key: scalar`,
  `key: [a, b]`, and `key:` followed by `  - item` lines. No anchors, aliases, custom tags,
  multi-document streams, block scalars or nesting. Only `---` closes a block: YAML's `...`
  document-end marker does not, because Obsidian does not accept it and honouring it would leave
  the remaining properties in the body. An unterminated fence yields an empty body rather than an
  exposed property block. Anything outside the subset admits the note with no properties and
  reports `frontmatter_unsupported`. We reject a YAML dependency: its parse
  surface (anchors, `!!python` tags, billion-laughs expansion) is far larger than the key names and
  short scalar lists this provider needs, and it would be a new runtime dependency under rule 4.
- **Bounds.** At most 32 tags, 16 aliases, 64 outbound links and 32 property keys per note; each
  token at most 128 characters; control, format and surrogate characters are replaced before the
  token is stored. Over-cap sets `truncated` and notes `locator_truncated`.
- **Structure is not content.** Wikilinks and tags found inside fenced blocks or inline code spans
  are not structure. A `#` followed by a space is a heading, not a tag.
- **Availability is not deletion.** If the vault stops being a vault during a scan — an unmounted
  sync folder, an evicted iCloud directory — the provider raises rather than reconciling an empty
  observation, because an empty vault under `complete` coverage would retract every note.
- **The note excerpt is a body excerpt.** Like the Folder source, Evidence carries up to 280
  characters of body prose, and it is indexed. The provider does *not* claim to avoid note bodies;
  it claims to avoid frontmatter values. The plugin manifest says so in both locales.

## Consequences

- **Positive:** the manifest promise becomes true; `.obsidian/` plugin configs and `.trash/` are
  never read; frontmatter values cannot reach the excerpt, the locator or the search index; the
  provider adds no dependency, no network and no new reconciliation path.
- **Negative / risks:** a rename under partial coverage stays `ambiguous`; the frontmatter subset
  will reject blocks that real vaults contain (nested properties and block scalars are common), so
  those notes lose properties while still being admitted — visible as `frontmatter_unsupported`
  rather than silent. Tag and alias values are user-authored content kept as structure; they are
  bounded and sanitized, but they are values, and that is a deliberate, documented exception.
- **Follow-ups:** `obsidian.locator@2` keyed on a frontmatter identifier stays available if real
  dogfood shows path identity is insufficient. Backlinks, the `.canvas` format and the Obsidian
  *interface* plugin (`interface.obsidian`) are separate, still-planned work.

## Verification

`tests/unit/sources/test_obsidian.py` covers admission, vault-aware exclusion, topology, every
wikilink form, code-fence exclusion, the frontmatter subset and its rejections, caps, control
characters and the replay matrix. `tests/integration/test_obsidian_source.py` covers refusal of a
plain folder, refusal of a vault overlapping the canonical Vault, excerpt minimization end to end,
absence of property values from the search index, no-op replay, rename identity, the crash-replay
window and the CLI flow. Two mutation probes confirm the privacy assertions fail when a property
value reaches the locator or the excerpt.

Independent Review 55 returned BLOCK on three findings, each now remediated test-first: a UTF-8
BOM (and a `...` line) defeated frontmatter detection and put property values into the excerpt and
the FTS index (B1); the injection tests were vacuous and `note_name`/`folder_path` plus the CLI
evidence row were unsanitized, so a crafted filename forged an evidence row with a live ANSI escape
(B2); and the plugin manifest claimed the provider does not read note bodies while storing an
indexed 280-character body excerpt (B3). Mutation probes confirm all three regressions now fail the
suite.

A real-vault dogfood on 5,750 Markdown files (3,814 admitted, 22 with out-of-subset or
unterminated frontmatter) re-ran after remediation and checked all 1,597 non-tag/alias property
values against every excerpt and every frontmatter-derived locator field: **zero** reached either,
and zero control characters reached any sanitized field. Initial sync took 7.8 s, the deterministic
no-op re-sync 4.0 s, and `doctor` passed. No note content was recorded in any artifact.

The same vault is why B1 mattered: **64 of its 3,814 notes carry a UTF-8 BOM**, 62 of those carry
frontmatter, and the defect would have put **101 real property values** into indexed Evidence
excerpts. The pre-remediation audit missed them precisely because a BOM'd note parsed as having no
frontmatter at all, so there was nothing for it to compare against — the failure mode hid itself
from the check designed to find it. The post-remediation audit asserts directly that no BOM note's
excerpt begins with the property block.

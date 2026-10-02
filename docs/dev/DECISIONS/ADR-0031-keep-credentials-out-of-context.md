# ADR-0031: Keep obvious credentials out of Evidence and out of Context

- **Status:** Accepted (maintainer brief of 2026-10-02: P1 privacy defect, defense in depth;
  independent review required)
- **Date:** 2026-10-02
- **Deciders:** maintainer (final say) · implementing agent · independent reviewer
- **Builds on:** ADR-0006 (folder secret filenames), ADR-0010 (purge, deletion ledger), ADR-0005
  (Context packing), ADR-0013/0018 (host proposals and their protected patterns)
- **Needs maintainer confirmation:** no for this contract; owner decisions for the incident are
  listed under "Incident"

## Context

A folder-source note named like any other note (ADR-0006 only skips secret-looking *file names*)
contained a mailbox and a university-account login with passwords. Its 280-character excerpt
became Evidence and could be returned to Agents through Full. Source ingest had no content check;
only Agent memory proposals were screened. Two further facts shaped the decision:

- Purging one Evidence record purges its whole source (ADR-0010 `_add_source_scope`, so a later
  sync cannot resurrect it). For a 119-record application folder that is the wrong tool for one file.
- Removing a file from a folder source retracts its Evidence, but the retraction copied the
  previous excerpt, so the secret was duplicated into a new canonical record.

## Decision

1. **Detector** (`aptuni.policy.secrets.credential_kinds`, high precision): PEM private-key
   blocks; known provider token formats (OpenAI/Anthropic `sk-`, GitHub `ghp_`/`github_pat_`, AWS
   `AKIA`/`ASIA`, Google `AIza`, Slack `xox?-`, Hugging Face `hf_`, GitLab `glpat-`, Stripe live
   keys, npm, long `Bearer` tokens); JWTs; credentials embedded in URLs; and labelled fields
   (`password`/`passwd`/`passcode`/`pwd`/`密码`/`口令`/`api key`/`secret key`/`client secret`/
   `access|refresh|auth token`) **only** when the value is a single secret-shaped token (6–200
   characters, not CJK prose, not a placeholder such as `******`, `<your password>`, `changeme`,
   and containing a digit, a symbol, mixed case, or ≥16 characters). Notes that discuss passwords
   ("use a password manager", "密码学", "password: required") are not credentials. On User #1's
   Vault (167,378 texts, 5.6 s) it flagged exactly the two records of the incident.
2. **Ingest** (`aptuni.application.credential_guard`, applied to every source type in
   `SourceCommands` before commit): a new or changed item whose subject or excerpt holds a
   credential is **withheld** — no Evidence is written; if an earlier version exists it is retracted.
   Every sync, including a sync with no changes, also **sweeps** the source's current Evidence and
   retracts any record holding a credential (deterministic id `credential-withheld:<id>`, idempotent).
   Retractions written by this path, and any retraction whose text holds a credential, carry
   `excerpt=None` (and a neutral subject if the subject itself holds one), so containment never
   copies a secret into a new record. The sync report gains `withheld` and the note
   `credential_withheld`; the CLI explains it. Source files are never modified.
3. **Retrieval** (last line): `pack_units`, which every Context, Profile, Memory, identity-card and
   review response goes through, drops any unit whose text holds a credential and reports
   `withheld_credentials` (content-free) in the response and the MCP JSON. This covers records from
   before this ADR, owner-typed statements and anything a future path might miss.
4. **Agent proposals**: the detector is added to the existing protected patterns (union).
5. **Inventory**: `aptuni doctor` lists records holding credential-like text (id, source, current or
   history, rule kind — never the text) with the remediation path.

## Behaviour of existing and future data

| Case | Behaviour |
|---|---|
| Already ingested, still current | Never returned (3); retracted on the source's next sync (2); listed by `doctor` |
| Already superseded (history) | Not exposable; stays in canonical history and backups; listed by `doctor` |
| Future source item with a credential | Withheld at ingest; counted in the sync report |
| User-owned source file | Never read for anything else, never modified or deleted |
| Owner-typed statement with a credential | Stored (owner's choice) but never returned to Context |
| False positive | The item stays out; the sync report and `doctor` name it; the owner rephrases the note (e.g. drops the `password:` label) and syncs. There is no bypass switch: a wrongly withheld note costs one note, a wrongly released secret cannot be recalled |
| Erasure from history | Only `aptuni privacy purge`, which is source-granular (ADR-0010); item-level erasure is out of scope |

The boundary is credentials and secrets. This does **not** detect or hide personal information in
general (names, phone numbers, addresses, health or financial details); module exposure policy is
the control for those.

## Incident (User #1, 2026-10-02)

Contained without code: the file was renamed in place to include `secret` (ADR-0006 skips it) and
the folder source synced (b9), which retracted the record — confirmed not exposable. Remaining
copies are two non-exposable history records (the original and the b9 retraction that copied its
excerpt) and the 2026-10-01 backup. Owner actions: rotate the exposed accounts; decide whether to
erase history (source-wide purge and re-adding the folder) and the old backup.

## Consequences

- No dependency; regex scanning of ~100 Context units per request is negligible; a sync scans only
  that source's items and current Evidence.
- MCP/CLI output gains additive, content-free counts; Vault schema and grants are unchanged.
- Unusual secret formats (an unlabelled random string, a password written in a sentence) are not
  detected; the module policy and source selection remain the owner's broader controls.

## Verification

`tests/unit/policy/test_secrets.py` (13 positive and 14 negative cases),
`tests/integration/test_credential_containment.py` (withhold, edit-to-secret retraction without
text, legacy sweep and idempotence, removal retraction without text, Context and MCP withholding,
identity card, `doctor` inventory, Agent proposals); real-Vault scan; independent review.

## Amendment 2026-10-02 — Review 93 remediation and historical records

Review 93 blocked on three findings; all are fixed test-first. Decisions 1–5 above stand, with
these changes.

1. **Detector coverage (B1, N2, N6; Review 94 B1, N1, N2).** Labels may be decorated by Markdown
   emphasis, inline code or quotes on either side of the separator (`**密码**：`, `**Password:**`,
   `` `api_key`: ``, `"password": "…"`), be env-style (`DB_PASSWORD=`, `GITHUB_TOKEN=`,
   `AWS_SECRET_ACCESS_KEY=`, a bounded `PREFIX_` chain anchored at a word start), or name a Markdown
   table column (`| 密码 |` header with the value in the same column, also after sources flatten the
   table onto one line; the header is the row right before each `|---|` separator, so a later table
   starts afresh, and a table value must be one token; or `| password | v |`). Unqualified `token`/
   `secret` labels, common in ML and code notes, need a value of at least 12 characters; qualified
   ones (`client_secret`, `access_token`, `GITHUB_TOKEN`) do not (Review 95 N1, N2). Values that are code (calls, indexing,
   `os.getenv`, `${{ … }}`, `name.attribute`), paths, dates, versions (`v2.1.0`), counted words
   (`6-digit`) or title-case words (`Required`) are not secrets. Matching is linear: the URL scheme is
   bounded to 32 characters, the label prefix to four segments, and the table rule reads at most 16
   label columns per row (60k-character adversarial inputs < 0.05 s). Tests: 30 positive and 50
   negative cases plus a worst-case runtime test.
2. **No copy paths (B2).** `credential_guard.scrubbed`/`retraction_of` neutralise the subject, drop
   the excerpt and replace credential-bearing locator strings (Notion and GitHub Deep `title`) with
   `[credential withheld]`. Source removal (ADR-0027) scrubs its retractions the same way. Authority
   grant and reclassify (ADR-0028/0029) always list credential-bearing current Evidence as a change
   and **retract** it instead of writing a correction, so no Evidence-derived Profile Fact is
   derived from it. `aptuni retract` writes `Retracted: [credential withheld]` for a credential
   statement. Detection and `doctor` now also read locator strings.
3. **Owner can locate withheld items (B3).** `SyncReport.withheld_items` lists each withheld item by
   relative path (folder/Obsidian), page id (Notion), path or activity key (GitHub), or note id
   (MarginNote) — never a title or text — in owner CLI sync output and `--json` only. MCP never sees
   it. An unchanged withheld item is listed on the sync that withheld it, not on every sync (N7).
4. **Hosts get no count (N1).** MCP Context JSON no longer carries `withheld_credentials`; the count
   stays in owner CLI output (`aptuni context`, now also `--json`). The public SDK `ContextResult`
   does not carry it.
5. **Identity card per statement (N3).** Credential-like identity statements are dropped one by one;
   the rest of the L0 card is still returned.
6. **Historical records: targeted erasure.** `aptuni privacy purge preview --credential-history`
   selects every **source Evidence** record holding credential-like text whose whole purge closure
   (supersession chain and dependants) holds only Evidence, review events and Facts, none of them
   **current** — current is judged independently of exposure, so a record in a hidden module,
   awaiting review, or a clean corrected successor keeps its chain out of scope (Review 94 B2).
   Memories, observations and owner-typed Facts are left out of this targeted path.
   Use the full set of ids `doctor` lists for a separately reviewed exact-id purge;
   do not purge an auto-promoted CLI memory by its memory id alone (pre-existing
   Review 96 N1 / KI-024 lifecycle bug). The expansion omits the source-wide scope of ADR-0010.
   This is safe because sync derives `supersedes` from current canonical Evidence, not from the
   source snapshot: once a chain is gone, a later change to the same path starts a new lineage, and a
   still-credential version is withheld again. Before anything is written, the preview validates the
   Vault without the selected records (`purge_scope_invalid` otherwise), and preview and confirm both
   refuse with `source_sync_pending` while an affected, not removed source has an interrupted sync
   whose replay could reference the purged ids (Review 94 B3, Review 95 N3); the owner syncs that
   source first. A chain with a current version is not selected; that history stays non-exposable
   and is listed by `doctor`. Everything
   else is the reviewed ADR-0010 purge: exact preview and digest, typed `PURGE`, deletion ledger,
   receipt, projection invalidation, and revocation of adapter grants and bundles (the owner re-runs
   adapter setup afterwards). Rehearsed on a scratch copy of User #1's Vault: exactly the two incident
   records were erased, 0 credential records remained, `doctor` passed.

### Defence in depth after this amendment

**Incident status update, 2026-10-02:** the owner confirmed the reviewed targeted
credential-history action. Its receipt reports `complete_managed_external_action_needed`.
Both incident Evidence ids are absent; doctor passes and the canonical credential
inventory is zero. No source was purged; all 125 unrelated exposable Evidence records
in the affected source remain. Active Claude/Codex grants were restored under explicit
owner chat authorization with unchanged scopes. A new verified post-purge backup has
zero detector hits and includes the deletion ledger; the old backup remains an
external copy (one incident record detected). This does not verify account rotation
or erase source files, earlier exports or host/provider transcripts. Review 96's
non-blocking detector residuals and pre-existing memory-id purge issue remain tracked.

| Layer | Protection |
|---|---|
| Source ingest | Detector on subject, excerpt and locator strings; item withheld, earlier version retracted |
| Every sync | Sweep of the source's current Evidence |
| Derivation / copy paths | Sync, removal, authority and Fact retractions scrub; authority retracts instead of re-deriving |
| Canonical history | Non-exposable; `doctor` lists it; `--credential-history` purge erases it |
| Context | `pack_units` drops any credential-like unit; identity card filters per statement |
| Agent | Host proposals refused; no withheld count over MCP |

### Residuals (documented, not detected or not covered)

- Not detected: unlabelled random strings; prose (`password is …`, `密码是…`); separators other than
  `:`, `：`, `=`, `|`; HTML-decorated labels (`<b>Password</b>:`); a label alone on a heading line
  with the value below it; lowercase words or passphrases and repeated-digit PINs as values; short
  labels `pw:`/`pass:`; bare `token:`/`secret:` values under 12 characters; CLI flags
  (`--password …`); `Authorization: Basic`; PIN/CVV/验证码/seed phrases; a value cut below six
  characters by the 280-character excerpt boundary (N5); underscore emphasis (`_Password:_`); a
  table without outer pipes once flattened; a table with empty cells may misalign its columns;
  a credential table cell with trailing words; a separator-less credential table following
  another table after flattening (Review 96 N2/N4).
- False positives remain possible for long tokenizer vocabulary values under bare credential-like
  labels/table headers (Review 96 N4). Removed-source pending sync state is not erased by the
  targeted history path and can retain text; an invalid candidate closure refuses the whole
  preview rather than selecting only the safe candidates (Review 96 N3/N5).
- A withheld file whose *name* holds a credential is listed only by its opaque `folder-<hash>` id.
- Owner surfaces `aptuni export`, `aptuni search` and `aptuni evidence` are not filtered; an export is
  portable and may hold a credential typed by the owner (N12).
- Non-canonical source snapshots and review entries keep Notion and GitHub Deep titles of withheld
  items; they are never exposed (N11).
- A source whose module has ingest disabled cannot sync, so its sweep waits; `pack_units` still
  protects it (N9).
- Copies outside the Vault are not reachable: earlier backups, earlier exports or Obsidian-interface
  copies, and any host transcript or model-provider log that received the record before containment.
  Rotation is the effective remedy (N10).
- Real-Vault measurement (scratch copy, 83,698 texts, 3.4–3.7 s, before and after Review 94): 2 hits, both the incident; a loose
  label scan of the remaining texts found no missed credential (precision 2/2; recall measured only
  on this Vault).

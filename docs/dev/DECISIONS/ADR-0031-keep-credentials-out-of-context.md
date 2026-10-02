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

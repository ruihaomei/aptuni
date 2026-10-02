# Review 93 — Credential guard: keep obvious credentials out of Evidence and Context (ADR-0031)

- **Scope:** commit `94c025d` ("fix(privacy): keep obvious credentials out of Evidence and Context
  (ADR-0031)") against its parent `d1506d0`: `src/aptuni/policy/secrets.py`,
  `src/aptuni/application/credential_guard.py`, its use in `SourceCommands._sync_locked` /
  `_sync_unchanged`, the `pack_units` guard and `withheld_credentials` plumbing (`context.py`,
  `knowledge_commands.py`, `service.py`, `mcp/server.py`, `cli/main.py`), the host-proposal union in
  `memory_commands.py`, `service.credential_records()` and `doctor`, ADR-0031, CHANGELOG and the
  BETA_DOGFOODING row. Neighbouring paths that write Evidence (`source_removal.py`,
  `source_authority.py`) were read because ADR-0031 makes a Vault-wide claim about them. The untracked
  `.agents/skills/` directory and the untracked Chinese-named `.txt` file are unrelated user files and
  were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in the session scratchpad against temporary Vaults with synthetic
  secret values only. The owner's Vault and source folders were not read; the ADR's real-Vault scan
  figures (167,378 texts, 2 hits) were therefore not reproduced. No source or test file was modified.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest` | exit 0; 1190 passed, 3 skipped (1193 collected); the 35 ADR-0031 tests pass |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 122 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |
| `python3.13 tools/check_supply_chain.py secrets` | supply-chain secrets check passed |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true` |
| `python3.13 -m unittest discover -s tests/dev` | Ran 56 tests, OK |

## Probes

| Probe | Result |
|---|---|
| Folder note with `**Password**: <secret>` / `- **密码**：<secret>`, a JSON block `{"password": "<secret>"}`, a Markdown table row | All three ingested as Evidence; `aptuni.full`-style Context returns 3 units holding the secret, `withheld_credentials=0` (B1) |
| 65 adversarial positives (`.env`, JSON/YAML/Python dicts, Markdown emphasis, tables, `pw:`/`pass:`, prose, CJK full-width colons, trailing punctuation, passphrases, URL variants, PIN-like codes) | 24 detected, 41 missed (B1, N4) |
| 69 adversarial negatives (crypto/tokenizer prose, code samples, placeholders, URLs with ports, hashes, UUIDs, git SHAs, base64 image data, `key: value` maths, title-case form labels) | 23 false positives, all from the labelled-field rule (N2) |
| Prototype: tolerate `[*_`"'\]]{0,3}` between label and separator | Catches all 7 decorated positives; flags none of the 14 committed negatives nor 6 decorated placeholders |
| Folder flows: withheld new file → clean edit → credential edit → delete; legacy sweep → still-credential edit → clean edit; legacy + delete in one sync | Correct current set at every step; `RecordSet.validate()` and `doctor` pass; sweep idempotent; no new record holds the secret |
| Crash after canonical commit (before `SourceStateStore.save`), and crash before commit | Both recover through `_recover_pending`; guard retraction ids are in `expected_ids`; rerun is a no-op / redoes the delta |
| MarginNote studied card whose title gains, or (pre-ADR) held, `密码：<secret>` | Card and its parent (summary lists the child label) withheld; their Evidence-derived Facts leave `exposable()`; clean edit re-derives them; invariants pass |
| Notion page titled `Wifi 密码：<secret>` ingested pre-ADR, then swept / removed | Retraction subject neutral and excerpt `None`, but `provenance.locator.extension.fields.title` still holds the secret (B2) |
| `remove_source` on a folder with legacy credential Evidence | New retraction holds the full excerpt (B2) |
| `grant_source_authority` on a MarginNote source with legacy credential Evidence, before any sync | Two new **current** corrections and one new **current** Profile Fact hold the secret; only `pack_units` hides them until the next sync (B2) |
| Context with an owner-typed credential statement | Query `bank` → 1 item + `withheld_credentials=1`; query = the exact secret → 0 items + `withheld_credentials=1`; an unrelated token → 0 (N1) |
| Identity card with one clean and one credential-like statement | Whole L0 card withheld (`items=0`) (N3) |
| `credential_kinds` on 10k / 30k / 60k characters of `a.a.a.` | 0.16 s / 1.4 s / 5.8 s (quadratic `_URL_CREDENTIALS`); every other pattern ≤ 30 ms (N6) |

## Blocking findings

### B1 — The labelled-field rule misses its own class in the most common note and config layouts

`src/aptuni/policy/secrets.py:35-39`: `_FIELD` requires the separator to follow the label after
whitespace only. Markdown emphasis or inline code around the label (`**Password**: …`,
`- **密码**：…`, `` `api_key`: … ``) and quoted keys (`"password": "…"` in JSON,
`'password': '…'` in Python/YAML) therefore never match, although ADR-0031 Decision 1 defines exactly
these as labelled fields with a secret-shaped value. Failure scenario (reproduced): an Obsidian or
folder note listing accounts as `- **Password**: <value>`, or a config snippet in a note, is ingested
as Evidence, is not swept, is not listed by `doctor`, and is returned to Agents by Full Context with
`withheld_credentials=0`. That is the P1 incident class this commit exists to close, and the
CHANGELOG tells owners that such notes "are no longer taken into Aptuni from any source".

Required: tolerate emphasis/code/quote decoration between the label and the separator (the
prototype above costs no precision on the committed negatives), with positive tests for each layout
and negative tests for decorated placeholders. Then state measured coverage honestly in ADR-0031
and the CHANGELOG ("passwords, keys and tokens written in a labelled `name: value` form …") and list
the documented misses (N4). Env-style `*_TOKEN=` / `*_SECRET=` assignments are cheap to add in the
same change (recommended, not required).

### B2 — Containment still copies secrets into new canonical records, contrary to ADR-0031 Decision 2

ADR-0031 states that retractions written by the guard, "and any retraction whose text holds a
credential", carry no excerpt, "so containment never copies a secret into a new record". Three paths
break this:

1. `src/aptuni/application/source_removal.py:102-109` (`_retraction`, ADR-0027 source removal)
   copies `previous.model_dump()` including `excerpt` and `subject`. Removing a source that holds
   legacy credential Evidence — a natural owner response to this incident — writes one new copy per
   record (reproduced).
2. `src/aptuni/application/source_authority.py:226-233` (`_rederived`, used by
   `grant_source_authority` and `reclassify_source`) writes a **current** `correction` copying the
   excerpt, and `derive_evidence_profile` then writes a **current** Profile Fact
   `Studied <subject>` that holds the secret (reproduced: 2 corrections + 1 Fact). Only `pack_units`
   hides them until the next sync sweep; `doctor` lists them as current.
3. `src/aptuni/application/credential_guard.py:34-49` (`_retraction`, `_scrubbed`) neutralise
   `subject` and `excerpt` but copy `provenance.locator.extension.fields`, which holds the free-text
   `title` for Notion pages (`sources/notion.py:186`) and GitHub Deep activity
   (`sources/github.py:434`). A Notion page titled with a credential keeps the secret in every guard
   retraction (reproduced). `service.credential_records()` (`service.py:716-727`) scans only
   `subject`/`statement`/`excerpt`, so `doctor` does not list these copies.

Required: apply the guard's scrubbing to source-removal retractions; in authority grant/reclassify,
do not re-derive (or retract instead of correcting) a record whose text holds a credential; scrub
credential-bearing free-text locator fields in guard retractions or, if the locator must stay
byte-identical, document the residual precisely and make `doctor` scan locator text. Add a test per
path.

### B3 — The owner cannot find a withheld item, so the ADR's false-positive and remediation path does not work

ADR-0031 ("Behaviour of existing and future data", False positive) says "the sync report and
`doctor` name it" and relies on the owner rephrasing the note, with no bypass switch. Neither names
it: `SyncReport.withheld` and the CLI message (`cli/main.py:445-448`) give only a count, and a
withheld new item never becomes a record, so `credential_records()` cannot list it. The same gap
leaves a true positive unlocatable — the owner is told to "remove the secret from the file" without
being told which file, and so cannot rotate or clean the right account. Required: list withheld items
by locator in owner-facing CLI sync output only (relative path for folder/Obsidian, page id for
Notion, path or activity key for GitHub, note id for MarginNote; never the title or text, never in
MCP), or correct the ADR and give the owner another working way to find them.

## Non-blocking notes

- **N1 — `withheld_credentials` is an oracle for host Agents.** It is content-free per item but
  query-dependent: an Agent learns that a credential exists for a topic (`bank` → 1), and can confirm
  a guessed value whole (query = the exact token → 0 items, 1 withheld). Source records stop
  answering after the next sync sweep; owner-typed credential statements answer indefinitely.
  Consider omitting the count from `host_mcp` responses (keep it for `owner_cli`), and do not call it
  content-free in ADR-0031 without that caveat.
- **N2 — False positives on ordinary notes.** Title-case words count as "mixed case":
  `Password: Required`, `API Key: Required`, `Access token: Expired`, `Auth token: Refreshed`,
  `passcode: Disabled`, `password: Forgotten`. Code and shell notes: `pwd = os.getcwd()`,
  `PWD=/Users/…`, `pwd: ~/code`, `password = os.getenv('DB_PW')`,
  `api_key = os.environ.get('…')`, `access_token = response.json()['access_token']`,
  `password = bcrypt.hashpw(pw, salt)`, `密码 = hashlib.sha256(…)`. Others: `pwd: 2024-10-01 …`,
  `passcode: 6-digit`, `api key: per-user, rotated …`, `password: not-set`. Suggested: mixed case only
  with an uppercase letter after the first character; skip values that look like code (`(`, `[`,
  leading `os.`/`self.`/`$`/`%`/`{{`) and `pwd` values that are paths. The CHANGELOG line "Notes that
  merely discuss passwords are unaffected" should be softened accordingly (this review itself is
  flagged because of the examples in this note).
- **N3 — Identity card is all-or-nothing.** `service.identity_card` joins every identity statement into
  one unit, so one credential-like (or falsely flagged) statement removes the entire L0 card. Filter
  per statement before joining.
- **N4 — Residual misses to document (or add when cheap):** Markdown tables (`| password | … |`);
  short labels `pw:`/`pass:`; prose (`password is …`, `密码是…`, `密码 …`); separators other than
  `:`/`=` (`-`, `→`, a newline-separated `username / password:` pair); passwords that are lowercase
  words or passphrases (`lemontree`, `correct horse battery staple`); repeated-digit PINs (`888888`,
  rejected by `len(set(value)) <= 2`); bare `secret:`/`token:` and env `*_TOKEN=`/`*_SECRET=`;
  AWS secret access keys; `Authorization: Basic`; `redis://:<pw>@host` (empty user); CLI flags
  (`--password …`, `-p…`); PIN/CVV/验证码/seed phrases; Stripe `sk_test_`. ADR-0031 currently names
  only "an unlabelled random string, a password written in a sentence".
- **N5 — Truncation boundary.** Detection runs on the 280-character excerpt (and on clipped MarginNote
  labels). A value cut to fewer than six characters at the boundary evades detection while a partial
  secret is stored and exposable.
- **N6 — Quadratic URL rule.** `_URL_CREDENTIALS` (`\b[a-z][a-z0-9+.-]*://…`) rescans from every word
  boundary: 60k characters of `a.a.a.` take 5.8 s. Inputs are bounded today (excerpts and statements
  ≤ 280 characters; the identity-card join is owner-only), so this is not a host-reachable DoS; bound
  the scheme (`{0,31}`) anyway.
- **N7 — Withheld items stay in the source snapshot.** Deleting such a file later writes a retraction
  that supersedes the guard retraction (valid, harmless noise), and an unchanged withheld item is
  never re-evaluated if a future detector removes a false positive. Document, or skip remove
  operations whose previous head is already a retraction.
- **N8 — `doctor` details.** `current` uses `exposable()`, so current records in an unexposed module
  print as `history`; the remediation text does not cover owner-typed records (`source=-`), and
  `aptuni retract` writes `Retracted: <statement>` (`service.py:698-702`), copying the credential again.
  `aptuni context --json` (`cli/main.py:566-577`) omits `withheld_credentials` although the human
  output prints it.
- **N9 — Sweep needs a runnable sync.** A source whose module has ingest disabled refuses to sync, so
  "retracted on the source's next sync" does not happen there; `pack_units` still protects it.
- **N10 — Incident section.** The remaining-copies list should also mention possible host-side copies
  (Agent transcripts and the model provider, if Full returned the record before containment), any
  earlier `aptuni export` or Obsidian-interface copies, and the non-canonical source state; rotation,
  already advised, is the effective remedy. The real-Vault scan measures precision only; recall was
  not measured and the probes above show it is materially incomplete.
- **N11 — Non-canonical locator text.** Source-state snapshots and review entries keep Notion and
  GitHub Deep titles for withheld items. They are never exposed; mention them in the ADR's residuals.
- **N12 — Unguarded owner surfaces.** `aptuni export`, `aptuni search` and `aptuni evidence` do not
  pass through `pack_units`. That is acceptable for owner actions, but ADR-0031 Decision 3 ("every
  Context, Profile, Memory, identity-card and review response") should name these exceptions; the
  export is meant to be portable and may be shared.

## Verified as correct

- Every source type (folder, Obsidian, Notion, MarginNote 4, GitHub, GitHub Deep) reaches Evidence
  only through `ingest.evidence_for` in `_sync_locked`, which now always passes through
  `contain_credentials`; the duplicate-delta path sweeps through `_sync_unchanged`.
- Withheld items with a previous version retract it under the would-be record id; sweep retractions
  use `credential-withheld:<id>`; both are deterministic, included in `PendingSourceState.expected_ids`,
  idempotent, and validate under `RecordSet.validate()` (single successor, later `recorded_at`, same
  type), including retraction chains and retraction-of-retraction.
- Evidence-derived Profile Facts (ADR-0028/0029) of withheld or swept Evidence leave `exposable()` and
  `current_facts()` without a Fact retraction that would copy text, and are re-derived after a clean
  edit.
- All MCP content tools (`aptuni_search_context`, `aptuni_activate_context`,
  `aptuni_get_identity_card`, `aptuni_get_memory_review`) and the public SDK reach `pack_units`;
  `aptuni_activation_status`, `aptuni_health`, `aptuni_activation_disable` and proposal responses
  carry no record text; the proposal rejection message is content-free. `ContextUnit.payload()` has
  `text` as its only free-text field, so checking `text` is sufficient.
- Host proposals use the union of the new detector and the earlier protected patterns.
- `doctor` prints ids, source ids, state and rule kinds, never text.

## Verdict rationale

The guard architecture is sound: one ingest choke point, deterministic and crash-safe retractions,
implicit withdrawal of derived Facts, and a last-line Context filter on the only free-text payload
field. It does not yet meet its own contract: common Markdown and JSON credential layouts still reach
Agents (B1), three paths still duplicate secrets into new canonical records — one of them into
current records (B2), and the owner has no way to locate a withheld item (B3). Each fix is small and
local; a narrow re-review of B1–B3 suffices.

**Verdict:** **BLOCK**

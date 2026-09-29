# Evidence-derived Profile report

Status: Reviews 82 and 83 remediated; Review 84 APPROVE_WITH_NON_BLOCKING_NOTES; checkpointed locally.

## Root cause

The source pipeline ended at canonical Evidence. Automatic Memory promotion consumed only explicit
owner interactions, while automatic Profile promotion consumed only owner-pinned Memory. The
owner's Vault therefore held 26,932 source Evidence records but no source-derived Profile.

## Implemented behavior

- `studied`, `applied` or `demonstrated` Evidence becomes an active
  `profile.evidence_signal` Fact only when the source has the exact `<module>.<signal>` authority.
- Fact and schema-v3 policy promotion event are written atomically with deterministic IDs. A Fact
  is algorithmically accepted and usable immediately; it never enters a human approval queue.
- Plain `exposure` never becomes a durable Fact or proficiency assertion. Profile activation can
  retrieve permitted Evidence, providing useful cold-start context without changing its meaning.
- Source Evidence does not become Memory. Memory remains a record of interactions and shared work.
- Source updates replace derived Facts, source loss/removal hides them, and privacy purge follows
  their provenance. The owner actions are reject/edit; a correction remains authoritative
  over later source changes.
- `aptuni profile refresh` and an unchanged re-sync backfill eligible existing strong Evidence.
  Guided setup grants MarginNote study notes `knowledge.studied` authority.

## Verification

The focused behavior, activation, setup, source, Profile, Obsidian, evaluation, Context, export,
privacy-purge and source-removal suites pass. The full repository pytest run, `ruff check .`, and
strict `mypy src` are green. Added tests cover authority/no-authority, active-without-acceptance,
idempotent backfill, source correction/loss/removal, owner reject/edit/override, cold-start Profile
Evidence retrieval, setup authority and invariant tamper rejection.

## Review 82 remediation

- B1 lineage: a source change writes the successor Fact (`supersedes` = the nearest earlier derived
  Fact, change kind mirrored); an owner reject or edit anywhere in the lineage is permanent; `accept`
  is refused with `profile_action_unsupported`.
- B2 admission: `aptuni.domain.evidence_profile` is the single canonical derivation, enforced by the
  Vault invariant for incremental commits and `doctor` (allow-list, ids, digest, time, confidence,
  lineage).
- B3 consent: the MarginNote setup step carries `primary_for`, digest-bound and rendered in en/zh;
  older plans stay reference-only; setup never upgrades an existing source.
- B4 migration: `aptuni source authorize SOURCE_ID --grant knowledge.studied` (preview, typed APPLY,
  stale-safe, idempotent) records a schema-v3 owner grant, re-derives current Evidence as `studied`
  corrections and forms Facts in one commit.
- B5 scale: indexes built once. 27k MarginNote items: promoting sync ~5.6 s, grant ~4.3 s, no-op sync
  ~3 s, `doctor` ~3 s (previously ~9 min extrapolated). 25k regression in the suite.

## Existing owner Vault

No live private record was changed. Its MarginNote source carries exposure-only Evidence and empty
authority. After re-review and a local checkpoint, the owner can back up and run
`aptuni source authorize <marginnote source id> --grant knowledge.studied`; the preview shows the
item count and nothing changes without APPLY. Other sources stay reference-only Evidence that
Profile activation can still retrieve.

## Remaining gate

ADR-0028 changes canonical review semantics and source-derived disclosure, so project policy
requires an independent correctness/privacy/compatibility review before checkpoint or release.

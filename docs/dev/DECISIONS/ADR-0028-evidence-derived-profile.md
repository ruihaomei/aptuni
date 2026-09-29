# ADR-0028: Build cold-start Profile automatically from authoritative Evidence

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** maintainer (reconfirmed original product intent) · implementing agent
- **PRD refs:** §1, §7, §16, §23
- **Builds on:** ADR-0006, ADR-0012, ADR-0018, ADR-0020, ADR-0025
- **Supersedes in part:** ADR-0006's blanket “no direct source-to-Profile mutation” and ADR-0020's
  claim that only pinned owner-declared Memories may create Profile Facts. Providers still write
  Evidence only; the canonical policy layer may now derive the bounded Fact below from admitted
  Evidence in the same atomic source commit. ADR-0020 remains unchanged for Memory-derived facts.
- **Needs maintainer confirmation:** no — the maintainer explicitly made this decision on 2026-09-29

## Context

The PRD promises a cold-start Profile built from user-authorized sources and retrospective review
after automatic promotion. Production source sync currently stops at Evidence. Interaction Memory
can auto-promote from an owner observation, and a pinned Memory can become a Fact, but no path turns
source Evidence into Profile. A real Vault therefore accumulated 26,932 Evidence records while its
Profile and Memory still contained only activation fixtures.

## Decision

1. Source Evidence and interaction Memory remain different. Source Evidence forms Profile Facts;
   it never becomes Memory merely because it was ingested.
2. Sync automatically creates an active `profile.evidence_signal` Fact only when Evidence carries
   `studied`, `applied` or `demonstrated` and the exact approved SourceConfig authority names
   `<module>.<signal>`. Plain `exposure` never creates a Fact and never implies expertise.
3. The Fact has one exact Evidence link, preserves module/source/observation time, uses a bounded
   signal-only statement, and is committed atomically with a schema-v3 `policy_auto/promote` review
   event targeting that Fact. IDs are deterministic, so crash replay is idempotent.
4. A source correction creates a successor Fact. The predecessor is the derived Fact of the nearest
   earlier Evidence version of the same source subject (resolved against the pre-delta snapshot);
   the successor supersedes it and mirrors the Evidence change kind (`correction`/`world_change`).
   With no such Fact it is an `assert`. A retraction or source removal makes an Evidence-derived Fact
   non-current/non-exposable when it has no current supporting Evidence. History is preserved.
5. Facts are algorithmically accepted and active immediately. They do not enter a per-item approval
   queue. The owner-facing actions are reject and edit; `accept` is refused
   (`profile_action_unsupported`) rather than reporting a second approval. Editing creates a
   user-declared correction and keeps the original lineage. An owner rejection or edit of any Fact
   in an Evidence lineage is permanent for every later version of that source subject: sync and
   `profile refresh` never recreate it. A privacy purge of such a Fact (or of the owner's edit, or
   any Fact in its successor chain) is the same permanent withdrawal: the writer checks the
   deletion ledger for the lineage's deterministic ids, so it never re-derives a purged id and the
   source keeps syncing (Review 83 B1).
6. `aptuni.profile` may retrieve relevant permitted Evidence as cold-start material as well as
   Facts. This does not weaken explicit activation: Aptuni stays OFF until Profile is invoked, and
   host grants still require `evidence.read`.
7. Guided setup records MarginNote `study-notes` as primary for `knowledge.studied` only through
   the confirmed plan: the authority is part of the digest-bound step target and the confirmation
   says, in English and Chinese, that studied topics are added to Profile automatically. A plan
   confirmed before this decision has no authority key and is applied with exactly the
   exposure-only meaning it was confirmed with. Setup never upgrades an existing source; a differing
   authority stops with `setup_source_authority_differs` and names the command below. Other
   providers remain exposure-only unless their exact source configuration grants a stronger dimension.
8. An existing source is upgraded only by `aptuni source authorize SOURCE_ID --grant
   knowledge.studied` (MarginNote only; the one grant whose ingest emits the signal). The preview is
   digest-bound to the source, dimension and exact current Evidence ids and writes nothing; only a
   typed `APPLY` applies it. One commit writes a schema-v3 `review_event`
   (`accept`/`user_cli`/`source_authority_studied`, target = source id), re-derives every current
   Evidence item as a `correction` carrying `studied` (the exposure item stays as history; the
   source keeps its id and sync state), and forms the Profile Facts. The source's effective authority
   is its approved `primary_for` plus its grants; later syncs emit `studied`. Declining changes
   nothing. A second grant, a grant after removal, or a grant for another source type is invalid.
9. The Vault invariant enforces the whole derivation, not only the writer: the strongest-signal
   allow-list (`demonstrated|applied|studied`, never `exposure`) against effective authority; the
   deterministic Fact/event ids (hence one Fact per Evidence); the event digest, nonce and epoch;
   exact valid time, confidence, statement, provenance and retention; and the exact lineage
   supersession of item 4. Incremental commits and full `doctor` share one index-backed check.
10. Derivation and validation are linear: indexes over supersession, owner decisions and grants are
   built once per snapshot, and a batch commits once. At 25k Evidence the promoting sync, backfill,
   no-op sync and `doctor` each take seconds (`tests/integration/test_evidence_profile_scale.py`).

## Rejected alternatives

- Auto-promote every excerpt or mention: floods Profile and violates the unsupported-claim guard.
- Put source documents into Memory: collapses the mandatory Profile/Memory distinction.
- Require per-item acceptance: recreates the onboarding bottleneck this decision removes.
- Let a model's confidence approve claims: confidence never overrides source authority.

## Compatibility and verification

ReviewEvent v3 (Evidence promotion and owner authority grants) is a clean fail-closed signal to
older builds. Review 82 blocked the first implementation on lineage, admission, consent, migration
and scale; Review 83 on a purge that froze sync. Items 4, 5 and 7–10 record the remediation. Test authority/no-authority,
unsupported exposure, atomic/idempotent sync and replay, correction/retraction/source removal,
module switches, retrospective reject/edit, Context review markers, Profile activation Evidence,
setup authority, privacy purge, export/index rebuild and full Vault validation.

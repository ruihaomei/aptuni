# ADR-0029: General Knowledge Evidence Model — authority as ceiling, item-level classification, derived Knowledge State

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** maintainer (design brief “知识层级设计 prd 构想_初步”, 2026-09-30) · implementing agent
- **PRD refs:** §1, §7, §16, §18, §23; design rationale “Knowledge evidence”
- **Builds on:** ADR-0005, ADR-0006, ADR-0015, ADR-0028
- **Amends:** ADR-0028 items 2 and 8. Source authority no longer stamps a signal on every item of a
  source; it is the ceiling a per-item classifier may reach. `source authorize` re-derives items
  through the classifier instead of relabelling them all.
- **Needs maintainer confirmation:** no — the maintainer supplied the design brief and asked for it

## Context

ADR-0028 made source Evidence form Profile Facts, but the only producer of a strong signal was a
source-wide label: once MarginNote was authorised for `knowledge.studied`, every one of User #1's
26,417 concept cards became `studied`, including isolated one-line cards, and the Profile gained
26,415 near-identical `Studied …` Facts. GitHub, the most objective source of hands-on evidence,
could only emit `exposure` for whole files. Profile activation then returned individual Facts
ranked by lexical match, so a task about XGBoost saw a handful of `Studied …` lines instead of what
the Evidence says as a whole.

## Decision drivers

- No over-claim: a mention, an import or a single highlighted card is not study or application.
- Provenance and owner control stay exactly as in ADR-0028 (lineage, reject/edit, purge).
- Local-first and deterministic: no model judges a signal.
- Progressive disclosure: an Agent gets a compact, cited summary per concept, not thousands of rows.
- A migration path for the real Vault that the owner confirms.

## Decision

1. **Canonical dimensions are unchanged and source-agnostic:** `exposure`, `studied`, `applied`,
   `demonstrated`. No proficiency score is stored anywhere.
2. **Authority is a ceiling (`may_emit`).** A source's effective authority (approved `primary_for`
   plus owner grants, ADR-0028 item 8) lists the `<module>.<signal>` dimensions its items *may*
   carry. `exposure` is always allowed. A per-item classifier decides the signal; the emitted signal
   is the classifier's judgement capped at the ceiling. The Vault invariant now enforces the ceiling
   on every committed Evidence record (closing Review 83 N3): a non-exposure signal outside the
   source's effective authority is refused. Classifier correctness is writer-enforced and tested.
3. **The classifier reads only what the Evidence locator records**, so the same judgement can be
   recomputed from the Vault alone (for re-derivation) and at sync time. Classifier v1:
   - *MarginNote 4* (`marginnote.locator@2`, which gains an `annotated` count): a concept card is
     `studied` when it organises sub-concepts (`child_count ≥ 1`), collects at least two further
     excerpts (`excerpt_count ≥ 2`), or carries the owner's own annotation (`annotated ≥ 1`);
     otherwise it is `exposure`. For Evidence written before this ADR, whose locator has no
     `annotated` field, the count is read from Aptuni's own structured summary (`N annotated`) when
     present and is otherwise 0 — the conservative direction.
   - *GitHub Standard* gains **concept items** (`github.concept@1`, one per resolved concept per
     repository) next to its file items. Each records a usage level from the selected files:
     `applied` (the file imports the library *and* constructs or calls it, e.g. `XGBClassifier(` with
     `.fit(`), `imported`, `declared` (a manifest lists the package) or `mentioned` (README/docs).
     Only `applied` may become the `applied` signal, and only under a `knowledge.applied` ceiling;
     every other level, and every file item, is `exposure`. No code text is stored: the excerpt
     names the level, counts and at most five paths. GitHub Standard never emits `demonstrated`.
   - Folder, Obsidian, Notion and GitHub Deep stay `exposure` in this ADR.
4. **Declared ceilings per source type** (only the first two have producers today):

   | Source | may emit | Notes |
   |---|---|---|
   | MarginNote 4 study notes | exposure, studied | grant `knowledge.studied` |
   | GitHub Standard repository | exposure, applied | grant `knowledge.applied`; demonstrated needs a stronger output (future Deep/release evidence) |
   | Coursework / publication / competition | up to demonstrated | future providers |
   | CV / application materials | owner-declared claims | `user_declared` trust; corroborated by, never equal to, external demonstration |
   | Notion | by semantic role (reading notes → studied; design doc → applied; TODO → nothing) | future; exposure today |

5. **Grants.** `aptuni source authorize SOURCE_ID --grant knowledge.applied` is added for GitHub
   Standard sources (schema-v3 grant, rationale `source_authority_applied`), beside
   `knowledge.studied` for MarginNote. Both preview and apply **re-derive through the classifier**:
   only current items whose classified signal under the new ceiling differs are written as
   corrections; the rest stay untouched. A grant with nothing to re-derive still records the
   ceiling so later syncs use it.
6. **Owner-confirmed migration.** `aptuni source reclassify SOURCE_ID` previews, digest-bound to
   the exact current Evidence ids, how many items the current classifier would change and in which
   direction, and writes only after a typed `APPLY`. Each change is a `correction` of the current
   Evidence version (history kept); a downgrade leaves the earlier Evidence-derived Fact without
   current support, so it is no longer current or exposable (ADR-0028 item 4); an upgrade forms a
   Fact through the ordinary ADR-0028 path. Owner rejections/edits/purges in a lineage stay final.
   Nothing reclassifies silently during sync; sync applies the classifier only to new and changed
   items.
7. **Concept resolution** (`aptuni.knowledge.concepts`) maps Evidence to canonical concepts: a
   curated registry of concepts with aliases, import roots, package names and usage calls
   (`XGBoost`, `xgboost`, `XGBClassifier` → `ml.xgboost`); a MarginNote card resolves by its leaf
   label, GitHub concept items by their concept id, owner-declared Facts by registry aliases in
   their statement. A label that matches no registry entry becomes its own normalised
   `label:<text>` concept so identical card titles across notebooks still aggregate. Resolution is
   deterministic and a projection: it never changes canonical records.
8. **Knowledge State is a derived projection**, recomputed from exposable records (cached per Vault
   sequence) and never stored canonically. Per concept it reports counts per dimension, distinct
   sources/contexts per dimension, owner-declared claims separately, and supporting Evidence ids.
   Its **evidence level** is a six-step ladder read directly from those counts: `unknown`,
   `exposed`, `studied`, `practiced` (≥1 applied context), `strongly_practiced` (≥2 distinct applied
   contexts), `demonstrated` (≥1 demonstrated). Owner-declared claims never raise the level. The
   level is labelled everywhere as derived from Evidence, not a proficiency measure; no numeric
   score exists. Task-specific Working Familiarity weighting and recency are deferred until
   providers record activity time and real owner-labelled trials exist.
9. **Profile activation is compact.** `aptuni.profile` prepends at most five L2
   `knowledge_state` units (concepts named in the query first, then concepts of the best matches),
   each citing its supporting ids, and omits the individual Evidence and Evidence-derived Facts
   those units already summarise. Owner-declared Facts and unrelated records are still listed.
   `aptuni knowledge [QUERY]` shows the same projection to the owner.

## Options considered

- **Keep source-wide labels, add a per-concept score.** Rejected: a stored score is uninterpretable
  and would harden the 26k over-claims.
- **Let a model classify items.** Rejected: non-deterministic, not local-first by default, and a
  confidence never overrides authority (ADR-0028).
- **Store Knowledge State canonically.** Rejected: it is a function of Evidence; storing it would
  create a second truth to migrate.
- **Reclassify automatically on sync.** Rejected for the migration: a 26k-item canonical change must
  be owner-confirmed; sync only classifies what changed.
- **File-level GitHub `applied`.** Rejected: “Applied src/train.py” names no knowledge.

## Consequences

- **Positive:** Profile Facts now mean something item by item; GitHub contributes objective applied
  evidence; Agents get one cited line per concept; the ceiling is enforced by the Vault.
- **Negative / risks:** thresholds are heuristics (v1) — changing them needs an amendment and real
  owner evidence. Unregistered library use is not detected as `applied`. Pre-ADR MarginNote Evidence
  stays over-classified until the owner runs `source reclassify`.
- **Follow-ups (BACKLOG):** setup offering `knowledge.applied` for GitHub; activity time in locators
  for recency; task-specific familiarity lenses; Notion semantic roles; demonstrated evidence from
  releases/publications; a classifier-bound invariant once legacy Evidence is migrated.

## Verification

Unit tests for the classifiers, resolver and level ladder; integration tests for MarginNote item
classification at sync, GitHub concept items (applied vs imported vs declared, ceiling, removal,
no code text), `source authorize --grant knowledge.applied`, `source reclassify` (preview writes
nothing, stale digest refused, downgrade hides Facts, upgrade forms Facts, owner decisions kept,
idempotent), the ceiling invariant, Knowledge State aggregation across MarginNote + GitHub +
owner-declared Facts, and compact `aptuni.profile` output. The migration is exercised on a scratch
copy of a Vault shaped like User #1's.

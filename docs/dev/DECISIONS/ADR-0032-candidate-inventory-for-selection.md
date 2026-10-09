# ADR-0032: Tell the Agent which candidates exist before it chooses among them

- **Status:** Accepted — maintainer accepted in chat on 2026-10-09 ("接受 ADR-0032，打 tag 发布
  0.2.0b10") after the owner approved the privacy surface in principle ("同意，开始产品化"),
  Review 114 and the production-path confirmation
- **Date:** 2026-10-09
- **Deciders:** maintainer (final say) · implementing agent · independent reviewer
- **Builds on:** ADR-0005 (Context API, MCP tools, progressive disclosure), ADR-0025 (explicit
  activation), ADR-0030 (host concepts), ADR-0031 (credentials out of context)
- **Research refs:** `docs/dev/b10-continuation/candidate-inventory-results.md` and metrics;
  `r1-localization-results.md`; `r1-stage-followup.md`
- **Needs maintainer confirmation:** no for this decision; the per-source "hide from inventory"
  switch (item 9) remains a separate follow-up

## Context

"Choose the two best projects / experiences / subjects from my history" is a core Aptuni use case.
Until now the only retrieval primitive was relevance search. For unnamed candidates the Agent
had to guess words that the right records happen to contain. Quality words rarely occur, broad
artifact words are swamped by study notes (98.7% of User #1's 49,734 exposable records), and
packet widening saturates. On fresh real tasks, ordinary b10 retrieval failed with R1 (candidate
not returned) in 7 of 12 Codex/Claude sessions.

A research seam that first *listed* the authorized candidate entities per category, then fetched
Evidence for the Agent's chosen IDs, was evaluated on a fresh, independently audited six-task
real set, graded blind across two model families:

| Fresh six | Codex A → I | Claude Sonnet 5.5 A → I |
|---|---|---|
| Strict E2E | 3/6 → 6/6 | 0/6 → 3/6 |
| Eligible selection | 3/6 → 6/6 | 1/6 → 6/6 |
| Audited pool recall | 9/16 → 16/16 | 3/16 → 15/16 |
| R1 / R2 failures | 2 / 1 → 0 / 0 | 5 / 1 → 0 / 0 |
| Task tokens | +26% | +58% |

The remaining Claude-I misses were two length-limit overruns and one answer naming inventory
items it never fetched Evidence for. Regression on six ordinary tasks was unchanged (Claude A 5/6,
I 5/6, silent on both self-contained tasks).

## Decision drivers

- Fix unnamed selection by telling the Agent what exists, not by making it guess.
- No new authorization: the inventory is a new *shape* of disclosure inside the existing explicit
  Full session and grant, never a new scope, module or OFF→Full path.
- No storage, index or schema change. The inventory is derived per call from canonical provenance.
- Bounded and category-scoped. Never a whole-Vault dump; ordinary tasks keep the existing path.
- One tool surface for hosts. Existing allowlists stay valid.

## Options considered

### Option A — modes on `aptuni_search_context` (chosen)
Add `mode` (`search` default, `inventory`, `evidence`), `categories` and `candidates`.
**+** This is what was validated. Host tool allowlists and bundles keep four tools, and the default
behaviour is unchanged. **−** One tool carries three shapes. The description must stay clear.

### Option B — two new tools (`aptuni_list_candidates`, `aptuni_get_candidate_evidence`)
**+** Simpler per-tool schemas. **−** Every host allowlist, bundle and research harness changes.
This shape was not validated.

### Option C — semantic recall (local embeddings)
Not needed: the inventory removed R1 on fresh data. It stays the next option for entities inside
long multi-topic documents (Folder/GitHub files keep only the first 280 characters), which is a
corpus-depth limit of every path.

### Option D — persistent entity database or ontology
Rejected: provenance already identifies the entities; a second store adds migration and
staleness without measured benefit.

## Decision

1. **Candidate entities** are derived per call from current, exposable Evidence in the requested
   modules, using locator provenance only:
   - `repositories`: `github.locator`, `github.concept`, `github.activity` Evidence grouped by
     (source, `repository_id`). Label: repository name from `owner_name` (`owner/name` grammar).
     Optional `about`: at most 90 UTF-8 bytes of the shallowest README Evidence, with markup removed.
   - `documents`: `folder.locator` / `obsidian.locator` grouped by (source, `relative_path`), label
     = path without extension; `notion.locator` grouped by (source, `entity_id`), label = `title`.
   - `subjects`: `marginnote.locator` v2 root topics grouped by root title (case-folded) across
     notebooks and sources, so one subject studied in several notebooks is one candidate with all
     its Evidence. Size = the largest depth-0 descendant count; at least 20; top 100 by size.
     Label = the root title.
   A candidate is an entity cue, not proof of the user's work. The Agent merges entities that
   several repositories or notebooks document.
2. **Candidate IDs** are `c` + category letter (`r`/`d`/`s`) + `-` + the first 12 hex digits of
   SHA-256 over (source ID, category, grouping key); subjects use an empty source. They are stable
   across calls and snapshots while the entity exists and need no session state. They are
   unsalted: an ID discloses nothing beyond its inventory row, but the same entity has the same ID
   for every host of one owner, and a low-entropy key (a repository number, a common path) can be
   confirmed offline by someone who already guesses it. A per-Vault salt is a follow-up if
   cross-host linkability ever matters.
3. **`mode="inventory"`** requires an explicitly enabled Full session (ADR-0025), the grant's
   `context.read` and `evidence.read` scopes and the requested modules. It requires 1–3 distinct
   `categories` and no `concepts`/`candidates`. Each category is one or more L4 units
   (`kind="candidate_inventory"`, `tainted=true`) holding JSON rows `{id, label, about?|evidence|notes}`.
   Rows are packed in order until the budget is reached; a row that would make the accumulated
   unit look like a credential is skipped rather than letting the last-line guard drop the whole
   category. Any omission, including a later category that no longer fits, sets `truncated`. In
   these modes `query` states the task; `concepts` must be absent and `include_evidence` is unused.
4. **`mode="evidence"`** has the same authorization and takes 1–6 distinct candidate IDs. It
   recomputes the inventory from the current snapshot, so a stale, hidden, withdrawn or unknown ID
   returns nothing for that ID and never errors in a way that reveals existence. It returns at
   most 3 Evidence per candidate, round-robin: shallowest README first for repositories, root card
   then broadest descendants for subjects, stable order otherwise. Results are ordinary
   `record_unit`s with canonical IDs.
5. **Bounds:** `max_units` as for search (default 1500, maximum 100,000). Guidance asks for about
   20,000 units for inventory and 10,000 for Evidence. Concept search keeps its retry rule. An
   unnamed-selection task uses one inventory call, then at most two Evidence calls.
6. **Guards unchanged and reapplied:** only `RecordSet.exposable()` Evidence (current, accepted, not
   revoked, module exposed) contributes. Evidence containing a credential is excluded before
   grouping, every row is credential-checked before disclosure, and `pack_units` keeps the ADR-0031
   last-line guard. A final snapshot check discards the response if the Vault changed. Nothing is
   logged or stored.
7. **Guidance** (the generated Full skill for both hosts, because only an explicitly enabled Full
   session can list candidates, and the `aptuni_search_context` description):
   use inventory → Evidence only to choose, rank, shortlist or compare the user's own prior items
   that the request does not name. Labels are clues. Judge eligibility only from returned Evidence.
   Name as the user's items only candidates whose Evidence was fetched. Keep the requested length.
   Every other task uses ordinary concept search.
8. **Unchanged:** default `mode="search"` behaviour, `aptuni_activate_context`, Profile/Memory
   intents, grants, activation, storage, index, schema and the developer SDK (ADR-0024). The
   inventory is not added to the SDK in this ADR.
9. **Privacy surface and follow-up:** an inventory call discloses, in breadth, the existence and
   names of authorized repositories, document paths and large study topics, independent of query
   relevance. All of these are already retrievable under the same grant. Owners control exposure
   per module and can remove sources (ADR-0027). A per-source "hide from inventory" switch would
   need a source-config field; it is deferred to an owner decision rather than added silently.

## Consequences

- **Positive:** unnamed selection becomes a choice problem; R1 removed on fresh data for two
  model families; no new store or dependency; existing hosts keep their four tools.
- **Negative / risks:** more tokens per selection task (+26–58% measured); paths and titles can
  themselves be sensitive (mitigated by explicit Full, category scoping, guidance limiting use to
  selection tasks, module exposure control and source removal); Agents may cite unfetched labels
  (guidance item 7; tested in confirmation); 280-character file excerpts still hide deep content.
- **Follow-ups:** owner decision on per-source inventory hiding; compact document rows if cost
  matters; Folder Evidence depth (chunked excerpts) as a separate ADR if real tasks need it.

## Verification

- Unit/integration tests: OFF refuses; grant scope/module denial; hidden-module, withdrawn and
  credential-bearing Evidence never contributes a row or label; credential-like labels dropped;
  stable IDs across calls; unknown or stale IDs return nothing; per-candidate cap and round-robin;
  budget truncation; snapshot change discards; default search unchanged; MCP schema validation.
- Independent review (privacy, MCP contract): Review 114, approve with non-blocking notes; N1
  (category emptied by a joined-unit credential match), N2 (ADR/docstring wording, subject
  merge), N3 (tool description), N4 (unsalted IDs, documented) and N5 (adversarial tests: server
  without required activation, task-scoped Full, stale vs unknown IDs, credentials in evidence
  mode, multi-category budget) were addressed before the confirmation; N6 is in HANDOFF.
- Fresh confirmation on the production path (Codex and Claude) plus ordinary/silent regression
  before any b10 release decision.

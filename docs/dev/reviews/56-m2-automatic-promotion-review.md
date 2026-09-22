# Milestone 2 automatic promotion and retrospective review

**Reviewer:** independent Claude subagent review of slices A–C (A and B committed, C uncommitted)

## Scope

Reviewed the eligibility rule table and derived review state (`src/aptuni/policy/promotion.py`),
the promotion records and review operations (`src/aptuni/application/review_commands.py`), the
`observe` promotion path and the `_decided`/`_revoked` split
(`src/aptuni/application/memory_commands.py`), `ReviewEvent` v2 / `ReviewPolicy` / per-record-type
`parse_record` (`src/aptuni/domain/records.py`), the shared derivations and admission rule
(`src/aptuni/domain/invariants.py`), the CLI (`src/aptuni/cli/memory_cli.py`), and the four test
files. Checked against `AGENTS.md`, ADR-0018, ADR-0011, ADR-0013 and the accepted plan.

## Verdict on the first submission

**BLOCK**, on six findings. All six are now remediated test-first.

## What held under direct attack

The two highest-risk claims in the slice were both verified sound, and neither needed a change.

- **Nothing is promoted that ADR-0018 says must be confirmed.** The reviewer tried episode
  spoofing, `principal` manipulation, idempotency-key collision and a candidate whose
  `derived_from` mixes CLI and host observations. A Memory is constructed in exactly three places;
  `promotion_records` has exactly one caller; `_owner_stated` demands `trust="user_declared"` *and*
  episode `cli` for **every** support, both derived from `origin`, which no MCP tool exposes. A
  host origin always yields `mcp:<principal>`, never `cli`. `expose_enabled=false` and
  `ingest_enabled=false` deny rather than ask; sensitive modules and live contradictions ask.
- **MCP cannot promote (ADR-0013 item 1).** The server exposes only `health`,
  `get_identity_card`, `search_context` and `propose_memory`; no review, approve or commit tool
  exists, and `propose_memory`'s `"status": "pending_owner_review"` is accurate for every
  reachable input.
- **No consumer of the old revocation rule was missed.** Every derivation of
  withdrawn/revoked/decided in `src/` now routes through `RecordSet.revoked_ids()` or
  `decided_candidate_ids()`, or uses the corrected `{"reject", "revoke"}` set directly.

## Blocking findings, all remediated

| # | Finding | Remediation |
|---|---|---|
| **B1** | `edit` left the replaced memory in the Profile export: `current_memories` had no supersession filter, and the correction inherits the original's `candidate_id`, so both rows passed. The owner's readable copy showed a statement they had corrected away. | Export now drops superseded memories, agreeing with `exposable()` and `memories()`; regression added |
| **B2** | `accept`/`reject`/`pin` were not idempotent once pinned. The guard compared a *collapsed* state, and `pin` outranks `accept` in that collapse, so a pinned memory never read back as `"accepted"` — three repeats appended three canonical events, and `--json` reported a state the ledger did not support. | Idempotence is decided from the events already on the memory, and the return value is re-derived after the commit; regression added |
| **B3** | A reminder marker holding a *naive* timestamp parsed cleanly and then raised `TypeError` on comparison, surfacing as "the Vault … could not be read safely" — wrong and unactionable. An aware far-future marker suppressed reminders forever with no way to clear it. | A naive timestamp now counts as unreadable; `clear_review_snooze()` and `aptuni memory review snooze --clear` added; regression added |
| **B4** | The reminder existed only in its own command, which an owner has no reason to run unless they already know there is something to review. ADR-0018 §6 and the plan both require it in `status` and `doctor`; as shipped the owner was never reminded. | Both now print one line when a reminder is due, and `status --json` carries the review block; regression added |
| **B5** | The Context API carried no `review_state`, so an agent could not tell an auto-promoted, unreviewed memory from an owner-confirmed one. ADR-0018 §3 names the Context API explicitly. | `ContextUnit` carries `review_state` and the payload includes it for memories; regression added |
| **B6** | `edit_memory` never checked `can_ingest`, so a correction wrote new content into a module that had stopped accepting information — while `observe`, `remember`, `correct` and `decide_memory` all enforce it. | `edit` now enforces `ingest_enabled`; withdrawal paths deliberately still do not; regression added |

## Non-blocking notes and their disposition

| Note | Disposition |
|---|---|
| N1 — `_proposal_for` took the first memory sharing a candidate id, so a repeated `observe` after an edit reported the superseded original | **Fixed**; regression added |
| N2 — the Mem0 rebuild projected a superseded memory, keeping corrected-away text in the local projection | **Fixed**; regression added |
| N3 — editing an already-superseded memory leaked an internal invariant message and a record id | **Fixed**: `_reviewable` refuses it with a plain `memory_not_current`; regression added |
| N4 — an unknown `record_type` (`review_policy`) fails in the discriminated union rather than as `SchemaVersionError` | **Documented** in ADR-0018 §7 as a legible-failure follow-up; the failure is still closed |
| N5 — ADR §8 says MCP never triggers a promotion evaluation, but the guarantee rested on two field values | **Fixed**: a structural gate skips the evaluator entirely for a non-CLI origin; regression added |
| N6 — the privacy purge scope had no `accept`/`pin` regression | **Fixed**; regression added |
| N7 — a tautological search assertion | **Fixed** |
| N8 — plan cases 13 and 17 have no direct test | Backlogged; the reviewer verified both behave correctly |
| N9, N11 — the ADR named `aptuni review …` and an interval measured "since the last reminder" | **Corrected** in the ADR: the commands live under `memory` because top-level `review` is taken, the interval runs from the oldest pending memory, and the snooze is checked before the threshold, with the reasoning recorded |
| N10 — `DEFAULT_REVIEW_POLICY` captured `utc_now()` at import | **Fixed**: fixed timestamp |
| N12 — the reminder directory kept its old mode if it already existed | **Fixed**: unconditional `chmod` |
| N13 — the checkpoint must record that slice D is not implemented | **Done** in `STATE.md` and `HANDOFF.md` |
| N14 — only `pin` writes schema v2 | **Kept**, now with a comment explaining why |

## Slice D is deliberately not in this checkpoint

The MCP read surface for the pending set and the reminder, and the negative regression proving the
approve/commit service is unreachable from any MCP handler, are plan slice D and are **not
implemented**. Nothing in the product or the documentation claims otherwise. The reviewer verified
by inspection that MCP cannot promote today; the structural gate added for N5 makes that cheaper to
keep true, but the regression that pins it is still owed.

## Evidence after remediation

Full gate: 598 tests plus 47 subtests, 3 optional-runtime skips; Ruff, strict mypy (74 source
files), relay and the notices/secrets/workflow supply-chain checks clean; the frozen evaluation
passes with unchanged metrics. CLI dogfood: `observe` reports the memory as in use and names the
undo command; `status` and `doctor` both show the reminder when due, fall silent after
`snooze`, and speak again after `snooze --clear`; `edit` leaves exactly the correction in
`memory list`; switching promotion off restores the confirmation path.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

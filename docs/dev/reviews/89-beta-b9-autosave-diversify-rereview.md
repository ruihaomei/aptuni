# Review 89 — 0.2.0b9 candidate re-review: host auto-save cap, truthful MCP status, exact-first Context

- **Scope:** remediation commits `6c648c8` and `c1ba630` on top of `c2df17a`, answering Review 88
  (`88-beta-b9-autosave-diversify-review.md`, BLOCK): `application/memory_commands.py`
  (`_open_host_items`), `mcp/server.py`, `retrieval/sqlite.py` (`SearchRow.exact`),
  `application/service.py` (`context()`), `retrieval/diversify.py`, `cli/memory_cli.py`, the ADR-0005
  and ADR-0018 amendment text, BACKLOG rows and the new tests. The untracked `.agents/skills/`
  directory and the untracked Chinese-named `.txt` file are unrelated user files and were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** the Review 88 scratch probes were re-run unchanged against HEAD, plus one edge probe,
  all on temporary Vaults in the session scratchpad. The owner's Vault was not touched. No source or
  test file was modified.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest -q` | exit 0; 1134 passed, 3 skipped |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 120 source files |
| `python3.13 tools/check_relay.py` | relay check passed (after registering this review) |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true`; dev FPR 0.0, recall@5 0.992, MRR 1.0; holdout FPR 0.0, recall@5 1.0, MRR 1.0 |
| `python3.13 -m unittest discover -s tests/dev` | Ran 56 tests, OK |

## Resolution of Review 88

| Review 88 item | Status | Evidence |
|---|---|---|
| B1 per-principal cap bypassed by auto-save | **Fixed** | `_open_host_items` (`memory_commands.py:352-358`) adds the episode's `auto_promoted_pending_review` memories to its quarantined candidates. Probe: cap 3 with the option on → 3 saved, the 4th gets `memory_queue_full` (was 10 of 10). Owner review (accept, pin, reject, edit) frees a slot (probe: an owner edit takes the count from 1 to 0, because the edit records an `accept`). Regression `test_auto_saved_memories_awaiting_review_count_toward_the_per_agent_cap` |
| B2 misreported `saved_pending_owner_review` | **Fixed** | `server.py:214-216` requires `review_state == "auto_promoted_pending_review"`. Probes: option off + owner-accepted re-send → b8 shape `pending_owner_review`, no `memory_id`; option on + owner-rejected re-send → `pending_owner_review`. Regression `test_mcp_reports_saved_only_for_a_proposal_it_auto_saved` |
| N1 CLI wording | Fixed (CLI); consent text unchanged (N1 below) | `memory_cli.py:179-181` depends on `auto_promotion_enabled`; test extended |
| N2 re-consent of existing grants | Addressed by the maintainer's explicit in-chat request; the coordinator will show the setting before running it | — |
| N3 fallback rows lifted above all-keyword matches | **Fixed** | `SearchRow.exact` is `False` only for fallback rows (`sqlite.py:192-193`); `context()` diversifies exact rows and fallback rows separately, exact first (`service.py:539-544`). Probe: `markov chains`, `limit=2` → two all-term rows again (the unrelated `tennis chains` row is back after them); ADR-0005 amendment states this |
| N4 eval coverage | Documented in ADR-0005; BACKLOG row | — |
| N5 `。` normalization; Notion generic titles | `。` fixed with a unit test; Notion titles in BACKLOG | — |
| N6 invariants vs opt-in | BACKLOG row | — |

Re-verified unchanged behaviour: option off still never evaluates host proposals; expose/ingest
denials, `auto_promotion_enabled` off and sensitive modules still prevent saving; idempotent
re-proposal and key-reuse conflict hold; pinned, edited and refreshed host memories never become
Profile Facts; `vault().verify()` is clean after auto-saves; schema-1 policies stay byte-identical
and b8 still refuses schema 2 with `SchemaVersionError`; hidden-module records stay out of Context.

## Findings

### Blocking

None.

### Non-blocking

1. **N1 — Consent text still omits the conditions.** `consent.detail.memory.propose` (en, zh-CN)
   still says suggestions outside identity, relationships and behavior "are saved at once" without
   noting that automatic promotion must be on and that expose-disabled modules still ask. Fix the
   wording with the next consent-touching change.

2. **N2 — Cap cost grows with the host's memory history.** `_open_host_items` calls
   `review_state_of` (two full passes over the records) for every memory of that episode, including
   long-accepted ones, on each host proposal. On a Vault the size of the owner's (~50k records) and
   a few hundred host memories this becomes a noticeable per-proposal cost. Suggest one pass that
   indexes review events by target (the same pattern would also speed `pending_review_memories`).

3. **N3 — A still-pending auto-saved memory is reported after its module is hidden.** If the owner
   turns a module's exposure off, a re-send of an auto-saved, unreviewed proposal still returns
   `saved_pending_owner_review` with its `memory_id` (probe). The status is accurate and the host
   proposed that content itself, so nothing new leaks; optionally require the memory to be
   exposable before reporting it.

4. **N4 — No Context-level regression for exact-first ordering.** The new integration test checks
   `SearchRow.exact` at the projection only; a `context()` case with all-term repeats plus a fallback
   row (as in this review's probe) would pin the ordering contract in ADR-0005.

5. **N5 — Cosmetic:** two lines in the ADR-0005 and ADR-0018 amendments exceed the surrounding wrap
   width.

## Summary

Both blocking findings are fixed with regressions and confirmed by re-running the original probes:
the per-Agent cap again bounds opted-in auto-saves, and the MCP tool reports "saved" only for a
memory the policy saved and the owner has not reviewed, restoring the b8 response otherwise.
Context keeps all-keyword matches ahead of fallback rows. Remaining notes are wording, performance
and test-coverage follow-ups.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

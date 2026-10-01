# Review 88 — 0.2.0b9 candidate: host memory auto-save opt-in and Context concept diversification

- **Scope:** `git log v0.2.0b8..HEAD` on `main`: `3f44616` (owner opt-in host memory auto-save,
  ADR-0018 2026-10-01 amendment), `bc5a552` (CHANGELOG) and `c2df17a` (Context concept
  diversification, ADR-0005 2026-10-01 amendment), with their tests and docs. The untracked
  `.agents/skills/` directory and the untracked Chinese-named `.txt` file are unrelated user files
  and were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in the session scratchpad against temporary Vaults only; the
  owner's Vault was not touched. The b8 compatibility probe ran `git archive v0.2.0b8 src` from the
  scratchpad. No source or test file was modified.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest -q` | exit 0; 1130 passed, 3 skipped |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 120 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true`; dev FPR 0.0, recall@5 0.992, MRR 1.0 (58 queries); holdout FPR 0.0, recall@5 1.0, MRR 1.0 (15 queries). Note: the harness calls the projection directly, not `context()`, so it does not exercise diversification (N4) |
| `python3.13 -m unittest discover -s tests/dev` | Ran 56 tests, OK |

## Probes

| Probe (temporary Vaults) | Result |
|---|---|
| Opt-in on, `MAX_PENDING_PER_ORIGIN` patched to 3, 10 distinct host proposals | **All 10 saved** as exposable `auto_promoted_pending_review` memories; no `memory_queue_full` (B1) |
| Same with opt-in off | Refused at the 4th proposal with `memory_queue_full` (unchanged) |
| Opt-in on, same idempotency key twice / reused for another statement | Same `memory_id`, `created=False`, state `auto_promoted_pending_review` / `idempotency_conflict` |
| Opt-in on, `goals` expose off; then ingest off | Candidate stays pending, no memory (`module_expose_disabled` deny) / `module_ingest_disabled` |
| Opt-in on, `auto_promotion_enabled=False` | No memory (`auto_promotion_disabled`) |
| Opt-in on, sensitive module (`identity`) | No memory (covered by the shipped test too) |
| Host-saved memory pinned, then `refresh_profile()`; then edited and refreshed | No `profile.promoted_memory` Fact in either case (`not_owner_declared_cli`); ADR-0020 holds |
| Host-saved memory rejected | State `revoked`, no longer exposable |
| Reload with a fresh service + `vault().verify()` after host auto-saves and option off | `ok=True`, no invariant problems |
| Schema-1 policy `canonical_json` at HEAD parsed by b8 `parse_record` and re-serialized | Byte-identical |
| Schema-2 policy parsed by b8 | `SchemaVersionError: unsupported schema_version 2 (supported: 1)` (fails closed) |
| MCP `aptuni_propose_memory`, **opt-in off**, owner accepted the candidate in the terminal, host re-proposes | `status="saved_pending_owner_review"` with the `memory_id` (B2) |
| MCP, opt-in on, owner rejected the saved memory, host re-proposes; then module expose off | `status="saved_pending_owner_review"` with the revoked `memory_id`, in both cases (B2) |
| Context, `markov chains`, three all-term repeats + one any-term-only record, `limit=2` | Now returns `[all-term, any-term-only]`; b8 (search limit 3) would not have run the fallback and returned two all-term rows (N3) |
| Context with a matching record in an expose-disabled module | Not included; exposure filtering precedes diversification |

## Findings

### Blocking

1. **B1 — BLOCKING (security/contract): with the opt-in on, the per-principal proposal cap no
   longer bounds host writes.**
   `src/aptuni/application/memory_commands.py:160-161` checks `len(self._pending(records, episode))
   >= MAX_PENDING_PER_ORIGIN`, and `_pending` (`:347-350`) counts only candidates without any review
   event (`RecordSet.decided_candidate_ids`, `src/aptuni/domain/invariants.py:403-409`). An
   auto-saved host candidate carries its `policy_auto` promote event, so it is "decided" and never
   counts. Failure scenario: the owner turns `--host-proposals on`; a prompt-injected or looping
   Agent with `memory.propose` calls `aptuni_propose_memory` with distinct statements in any
   non-sensitive granted module; every call commits an Observation, a Candidate, a ReviewEvent and an
   immediately exposable Memory, without limit (probe: 10 of 10 saved under a cap of 3). The 200 cap
   is the only rate bound ADR-0005 (2026-09-20: "capped at 200 pending proposals per principal") puts
   on a host write path, and ADR-0018's amendment
   (`docs/dev/DECISIONS/ADR-0018-automatic-promotion-and-retrospective-review.md:203`) states that the
   per-origin pending limit still runs "as before", which is true in form but not in effect. The
   owner's accepted risk covers "a wrong Memory", not unbounded exposable writes that crowd later
   activations, inflate the review queue and, with whole-Vault revalidation per commit (KI-016), slow
   every command. Fix (small): in `observe()`, for `origin == "host"`, count the principal's
   undecided candidates **plus** its memories still in `auto_promoted_pending_review`
   (episode-matched) against `MAX_PENDING_PER_ORIGIN`; add a regression that patches the cap and
   shows the next proposal gets `memory_queue_full` with the opt-in on.

2. **B2 — BLOCKING (correctness/contract): `aptuni_propose_memory` reports
   `saved_pending_owner_review` for memories that were not auto-saved, including with the option
   off.**
   `src/aptuni/mcp/server.py:214` keys the new status on `proposal.memory_id is not None`. But
   `_proposal_for` (`src/aptuni/application/memory_commands.py:201-209`) also returns a `memory_id`
   on an idempotent re-proposal of a candidate the owner accepted in the terminal, or of a saved
   memory the owner has since rejected/revoked, with `review_state` `accepted` or `revoked`. Failure
   scenarios (probed): (a) default policy, owner accepted a proposal with `aptuni memory accept`, the
   Agent re-sends it: b8 answered `pending_owner_review`; HEAD answers `saved_pending_owner_review`
   plus the `memory_id`, so the default behaviour changed, contrary to the amendment ("the default is
   unchanged") and to its own condition ("when it saved"); (b) opt-in on, the owner rejected the
   saved memory, the Agent re-sends it: the tool says it is saved and pending review, so the Agent
   tells the user it saved something the owner explicitly withdrew. The response also discloses the
   owner's terminal decision and a memory id even after the module's exposure is turned off. Fix
   (small): return the saved status and `memory_id` only when `proposal.review_state ==
   "auto_promoted_pending_review"` (preferably also only while the memory is exposable); otherwise
   keep the b8 shape `{"status": "pending_owner_review"}`; add MCP regressions for the accepted
   (option off) and revoked re-proposal cases.

### Non-blocking

1. **N1 — Status and consent wording overstate the effect.** `aptuni memory review policy` prints
   "Agent proposals: saved automatically" (`src/aptuni/cli/memory_cli.py:179`) even when
   `auto_promotion_enabled` is off, in which case nothing is saved (probe). The consent text
   (`consent.detail.memory.propose`, en and zh-CN) says suggestions outside identity, relationships
   and behavior "are saved at once", omitting that automatic promotion must be on and that
   expose-disabled modules and the (configurable) sensitive set still ask. Suggest: print "saved
   automatically (automatic promotion is off, so they wait)" in that state and qualify the consent
   sentence.

2. **N2 — Existing grants change effect without re-consent.** The switch is global: every principal
   that already holds `memory.propose` (consented under b8's "they stay hidden until you accept them")
   starts writing exposable memories when the owner turns it on. This is the owner's documented
   decision, but the CLI could name the affected grants when the option is turned on. Relatedly,
   HANDOFF's next step "run `aptuni memory review policy --host-proposals on` for the owner" should
   be done only after an explicit in-chat yes, per the owner-confirmation rule.

3. **N3 — Over-fetch changes when the any-term fallback runs, and diversification can lift a
   fallback row above all-term matches.** `src/aptuni/retrieval/sqlite.py:183` runs the ADR-0004
   fallback only when all-term hits fill fewer than the search `limit`; Context now passes
   `min(101, max(limit+1, 3*limit))` (`src/aptuni/application/service.py:535`), so queries with
   between `limit+1` and `3*limit` all-term hits now also fetch fallback rows, and `diversify`
   (`:539`) places a distinct-concept fallback row before all-term repeats and before all-term rows
   of a crowded notebook (probe: an unrelated `tennis chains` note entered a top-2 that b8 filled
   with all-term matches). ADR-0004 says "all-terms hits always rank first"; the ADR-0005 amendment
   does not mention either effect, and this is the KI-018 noise class. Similarly, the 2026-09-25
   amendment's guarantee that a better-matching requested Evidence unit is not displaced by a weaker
   L3 match is now narrowed (an Evidence unit that is a repeat of its own Fact moves behind weaker
   distinct concepts). Nothing hidden is included and nothing is dropped, so this is a quality and
   documentation note: either diversify within the all-term tier first, or state both effects in
   the ADR-0005 amendment and add a partial-overlap Context case to KI-018's judgment set.

4. **N4 — The frozen evaluation does not cover Context ordering.** `tools/run_evals.py` searches the
   projection directly, so its unchanged 0.0 FPR says nothing about diversification; the ADR's
   numbers come from a private, pattern-judged experiment. Owner longitudinal trials taken through
   `_evaluation_context` before and after b9 are also not rank-comparable; worth one line in the
   evaluation report notes.

5. **N5 — `concept_key` edge cases.** Notion Evidence is keyed by page title, so distinct pages
   sharing a generic title ("Untitled", "Meeting notes") are treated as repeats and demoted;
   `_normalize` strips a trailing ASCII `.` but not `。`, so `学习Python。` and `学习Python` are
   distinct keys. Both only affect ordering. The per-notebook cap (`diversify.py:52`) applies to any
   statement that happens to contain `›`.

6. **N6 — Invariants do not bind a host promotion to an opt-in in force.** `_check_profile_promotion_event`
   accepts a `policy_auto` promote of a `host_proposal` candidate regardless of the recorded
   `ReviewPolicy`; the application gate is the only enforcement. Acceptable because the Vault is
   owner-controlled and b8 refuses any Vault containing a schema-2 policy, but worth noting if Vault
   compaction or policy-record purge is ever added.

### Verified (no finding)

- No MCP path can set the option: `set_review_policy` is called only from `cli/memory_cli.py`; MCP
  exposes no policy tool, and `actor="policy_auto"` events are written only by the core.
- Option off: `observe()` still never calls the evaluator for host input (structural gate at
  `memory_commands.py:183-185`); option on: ingest/expose denials, `auto_promotion_enabled`, the
  sensitive set and contradiction rules still apply, host filtering and idempotency run first.
- `_host_proposed` requires every support to be an Observation with `trust="host_proposal"` and an
  `mcp:` episode; a dangling link asks. Mixed CLI/host support cannot pass either rule.
- ADR-0020 holds on every Profile path: `evaluate_profile_memory` requires CLI `user_declared`
  support for both `pin` and `refresh_profile`; `derive_evidence_profile` reads Evidence only.
- Invariants accept the new events (`rationale_code="policy_host_proposal_allowed"` matches the
  pattern; exactly one root Memory per promoted candidate); reminders and `review pending` include
  host-saved memories; reject/revoke removes them from exposure.
- Schema 1 policies are byte-identical (model serializer drops the field); the validator ties
  `auto_promote_host_proposals` to schema 2 both ways; `set_review_policy` writes schema 1 again
  when the option is turned off; b8 fails closed with `SchemaVersionError`, and the CHANGELOG and ADR
  correctly say a downgrade needs a backup restore.
- Context: exposure is filtered in `_stable_search` and again via `records.exposable()` before
  `diversify`; `limit` is honoured by `[:limit]`; `limit` is bounded to 1..100 so the search limit
  is always `>= limit+1` and `<= 101` (the projection's bound); `more_results` keeps b8 semantics
  (more than `limit` permitted rows exist); the ordering is deterministic (stable over the
  `bm25, record_id` order); declared Facts (`subject="self"`) are keyed by statement, Evidence and
  Evidence-derived Facts by subject.

## Summary

Both changes are well scoped, schema-compatible and keep the Profile boundary intact, and the
diversification never includes hidden records. Two defects in the auto-save change need small fixes
before 0.2.0b9: the opt-in silently removes the per-principal cap on host writes (B1), and the MCP
tool misreports accepted or revoked re-proposals as freshly saved, changing the default-mode
response (B2). The notes are wording, documentation and retrieval-quality follow-ups.

**Verdict:** **BLOCK**

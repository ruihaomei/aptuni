# Milestone 2 Automatic Promotion and Retrospective Review Plan (TDD)

**Status:** Accepted (2026-09-22)
**Owner:** single owner. This touches the canonical record envelope and the revocation rule, both
shared architecture, so no parallel contract work while it is open.
**Contract:** ADR-0018.

## Objective

Make the core loop stop costing one confirmation per proposal: promote stable candidates
automatically, mark them as awaiting review, and let the owner review them retrospectively with
accept / edit / reject / pin / forget — while risky, conflicting and sensitive changes keep the
ADR-0013 confirmation.

## Why this is split

ADR-0018 §4 changes a rule that shipped code already depends on: today *any* `ReviewEvent`
targeting a memory id means "revoked". The Mem0 projection rebuild, the hybrid retrieval semantic
lane, Profile export and the privacy purge scope all encode that assumption. Introducing `accept`
and `pin` events before that rule is corrected would silently hide memories from four subsystems,
two of which shipped today. So the revocation rule is fixed and regressed **first**, on its own,
with no new event types in play.

### Slice A — Correct the revocation rule (no behaviour change)

Replace "any review event targeting a memory" with `decision in {"revoke", "reject"}` at every
consumer, and pin each consumer with a regression. Because no `accept`/`pin` event exists yet,
this slice is provably behaviour-preserving: the two rules agree on every event the product can
currently produce. That is exactly what makes it safe to land separately.

### Slice B — The promotion domain and the state machine

`ReviewEvent` schema v2 (`actor="policy_auto"`, `decision="pin"`), per-record-type version
resolution in `parse_record`, the `ReviewPolicy` canonical record, the eligibility evaluator, and
the derived `review_state`. No new CLI surface yet; the evaluator is exercised through the service.

### Slice C — The owner-facing loop

Automatic promotion wired into the `observe` commit path, `aptuni memory review
list|accept|edit|reject|pin`, the reminder in `status`/`doctor`, `aptuni review reminders|snooze`,
and the `review_state` marker in CLI, `--json` and the Context API.

### Slice D — MCP read surface

Pending set and reminder state over the existing bounded permissioned read path, plus the negative
proof that MCP cannot promote, accept, edit, reject or pin.

## Slice A failing-first cases

1. A memory with an `accept` event is still exposable, still in `memories()`, still projected by a
   Mem0 rebuild, still reachable through the hybrid semantic lane, still in Profile export, and
   still inside a privacy purge scope that names it.
2. A memory with a `revoke` event is excluded from all six, exactly as today.
3. A memory with a `reject` event is excluded from all six. (Today `reject` targets a candidate,
   never a memory; the rule must name it anyway so a future reject-on-memory is not a no-op.)
4. Candidate decisions are unaffected: `_decided()` over candidate ids keeps its current meaning
   for `accept` and `reject`, so a decided candidate is still not pending.
5. The Mem0 rebuild and the hybrid lane compute the same revoked set as the service does — pinned
   by a test that asserts the two derivations agree over a mixed ledger, so they cannot drift.

## Slice B failing-first cases

6. `parse_record` accepts `ReviewEvent` v1 and v2, rejects v3, and still rejects v2 for every other
   record type. The error stays `SchemaVersionError` with the migration message.
7. `actor="policy_auto"` and `decision="pin"` are rejected at v1 and accepted at v2.
8. Each eligibility rule, failed alone, produces its documented outcome: rule 2 leaves the
   candidate quarantined and silent; rules 3 and 4 route it to confirmation; rules 1 and 5 fail
   closed. All five passing promotes.
9. "Currently in force" for rule 3 excludes already-revoked memories and superseded facts, so a
   contradiction with a retracted claim does not block promotion.
10. `ReviewPolicy` defaults apply when no record exists, and an explicit record overrides them;
    an invalid policy fails closed rather than silently reverting to defaults.
11. `review_state` is derived correctly for: never-reviewed manual accept, auto-promoted pending,
    auto-promoted then accepted, auto-promoted then rejected, pinned, and revoked.

## Slice C failing-first cases

12. `observe` of a second supporting observation promotes the candidate in **one** commit that
    contains both the `Memory` and the `policy_auto` `promote` event, and the memory is exposable
    immediately.
13. A promotion that races a policy change is retried or fails closed, never exposing under a stale
    epoch.
14. `accept`, `reject` and `pin` are idempotent; `edit` supersedes with `change_kind="correction"`
    and preserves the original in history; `edit`/`reject` on a revoked memory fail closed.
15. Reminder arithmetic over a frozen clock: due at the threshold, due at the interval, not due
    after a snooze until `snooze_days` pass, and pinned memories never counted.
16. The `review_state` marker appears in `memory list`, `--json` and the Context API response.
17. A crash between the canonical commit and any derived-state write replays without promoting
    twice — promotion is idempotent on the candidate id.

## Slice D failing-first cases

18. MCP can read the pending set and the reminder state under an exact read scope, and cannot read
    either without it.
19. MCP has no tool that promotes, accepts, edits, rejects or pins, and the approve/commit service
    is not reachable from any MCP handler (ADR-0013 item 1 regression).

## Verification

```sh
.tools/bin/uv run --no-sync pytest tests/unit/domain tests/integration/test_memory_lifecycle.py \
  tests/integration/test_mem0_projection.py tests/integration/test_retrieval.py \
  tests/integration/test_export.py tests/integration/test_privacy_purge.py
.tools/bin/uv run --no-sync pytest
.tools/bin/uv run --no-sync ruff check . && .tools/bin/uv run --no-sync mypy src
python3.13 tools/check_relay.py
python3.13 tools/check_supply_chain.py notices && python3.13 tools/check_supply_chain.py secrets
```

Independent review is required: this changes the canonical envelope, a shared derivation rule, and
the acceptance path that ADR-0013 governs. Slices A and B are reviewed together with C; D may be
reviewed with C if it lands in the same checkpoint.

## Exit

Complete when an owner can let Aptuni learn without confirming each proposal, see exactly which
memories were promoted by policy and are awaiting review, act on them with accept/edit/reject/pin/
forget with full history preserved, be reminded gently rather than blocked, still be asked before
anything conflicting or sensitive is promoted, and when no shipped consumer of the old revocation
rule has silently changed behaviour.

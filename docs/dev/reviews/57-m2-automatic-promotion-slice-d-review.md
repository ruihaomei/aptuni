# Review 57 — M2 automatic-promotion Slice D

**Reviewer:** independent Codex subagent

## Scope and evidence

Reviewed only the uncommitted Slice D changes in `src/aptuni/adapters/manager.py`,
`src/aptuni/application/review_commands.py`, `src/aptuni/application/service.py`,
`src/aptuni/mcp/server.py`, `tests/integration/test_mcp.py`, and
`tests/integration/test_setup_apply.py`. Checked them against ADR-0005's bounded and
permission-mediated MCP read contract, ADR-0013 item 1, ADR-0018 §8, and cases 18–19 in the
accepted TDD plan.

Focused verification passed:

```text
.tools/bin/uv run --no-sync pytest tests/integration/test_mcp.py \
  tests/integration/test_setup_apply.py -q
61 passed

.tools/bin/uv run --no-sync ruff check tests/integration/test_mcp.py
All checks passed!

.tools/bin/uv run --no-sync mypy src
Success: no issues found in 74 source files
```

The new feed itself has the right shape. It authorizes the dedicated
`memory.review.read` scope through the common module/egress gate before reading; intersects pending
memories with both `RecordSet.exposable()` and the grant's modules; derives the reminder from that
filtered set, so hidden-module counts and due state do not leak; packs only the first `limit`
records through the existing byte-accounted budget; and rechecks the Vault sequence before returning.
The setup preview also discloses the newly granted scope. I found no production-path content leak or
direct mutation in the implementation as submitted.

## Initial blocking issue and remediation

### B1 — The executable regression does not prove the transitive boundary its name and ADR claim

`test_mcp_handlers_cannot_reach_owner_decision_or_commit_services`
(`tests/integration/test_mcp.py:56-74`) parses only `src/aptuni/mcp/server.py` and collects immediate
calls whose receiver is literally named `application`. It therefore proves that a handler invokes
one of four facade methods, but it does **not** inspect what the newly allowlisted
`memory_review_feed` (or either existing read facade) can reach. For example, adding
`self.observe(...)`, `self.review_memory(...)`, `self._commit(...)`, or a helper that calls any of
them inside `memory_review_feed` leaves the AST assertion green. The happy-path sequence comparison
at `tests/integration/test_mcp.py:147` would catch a write for that one fixture today, but not a
conditional promotion/commit reached only for another policy, module, queue size, or reminder
state.

That falls short of both the requested permanent regression and ADR-0013 item 1's stronger
"approve/commit service is reachable only from the CLI" contract. It also leaves the read-only MCP
annotation vulnerable to future internal drift without a failing gate.

**Required fix:** make the executable check cover the reachable facade implementation, not only the
adapter's first hop. A bounded solution is to inspect the AST/call graph of the three read entry
methods and every same-class helper they invoke, failing on promotion, owner-decision, confirmation,
and commit sinks. Alternatively, exercise every MCP read tool with those sinks monkeypatched to
raise and include fixtures that cover empty/non-empty queues and reminder branches; keep the direct
handler allowlist as the schema/surface guard. The forbidden sink set should include the complete
owner/consequential surface, not only the current nine names (for example privacy/restore/setup
confirmers as well as memory decisions). The regression must fail if
`memory_review_feed` begins calling `observe`, `promotion_records`, `_commit`, or an owner decision
service through a helper.

**Disposition: closed on re-review.** The direct handler allowlist remains, and the test now builds a
call graph from `identity_card`, `context`, and `memory_review_feed` across `AptuniService` and its
`ReviewCommands`, `MemoryCommands`, and `SourceCommands` mixins. It follows every same-service helper
reachable from those three read roots and rejects a concrete sink set containing `_commit`,
`promotion_records`, `observe`, the memory decision/confirmation methods, review-policy mutations,
source add/sync operations, module-policy changes, and privacy/restore confirmation or cancellation.
This means the previously demonstrated failure mode — adding a commit or owner decision inside an
allowlisted read facade or one of its service helpers while leaving the MCP adapter unchanged — now
fails the executable gate. Keeping the first-hop allowlist separately also prevents an MCP handler
from acquiring a new facade entry point without an explicit test change.

The test intentionally does not root `propose_from_host`: that MCP tool is a declared reversible
write which must commit a quarantined proposal, whereas ADR-0018 Slice D's claim is that the three
read surfaces cannot trigger promotion or owner/consequential mutation. Its host-origin structural
gate remains covered by the earlier automatic-promotion suite.

## Warnings and non-blocking suggestions

### W1 — Add a direct egress-denial case for the new scope

**Disposition: closed on re-review.** The focused Slice D test now invokes
`aptuni_get_memory_review` with the exact `memory.review.read` scope and permitted module but
`host_model_egress=False`, and requires `host_model_egress_denied`. Scope, module filtering, and
egress are therefore all pinned on the new surface itself.

### W2 — The final sequence check does not stabilize the disposable snooze marker

`memory_review_feed` stabilizes canonical records and policy with `vault_seq`, but
`_review_reminder_for` reads `state/review/reminder.json` outside that sequence. A concurrent
`snooze_review` or `clear_review_snooze` can therefore make one response carry a reminder state that
was already superseded even though the final Vault sequence still matches. This does not expose a
hidden module or corrupt canonical state, so it is not a release blocker. Either document reminder
snooze as best-effort disposable state in this MCP response, or add a marker generation/stat recheck
if the phrase "stable response" is intended to cover reminder cadence as well as the canonical
queue and policy.

## Overall judgment

The Slice D production implementation preserves scope, module, exposure, egress, budget, and
canonical snapshot boundaries. The remediated executable gate covers both the MCP adapter's direct
facade allowlist and transitive service/mixin reachability from every MCP read facade, closing B1.
The only remaining note is the already documented best-effort nature of the disposable snooze
marker under a concurrent marker-only change; it cannot expose hidden-module content or mutate
canonical state and does not block this slice.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

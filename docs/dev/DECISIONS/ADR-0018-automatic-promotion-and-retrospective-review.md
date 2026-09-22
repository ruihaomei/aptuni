# ADR-0018: Promote stable memories automatically and review them retrospectively

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** maintainer (made the product decision explicitly) · proposing agent · reviewing agent
- **PRD refs:** §16, §17, §21, §23
- **Supersedes in part:** ADR-0011's clause "In MVP only the ADR-0013 confirmation can accept it;
  later auto-promotion needs a new accepted ADR" — this is that ADR. Also supersedes ADR-0013
  item 2's implication that *every* candidate acceptance is an approval action. All other content
  of ADR-0011 and ADR-0013 stands, including the honest host trust boundary itself.
- **Needs maintainer confirmation:** no — the maintainer specified the policy directly.

## Context

The MVP deliberately required an explicit terminal confirmation before any CandidateMemory became
a Memory. That was the right default while the lifecycle was unproven, and ADR-0011 said so at the
time, but it makes the product's core loop cost the user one confirmation per proposal. In daily
use that is the difference between a context layer that grows and one that stalls in a queue.

The maintainer's decision: stable candidates may be promoted automatically when the evidence and
risk policy allows; promoted facts become active immediately; they are marked as awaiting review;
the user reviews them *retrospectively* rather than blocking on them; genuinely risky changes still
require immediate confirmation; and the user is reminded gently rather than nagged.

## Decision drivers

- The core loop must not require a confirmation per proposal.
- A wrong auto-promotion must be cheap to discover and cheap to undo, never silent.
- Risky, conflicting and sensitive changes keep the ADR-0013 confirmation.
- Provenance and history are preserved through every path; nothing is overwritten.
- No canonical duplication of state that can be derived from the append-only ledger.

## Decision

### 1. Promotion is a policy decision recorded in the ledger

A candidate that satisfies **every** eligibility rule below is promoted without confirmation. The
promotion appends a `ReviewEvent` with `decision="promote"` and `actor="policy_auto"`, and creates
the `Memory` in the same commit. The Memory is **active and exposable immediately**.

`actor="policy_auto"` is a new value and is deliberately distinct from `user_cli`. ADR-0011's rule
that "no source/model content can act as the reviewer" is unchanged: the promoter is the core's own
policy evaluated over canonical records, never a source, a model, or a host.

### 2. Eligibility (all must hold)

1. The candidate's module has `ingest_enabled`.
2. **Stability.** The candidate is supported by at least two distinct Observations, or by one
   Observation whose trust is `user_declared` and whose origin is `cli`.
3. **No contradiction.** The candidate does not `contradict` any Memory or Fact that is currently
   in force.
4. **Not sensitive.** The candidate's module is not in the configured sensitive set
   (default: `identity`, `relationships`, `behavior`).
5. **No exposure widening.** Promotion does not expose anything the module's current
   `expose_enabled` does not already allow.

Failing rule 2 leaves the candidate quarantined and pending more evidence; nothing is asked of the
user. Failing rule 3 or 4 routes the candidate to the **existing ADR-0013 confirmation path** — the
user is asked, exactly as today. Failing rule 1 or 5 fails closed.

### 2b. Which id each event targets

`ReviewEvent.target_id` already means different things for different decisions, and this ADR keeps
that split explicit rather than inventing a second link field:

- `accept`, `reject` and `promote` **on a candidate** target the **candidate id**. They are the
  decision that turns a proposal into a Memory, or refuses it. `exposable()` already admits a
  Memory only when its `candidate_id` carries an `accept`; it must now also admit `promote`.
- `accept`, `reject`, `revoke` and `pin` **on an existing Memory** target the **memory id**. They
  are decisions about a record that already exists.

The derived review state therefore joins the two: a Memory is *auto-promoted pending review* when
its `candidate_id` carries a `policy_auto` `promote` event and its own id carries no user
`accept`, `reject` or `revoke`.

### 3. `auto_promoted_pending_review` is derived, not stored

A Memory is *auto-promoted pending review* when its ledger has a `policy_auto` `promote` event and
no later user decision targeting it. This follows ADR-0011's "reverse links are derived" rule and
means no Memory record has to change shape. The marker is surfaced explicitly wherever the user or
an agent sees a memory: `aptuni memory list`, `--json` output, the Context API response and the MCP
memory tools all carry a `review_state` field.

### 4. Revocation is no longer "any review event"

Today `_decided()` treats **any** `ReviewEvent` whose `target_id` is a memory id as a revocation,
because the only events that could target a memory were revocations. This ADR adds `accept` and
`pin` events that target memory ids, so that rule becomes wrong.

**Normative:** a Memory is revoked when a `ReviewEvent` targeting it has
`decision in {"revoke", "reject"}`. Every consumer of the old rule must move to it. The known
consumers are the Mem0 projection rebuild, the hybrid retrieval semantic lane (ADR-0004's
2026-09-22 amendment), Profile export and the privacy purge scope. Each needs a regression proving
that an `accept` or `pin` event does not hide a memory.

### 5. Retrospective review operations

Over a Memory, from the CLI and (read plus propose only) from MCP:

| Operation | Effect |
|---|---|
| `accept` | `ReviewEvent(accept, user_cli)`. The memory leaves the pending set; content unchanged. |
| `edit` | Appends a corrected Memory with `change_kind="correction"` superseding the original, plus an `accept` event. The original stays in history. |
| `reject` | `ReviewEvent(reject, user_cli)`. No longer exposable; history preserved. |
| `pin` | `ReviewEvent(pin, user_cli)`. The memory is exempt from future automatic supersession and is never counted toward a review reminder. |
| `forget` | The existing ADR-0011 revocation path, unchanged. |

`accept`, `reject` and `pin` are idempotent: a repeat is a no-op, not a second event. `edit` and
`reject` on an already-revoked memory fail closed.

### 6. Reminder policy, not notification

A new canonical `ReviewPolicy` record holds `auto_promotion_enabled` (default true),
`sensitive_modules`, `pending_threshold` (default 10), `interval_days` (default 15) and
`snooze_days` (default 15). A reminder is *due* when the pending count reaches the threshold, or
when `interval_days` have passed since the last reminder was shown or snoozed — whichever comes
first. Pinned memories never count. A reminder is a line in `aptuni status` and `aptuni doctor` and
a dedicated `aptuni review reminders`; it is never a blocking prompt, and `aptuni review snooze`
defers it by `snooze_days`.

### 7. Schema versioning: per-record-type, no data migration

`ReviewEvent` gains `schema_version: Literal[1, 2]`; `actor="policy_auto"` and `decision="pin"` are
valid only at version 2. Every other record type stays at version 1 and no existing record is
rewritten. `parse_record` resolves the allowed versions per `record_type` instead of comparing one
global constant.

An Aptuni 0.1.0 install reading a Vault that contains a v2 `ReviewEvent` therefore raises the
existing `SchemaVersionError`, whose message already says to run the documented migration. That is
a clean fail-closed signal rather than a pydantic validation crash, and it is why this is preferred
over widening the v1 literal in place. A global `SCHEMA_VERSION` bump was rejected: it would rewrite
the version of every record type for a change that affects one.

### 8. MCP behaviour

MCP gains read access to the pending set and the reminder state through the existing bounded,
permissioned read path, and it may *propose* a candidate exactly as today. MCP never accepts,
edits, rejects, pins or promotes, and it never triggers a promotion evaluation. ADR-0013 item 1's
rule that the approve/commit service is reachable only from the CLI is unchanged; automatic
promotion runs inside the `observe`/`sync` commit path, not through an approval service.

## Consequences

- **Positive:** the core loop stops costing a confirmation per proposal; a wrong promotion is
  visible, attributable to `policy_auto`, and reversible with full history; risky changes keep the
  old guarantee.
- **Negative / risks:** a wrong auto-promotion is *exposable before the user sees it*. That is the
  accepted trade, bounded by the eligibility rules, the sensitive-module set, the visible marker and
  the reminder. The revocation-rule change in §4 touches shipped code paths, including ones added
  the same day, so it is the highest-risk part of this ADR and needs explicit regressions. A Vault
  written after this change cannot be read by 0.1.0.
- **Follow-ups:** the Obsidian review interface consumes this state machine and is deliberately
  *not* designed here. Per-module promotion thresholds, and promotion of Memory into Fact (this ADR
  covers Candidate into Memory), are separate decisions.

## Verification

A promotion matrix over the five eligibility rules; idempotence of every operation; a regression per
known consumer of the old revocation rule proving `accept`/`pin` does not hide a memory; reminder
due/snooze/threshold arithmetic over a frozen clock; the derived marker appearing in CLI, JSON,
Context API and MCP; MCP proven unable to promote, accept, edit, reject or pin; `parse_record`
accepting v1 and v2 `ReviewEvent`s and rejecting v3; and a 0.1.0-compatibility test asserting the
clean `SchemaVersionError`.

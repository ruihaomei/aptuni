# Review 26 — M1 interaction-memory lifecycle and MCP proposal path

- **Date:** 2026-09-20
- **Reviewer:** independent Codex subagent (did not write the change)
- **Scope (uncommitted):** `src/aptuni/application/memory_commands.py`, service mixin wiring,
  `src/aptuni/cli/memory_cli.py` and CLI dispatch, adapter `memory.propose` scope changes,
  `aptuni_propose_memory`, `tests/integration/test_memory_lifecycle.py`, the related MCP/export tests,
  and the ADR-0005 amendment.
- **Risk class:** high (canonical memory, authorization, MCP write path, privacy, revocation).

## Checks run

| Check | Result |
|---|---|
| `pytest -q tests/integration/test_memory_lifecycle.py tests/integration/test_mcp.py tests/integration/test_export.py` | 15 passed |
| Focused idempotency collision reproduction | reproduced: two different statements/modules with `same-key` returned the same candidate ID |
| Focused credential persistence reproduction | reproduced: an AWS-key-shaped statement was stored as a canonical pending Observation/CandidateMemory |
| Focused confirmation reproduction | reproduced: `decide_memory` accepted a digest computed from public preview fields without any pre-issued/consumed nonce |
| `git diff --check` | clean |

The positive properties are substantial: scope and exact-module checks precede the MCP write; proposals
remain quarantined; accepted memories respect current ingest/expose policy; stale policy epochs and wrong
digests deny; accept/reject are single-decision under the Vault sequence check; revocation removes a Memory
from `RecordSet.exposable()` while retaining history; and the MCP schema exposes no approval field.

## Blocking findings

### B1 — The claimed single-use confirmation nonce does not exist as an authorization control

`memory_commands.py:55-57,140-164,213-218`; `memory_cli.py:73-85`; ADR-0005 amendment lines 114-117.

`MemoryPreview.digest()` is a deterministic hash of fields already known to the proposer (decision,
candidate ID, module, policy epoch and statement). `decide_memory()` accepts that hash directly. The
`nonce_id` is generated only **after** authorization has succeeded, while constructing the audit event;
it is never issued with a preview, presented for confirmation, validated, expired, or consumed. Thus it
cannot prevent replay or authorize anything. Candidate state happens to make a second decision fail, but
that is not the ADR-0005/0013 confirmation contract and does not make the stored nonce meaningful.

This is a contract and audit-integrity blocker, not a claim that core can prove human presence (ADR-0013
correctly says it cannot). The supported CLI/service path still promises a digest-bound, single-use nonce
and currently implements only the digest. Implement a pending confirmation carrying a random nonce and
expiry, bind the nonce plus principal/action/scope/policy epoch into the digest, and consume it atomically
with the ReviewEvent/Memory commit. Alternatively amend the accepted confirmation ADR before shipping,
remove the false nonce claim/field, and document why candidate single-decision is the chosen replay guard.
Add tests for replay, expiry, stale epoch, changed payload, and concurrent consumption.

### B2 — `memory forget` permanently revokes immediately, without the review/confirmation contract

`memory_cli.py:69-72`; `memory_commands.py:167-176`.

Accept and reject render a preview and require a typed confirmation, but `aptuni memory forget <id>` calls
the revocation service immediately. Revocation is append-only and there is no unforget operation, so a
mistyped or agent-invoked command permanently changes agent-visible context. Its locally computed digest
and post-hoc random `nonce_id` provide no user confirmation. This conflicts with ADR-0005's rule that
consequential mutations use an exact preview and single-use confirmation, and leaves the most
privacy-sensitive lifecycle action with less accidental-action protection than rejection.

Render the memory, module, provenance and effect; require an exact terminal confirmation; and pass the
revocation through the same fixed confirmation mechanism as B1. Test cancellation, stale policy/digest,
replay/idempotent retry, and that a cancelled forget leaves both owner and agent views unchanged.

### B3 — Caller idempotency keys are global aliases, not bound to principal, module, or payload

`memory_commands.py:88-96,119-127,199-206`; `mcp/server.py:106-119`.

The MCP caller controls `idempotency_key`, but lookup searches every Observation by that raw key and
returns its candidate without checking provenance episode, module, normalized statement, or `about`.
Reproduction: propose `"First statement"` in `preferences` with `same-key`, then propose
`"Completely different statement"` in `goals` with `same-key`; the second call returns the first
candidate ID with `created=False`, and no goals candidate exists. Across principals or a later narrowed
grant this also returns an ID belonging to another episode/module, contradicting the method's
"releases no personal data" claim and exact-module authorization model.

Namespace the stored key by principal/episode and bind it to a canonical payload hash. On reuse, return
the existing candidate only when principal, module, statement and other semantic fields match; otherwise
return a fixed `idempotency_conflict` error without an existing candidate ID. Add same-key/different-
payload, cross-principal, cross-module and concurrent-retry tests. The current test covers only the
default content-derived key.

### B4 — The untrusted MCP write path persists obvious credentials/raw text despite claiming not to

`mcp/server.py:106-119`; `memory_commands.py:81-117`; PRD §14.

The only content validation is normalized length (1-280). The tool docstring tells the model never to
submit secrets, credentials or raw conversation text, but model text is untrusted under ADR-0005/0013
and cannot enforce policy. A focused call with `AWS secret: AKIAIOSFODNN7EXAMPLE` produced durable
canonical Observation and CandidateMemory records. Rejection does not delete them. A granted host can
therefore persist up to 200 credential/raw-text payloads per principal even though raw conversation
retention is off by default and the tool advertises the opposite behavior.

Apply a fail-closed host-proposal content policy before commit: at minimum reject credential/private-key
patterns and control/instruction-shaped or non-structured payloads using a fixed, content-free error;
keep owner-authored CLI observations a distinct trust path. Make the exact enforceable guarantee in the
tool description and ADR (do not promise detection that cannot be implemented), and add tests proving
rejected payload bytes never enter any canonical record, error, or log. If arbitrary free-text host
proposals are intentionally accepted, that privacy decision needs an explicit ADR/PRD change rather than
a docstring instruction.

## Non-blocking warnings and test gaps

- **N1 — Permanent content deduplication is broader than retry idempotency.** The default key is a hash
  of constant episode + module + statement. After rejection or revocation, an identical observation can
  never become a new candidate unless a caller invents a new key; the CLI has no such option. Define an
  episode/request boundary or explicitly document permanent deduplication, then test the rejected and
  revoked re-observation cases.
- **N2 — Adapter opt-in lacks focused coverage.** Add tests that the default plan/grant omits
  `memory.propose`, `--allow-memory-proposals` adds it to the digest-bound plan and persisted grant, a
  tampered pending plan fails validation, and the preview discloses the write capability.
- **N3 — Concurrency is not tested.** Two simultaneous identical proposals can race: one succeeds and
  the other receives `concurrent_write`, despite the tool's `idempotentHint=True`. Either retry the
  snapshot once and return the winner when the bound payload matches, or weaken the annotation/contract.
- **N4 — CLI behavior is unit-invoked only through service helpers.** Add end-to-end CLI tests for
  rendering untrusted statement text safely, cancellation, wrong digest, stale epoch, accept/reject,
  broken input/EOF, and the fixed forget flow.
- **N5 — Actor provenance is asserted, not derived.** Every event hard-codes `actor="user_cli"`, even
  though `decide_memory()` and `forget_memory()` are public application methods callable in process.
  Restrict these methods behind a CLI-only confirmation capability or rename the actor to an accurately
  verified application principal.

**Verdict:** **BLOCK**

# M2 Automatic Profile Promotion — bounded TDD plan

## Outcome

Close the canonical `Memory → stable Profile Fact` lifecycle without semantic inference. A current
Memory becomes eligible only after the owner pins it and its complete support remains owner-declared
CLI material. Aptuni copies the statement into a lineage-linked Fact in the same commit as the pin,
marks the resulting Fact as retrospectively reviewable through ledger-derived state, and exposes
small CLI review commands. A refresh command handles pinned Memories created before this slice.

## Contract boundary

- Keep the canonical `Fact`, `Memory`, and `ReviewEvent` schemas; clarify the already-versioned
  `promote` event so a policy promotion targeting a Memory admits one linked Fact.
- Require every gate: current/non-revoked/non-superseded Memory, owner `pin`, owner-declared CLI
  support, current module ingest and expose permission, no unresolved candidate contradicting the
  Memory, automatic promotion enabled, and no historical Fact already linked to that Memory.
- Copy only the bounded Memory statement. Set `memory_ids` to the exact source Memory and preserve
  candidate provenance, module, policy epoch, and temporal fields. Do not infer a richer predicate,
  proficiency, identity, or time range.
- Append the policy `promote` event and Fact atomically. Derive Profile review state from the ledger;
  never duplicate it on the Fact.
- Owner `accept` settles the Fact; owner `reject` withdraws only the Fact and keeps Memory/history.
- Keep MCP read/write surfaces unchanged in this slice.

## Red → green sequence

1. Unit matrix for every eligibility gate, idempotence, existing pinned-memory refresh, derived
   Profile review states, and unresolved contradiction handling.
2. Canonical invariant tests for valid Memory→Fact lineage and invalid/missing/multi-source policy
   promotion records.
3. Integration tests proving pin+promotion atomicity, permissions, supersession/history, accept and
   reject behavior, export/context visibility, and refresh idempotence.
4. CLI tests for `profile refresh` and `profile review list|accept|reject`, including JSON output.
5. Implement the smallest policy/service/CLI surface needed to pass those tests.

## Gates and checkpoint

Run focused unit/integration tests during iteration; then pytest, Ruff, strict mypy, relay,
supply-chain/developer checks, and the frozen evaluation gate. Because this changes a canonical
lifecycle contract, obtain independent review, remediate only blocking findings, update durable
state/research notes, and create a local checkpoint without pushing.

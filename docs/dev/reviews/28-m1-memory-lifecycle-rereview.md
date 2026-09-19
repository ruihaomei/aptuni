# Review 28 — M1 interaction-memory lifecycle remediation re-review

- **Date:** 2026-09-20
- **Reviewer:** independent Codex subagent (did not write the implementation or remediation)
- **Scope:** Review 26 B1-B4 remediation in `application/memory_commands.py`, `cli/memory_cli.py`,
  MCP and adapter wiring, focused tests, ADR-0005 amendment, and
  `26-m1-memory-lifecycle-remediation.md`.
- **Risk class:** high (canonical memory, MCP write authorization, confirmation and privacy).

## Validation

| Check | Result |
|---|---|
| `pytest -q tests/integration/test_memory_lifecycle.py tests/integration/test_mcp.py tests/integration/test_adapters.py tests/integration/test_export.py` | 28 passed |
| Focused Ruff check | passed |
| `.tools/bin/uv run mypy src` | passed (56 source files) |
| Forced concurrent identical proposal (two threads held at commit) | one create + one retry result, same candidate ID, one pending candidate |
| Cross-payload/principal/module idempotency adversarial checks | conflicts are content-free; no foreign candidate ID returned |
| Expiry, stale epoch, wrong digest, replay and canonical nonce inspection | fail closed; committed ReviewEvent carries the issued nonce |
| Protected-content pre-commit check | representative access key, credential assignment, transcript prefix and control instruction rejected before a Vault segment contains the bytes |

## Review 26 blocking findings

### B1 — Nonce issuance, expiry and consumption: PASS

`memory_commands.py:193-227,320-370` now creates a random 128-bit nonce in a mode-0600 file under a
mode-0700 directory, with a ten-minute expiry and current policy epoch. Decision digests bind action,
target, module, statement, epoch, nonce and expiry. A missing, malformed, expired or wrong-epoch
confirmation fails before commit. The ReviewEvent and accepted Memory share the one canonical commit;
the ReviewEvent stores the exact nonce, and target lifecycle state prevents a leftover file after a
crash from authorizing another decision. A successful commit removes the preview file best-effort.

The focused test mutates expiry, advances policy, tries a wrong digest, verifies the stored nonce and
replays the decision. The implementation correctly treats the canonical event/decision as authoritative
when file unlink is interrupted.

### B2 — Confirmed forget: PASS (notes N1-N2)

`memory_cli.py:51-70` renders the full memory, provenance, effect, epoch, nonce, expiry and digest, then
requires `FORGET` or an exact digest. `forget_memory_confirmed()` validates the current policy-bound
confirmation before appending a revocation. Wrong confirmation and cancellation leave the memory
exposable; exact service-level retry is idempotent; canonical history remains intact. The CLI integration
test covers cancellation and successful confirmed revocation.

### B3 — Idempotency binding and concurrent retry: PASS

`memory_commands.py:131-174,279-288` namespaces caller keys by episode/principal and validates module,
normalized `about` and normalized statement before returning an existing candidate. A changed payload
raises fixed `idempotency_conflict` without exposing the existing ID. Different principals produce
different keys. On `concurrent_write`, the loser re-reads and returns the winner only if the complete
bound payload matches.

The committed tests cover same-key retry, changed statement, changed module and changed principal. I
also forced two threads to take the same pre-commit snapshot; results were `created=True` and
`created=False` with the same ID and exactly one candidate.

### B4 — Protected-content rejection: PASS (note N3)

`memory_commands.py:40-49,128-138` normalizes text and runs the host-only filter before opening the
Vault snapshot or constructing records. It rejects fixed high-confidence credential/access-token,
private-key, credential-assignment, transcript-role and instruction-control patterns with one fixed
error. MCP returns only the error code. Owner-authored CLI observations remain a separate intentional
path. The ADR and tool description now accurately call this a narrow recognizable-pattern screen, not
complete secret detection.

The parameterized test verifies that each rejected input's exact bytes are absent from all Vault
segments. This satisfies the scoped remediation without pretending arbitrary secret/raw-text detection
is possible.

## Non-blocking notes

- **N1 — Exact forget retry is not reachable through the CLI.** The service returns success when the
  same revocation digest is retried, but `_cmd_forget()` always calls `memory_forget_preview()` first.
  Once revoked, that call raises `memory_not_current`, so
  `aptuni memory forget ID --confirm-digest SAME_DIGEST` reports failure after an uncertain successful
  first run. I reproduced this. Move the exact confirmed-retry check ahead of fresh-preview creation, or
  add a CLI/service operation that returns the existing matching receipt. This is reliability/UX rather
  than a safety failure: the desired revocation is already canonical and no second mutation occurs.
- **N2 — Cancellation leaves the issued confirmation valid until expiry.** Both accept/reject and forget
  return after printing `Cancelled` without clearing their nonce file. The token remains usable for up
  to ten minutes through the supported digest path. Clearing the confirmation on explicit cancellation
  would better match user intent and reduce accidental reuse; add a regression test. Host confinement
  remains the boundary against agent-shell use, as ADR-0013 states.
- **N3 — Keep the protected-pattern corpus current.** The intentionally narrow filter does not catch
  every recognizable credential family (for example Google API keys, JWTs or webhook URLs). Add
  high-confidence formats as evidence appears, without changing the ADR into an impossible universal
  detection claim. Also test that errors and logs contain neither submitted text nor matched fragments.
- **N4 — Preserve a deterministic concurrency regression.** The retry branch passed my forced-barrier
  reproduction, but the committed suite does not itself force the two writers past the same snapshot.
  Add that test so future refactors cannot silently turn the MCP tool's `idempotentHint=True` into an
  occasional `concurrent_write` response.
- **N5 — Module-level wording remains stronger than enforcement.** The file docstring says raw
  conversations are “never stored”; the implementation can only reject recognizable transcript/control
  shapes. Use the ADR's precise wording: Aptuni accepts a bounded structured statement and does not
  intentionally retain the surrounding conversation.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

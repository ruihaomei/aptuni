# Milestone 2 Mem0 production projection adapter review

**Reviewer:** independent Codex review of the uncommitted production adapter slice

## Scope

Reviewed the projection contract and local Mem0 factory, service and CLI integration, privacy
inventory/purge behavior, Advisor preview catalog, public English/Chinese documentation, ADR-0003
amendment, optional dependency metadata and lock, and focused unit/integration coverage. The review
also exercised the hash-locked isolated Mem0 2.0.20 / Ollama 0.6.2 runtime.

## Blocking findings

None in the final reviewed tree.

## Correctness and failure cleanup

- Rebuild accepts only current non-revoked canonical `Memory` records, sorts them deterministically,
  sends exact bounded metadata, forces `infer=False`, and rejects duplicate, missing, changed,
  malformed, or extra enumeration rows before publication.
- A generation becomes active only after exact validation, provider close, bounded manifest write,
  and atomic `CURRENT` replacement. Pre-publication add, enumeration, close, manifest, and selector
  failures remove the failed generation while leaving the prior selector unchanged and expose only
  a bounded Aptuni error.
- The publication commit point is now handled correctly. Old-generation cleanup cannot re-enter the
  generic failure path and delete the selected generation. Both injected `rmtree` failure and
  generation-enumeration failure retain a valid new generation and surface
  `cleanup_pending=true` / `state=cleanup_required` for honest follow-up.
- Provider enumeration no longer silently discards malformed non-dictionary rows; the regression
  verifies that such an extra row fails the exact projection check.

## Privacy, deletion, and concurrency

- Capabilities truthfully deny inference, incremental deletion, and portable export while exposing
  whole-store deletion and rebuild. The adapter has no record-level mutation or inference entry
  point.
- Both explicit provider deletion and privacy purge remove the whole Aptuni-managed Mem0 root.
  Privacy previews always include the projection token, so a projection created after preview is
  still in confirmed cleanup scope.
- Rebuild/delete and confirmed privacy purge share `source_operations_lock`. The concurrency
  regression demonstrates that a purge waiting on an in-flight rebuild removes the finished
  projection, preventing old canonical content from being published after a confirmed purge.
- The projection remains outside the Vault, is excluded from backup semantics, and canonical
  records are unchanged by rebuild/delete operations. Revocations are excluded on the next fresh
  whole-store rebuild rather than delegated to Mem0 deletion.

## Optional dependency, import, and network boundary

- Mem0 and Ollama remain optional extras; default-runtime tests skip the real provider paths, and
  missing dependencies clean the attempted generation without selecting it. Runtime activation
  requires exactly `mem0ai==2.0.20` and `ollama==0.6.2`, matching `pyproject.toml`, `uv.lock`, and
  ADR-0003.
- Telemetry is disabled before the first Mem0 import. Configuration permits only plain HTTP
  loopback Ollama endpoints, bounds model names/dimensions, embeds through local Ollama, uses
  embedded Qdrant below the generation root, and refuses automatic model pulls.
- The production Ollama client now disables redirects and environment-derived proxies. Unit and
  isolated-runtime regressions verify `follow_redirects=False`, `trust_env=False`, real model-list
  object handling, and refusal to follow a loopback server's remote redirect. This closes the path
  by which canonical memory bodies could otherwise leave the local endpoint despite URL
  validation.

## Public contract and roadmap consistency

The implementation matches the narrow ADR-0003 amendment and S10 admission: this is an explicit
preview-only, rebuild-only derived projection, not a canonical store, backup, inference service, or
Advisor-selected default. The catalog advertises no external egress/API key, disables automatic
extraction, and keeps the preview behind the existing evidence gate. CLI status/rebuild/delete
outputs are content-free and expose generation cleanup and capability limitations.

## Non-blocking notes

- `Mem0Projection.status()` validates the selector and manifest in a bounded `try`, but its final
  `generations.iterdir()` cleanup scan is outside that boundary. A permission/I/O failure there is
  still caught content-free by the CLI's global unsafe-state boundary, but the service call raises
  instead of returning `invalid` or `cleanup_required`. Fold that scan into the status boundary in
  a later hardening pass.
- README wording says Aptuni removes and rebuilds the projection when a canonical memory is
  forgotten. The implemented behavior marks the existing generation stale and excludes the revoked
  record on the next explicit `memory provider rebuild`; it does not automatically rebuild during
  `memory forget`. Clarifying “on the next explicit rebuild” would make the user-facing lifecycle
  exact. This is not a privacy-deletion defect because `forget` explicitly retains canonical
  history, while confirmed `privacy purge` removes the projection immediately.
- `dependency_available` reports module presence, while exact version compatibility is enforced at
  rebuild time. A future richer health status could distinguish “installed but unsupported” without
  importing the optional provider.

## Verification

- Focused default-runtime Mem0, privacy purge/inventory, and Advisor catalog tests passed; the real
  optional-runtime cases skipped as designed.
- In `/tmp/aptuni-s10-runtime.gmDDO3`, all 22 Mem0 unit/integration tests passed against the pinned
  real optional dependency runtime.
- Focused Ruff passed, strict mypy passed across 68 source files, `uv lock --check` resolved the
  92-package lock successfully, and `git diff --check` reported no whitespace errors.

## Overall judgment

The slice preserves the Vault as the sole source of truth and implements the conditional S10
admission without widening it. Failure publication, purge concurrency, malformed enumeration, and
loopback egress risks found during review are covered by explicit remediations and regressions. The
remaining notes are bounded maintainability/documentation improvements and do not prevent the M2
preview adapter from landing.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

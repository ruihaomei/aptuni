# Milestone 2 Mem0 Projection Adapter Plan (TDD)

**Status:** Accepted (2026-09-22)

## Objective

Ship a user-visible, local-only Mem0 projection manager that materializes current accepted canonical
memories without giving Mem0 inference, history, deletion, or export authority.

## Vertical slice

- Define the narrow internal memory-projection contract and content-free capability/health report.
- Add `aptuni memory provider status|rebuild|delete` for the Mem0 projection.
- Rebuild into a fresh generation with `infer=False`, exact canonical ID/module/schema metadata, and
  exact post-write validation before an atomic generation switch.
- Configure only loopback Ollama plus embedded Qdrant below one Aptuni-managed state root. Mem0 and
  Ollama remain optional dependencies and missing prerequisites fail with stable bounded errors.
- Add the projection to privacy inventory and always invalidate its whole root for any canonical
  privacy purge.

## Failing-first cases

1. Missing optional dependencies and invalid/non-loopback configuration never import or partially
   create a live generation.
2. Every add call uses `infer=False`; raw messages and arbitrary provider metadata are impossible
   through the adapter contract.
3. Duplicate, missing, changed, or extra provider rows fail exact validation and keep the prior
   generation selected.
4. Failed add, validation, close, or publication leaves the prior generation usable and cleans the
   failed generation.
5. Rebuild includes only current accepted canonical memories; revocations disappear because every
   operation is a whole-store rebuild.
6. Status and errors remain content-free. A corrupt selector, symlink, unsafe path, or unknown
   manifest fails closed.
7. `delete` closes no live in-process client, removes the entire managed root, and is idempotent.
8. Privacy inventory names the derived projection and confirmed canonical purge invalidates it even
   when it appeared after the preview.

## Verification

Run focused provider and CLI/privacy regressions, the isolated Mem0 runtime smoke, full pytest,
Ruff, strict mypy, relay, and an independent privacy/public-contract review before checkpointing.

## Exit

The slice is complete only when the CLI can truthfully report, rebuild, and delete the projection;
failure injection proves old-generation preservation; privacy purge cannot leave the projection;
and the Vault bytes and Context API schema remain unchanged.

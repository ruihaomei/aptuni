# Milestone 1.1 Execution Plan — Foundation (TDD)

**Status:** Draft; do not execute until Gate 0 passes.

Development distribution is `personal-context-core`, import namespace `personal_context_core`, and
temporary CLI name `personal-context`. A public rename requires a migration plan before stable API.

## Objective

Create the smallest production foundation that safely owns canonical records, policy, provider
contracts, and projections. No real source adapters, MCP server, optional memory backend, or UI is
implemented in this package.

## Proposed file ownership

```text
pyproject.toml
src/personal_context_core/
  domain/          # pure versioned records and invariants
  vault/           # ports + filesystem implementation + migrations
  policy/          # fail-closed ingest/expose/retention decisions
  plugins/         # protocols, manifests, discovery and activation
  application/     # command/query services, SDK envelopes, errors, confirmations
  inference/       # proposal-only InferenceProvider port
  projections/     # generic projection lifecycle only
tests/
  unit/
  contract/
  integration/
  fixtures/
schemas/
```

Dependency direction is `domain ← vault/policy/plugin contracts ← application services`. Domain
must not import SQLite, MCP, host SDKs, or concrete providers.

## Slice 1 — Toolchain and package skeleton

1. Write a smoke test that imports the confirmed namespace and reports package version.
2. Add the minimal `pyproject.toml`, `src/` package, test runner, formatter/linter, and type checker.
3. Lock and review dependencies; add isolated build, SBOM/license/vulnerability/secret checks and a
   process-level network canary. Reject unexpected install-time code where tooling permits.
4. Build sdist and wheel; install each non-editably into clean environments and smoke-test import,
   CLI, bundled schemas/translations, and fixture entry point on the supported Python/OS matrix in
   `COMPATIBILITY.md`. CI runs exactly the same commands.
5. Define offline install as installation from an explicit local wheelhouse with sockets denied;
   test no-key/offline runtime separately.
6. Add verified local/CI commands to `AGENTS.md`.
7. Assert security test doubles (fake proven-local host, confinement probes) are excluded from the
   sdist and absent from the wheel and any installed import path (ADR-0013 item 7).

**Done:** sdist/wheel contents match, clean non-editable installs pass in CI, wheelhouse install works
with sockets denied, runtime smoke tests use no optional service or key, and no test double ships.

## Slice 2 — Domain records and invariants

1. Convert S01 golden fixtures into failing unit/schema tests.
2. Implement versioned Fact, Observation, CandidateMemory, Memory, ReviewEvent, Evidence,
   SourceLocator, SourceConfig/AuthorityPolicy, Snapshot, CandidateDelta, ModulePolicy,
   PluginManifest, trust/taint, policy epoch, pending action/confirmation, retention label, deletion
   receipt, and minimal restore tombstone types.
3. Add invariant tests: timezone-aware timestamps; valid intervals; supersession consistency;
   valid/system-time queries; interaction-memory transitions; source-authority conflicts; evidence
   cannot imply mastery; unknown schema versions fail with migration guidance.
4. Export machine-readable schemas and snapshot them.

**Done:** exact semantic round trip and stable schema snapshots.

## Slice 3 — Vault port and filesystem repository

1. Specify behavior tests for create/read/list/append/supersede, idempotency, optimistic conflict,
   atomic batch, backup, and migration.
2. Implement the port against a temporary filesystem using S01's accepted write protocol.
3. Add crash/fault injection, path traversal, symlink, restrictive permission/ownership,
   malformed-record, and concurrent-writer tests. Document that open-format data is plaintext unless
   the user's disk/backup layer encrypts it.
4. Add coordinated purge journal/receipt tests, partial-failure retries, backup rotation, and restore
   from a generation predating purge without resurrection.
5. Test opted-in raw buffers through crash/restart/expiry using OS-backed encryption or encrypted-disk
   placement; unavailable encryption requires an explicit high-friction plaintext warning and never
   enables silently. Assert markers never reach generic temp paths or logs.
6. Define version markers and migration transaction boundaries; fault every step, retry idempotently,
   refuse unknown newer versions, restore last-known-good on failure, fall back from a corrupted newest
   generation, and verify a backup before rotating its predecessor.
7. Verify a failed write never mutates the last valid state and concurrent writers follow S01's
   accepted serial protocol.

**Done:** the same contract can later accept another implementation without changing domain code.

## Slice 4 — Policy service

1. Write the full module/source/action matrix as table-driven failing tests.
2. Implement explicit decisions for ingest, retain raw, project, retrieve, expose, network egress,
   credential use, permission change, unlink, and privacy purge.
3. Require caller/source/action context; missing context denies.
4. Add principal/scope/epoch/confirmation validation and force policy changes during in-flight work.
5. Add the centralized diagnostic boundary and marker redaction tests.

**Done:** the policy contract and mandatory application-port shape deny unknown states and raw
retention. Every later persistence/exposure slice must add an integration test enumerating its entry
points, epoch propagation, and final exposure recheck before that slice can pass.

## Slice 5 — Plugin contract and discovery

1. Promote S02 fixture cases into contract tests.
2. Implement provider protocols and manifest validation without importing concrete providers.
3. Implement side-effect-free entry-point discovery and explicit activation with reviewed
   manifest plus resolved lock/SBOM closure approval and narrow injected ports.
4. Add compatibility, duplicate, failure isolation, capability gating, honest trust-warning, and
   transitive-artifact-drift tests.

**Done:** builtin and external fixture providers pass the same suite; installation alone cannot
activate code or network.

## Slice 6 — Projection lifecycle seam

1. Write failing tests for initialize/status/project/delete-derived/rebuild and projection ledger.
2. Implement only generic orchestration and a deterministic in-memory fixture projection.
3. Prove delete/rebuild does not change canonical file hashes.

**Done:** SQLite and future memory providers can plug in without owning truth.

## Slice 7 — Application services and in-process SDK

1. Write failing command/query/error conformance tests for source config/sync, observation/candidate
   lifecycle, review/confirmation, context retrieval, privacy inventory, purge, export, and health.
2. Implement service ports, unit of work, principal/scope lookup, action canonicalization/digest, and
   ADR-0013 confirmation verification without MCP/model authority (terminal-only approval taking only
   core-generated IDs; sandboxed and SDK-level approve fail closed; isolated `-I` entry point),
   evidence-only status derivation (`not_in_effect` / `unverified`, session-bound), and out-of-band edit
   detection before every policy decision (narrowing honored; widening/mixed/retag quarantined;
   restore/migration/import never re-baseline). Every case in ADR-0013 Verification is a failing test
   first; the flag/env/config enumeration test proves no override.
3. For Vault actions atomically consume nonce with mutation. For external actions atomically consume
   nonce with a durable idempotent operation journal; fault concurrent approval, pre/post commit,
   effect-before-receipt, restart/retry, and digest/scope change.
4. Implement proposal-only InferenceProvider plus structured-host-proposal fixture; prove it cannot
   persist, approve, promote, or expose.
5. Expose a versioned in-process SDK and prove direct SDK/fixture CLI adapters return the same errors.

**Done:** interfaces cannot import Vault implementations/provider internals; quarantined observations
cannot become exposed truth; accepted memory view rebuilds from canonical records alone; all ADR-0013
Verification cases pass.

## Final verification

- Unit, contract, integration, schema snapshot, type, lint, secret, dependency/license checks pass.
- Threat-model abuse cases and ADR-0010 marker/purge/restore cases pass.
- Property tests must cover valid/system-time ordering, supersession acyclicity, memory-transition
  legality, idempotency, authority conflict, policy monotonic epoch, and purge non-resurrection.
- Mutation testing must exercise domain/policy/application modules; any surviving critical-boundary
  mutant requires a recorded test addition or reviewer-approved exception with rationale.
- Clean wheelhouse install and socket-denied runtime pass on the compatibility matrix.
- Executable documentation examples for schema, SDK, CLI fixture, migration, and restore pass.
- Independent architecture/security review has no blocking finding.
- `STATE.md`, `HANDOFF.md`, ADRs, and user/developer documentation are updated.

## Explicit exclusions

No embeddings, LlamaIndex, Mem0, Graphiti, Docker, remote service, plugin registry, broad web UI, or
automatic Profile promotion. Any new heavy dependency requires an ADR.

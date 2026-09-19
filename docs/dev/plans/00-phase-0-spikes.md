# Phase 0 Execution Plan — Decision-Changing Spikes

**Status:** Ready after independent plan review; the S00 development namespace is complete.

## Objective

Retire the uncertainties that could invalidate schemas, packaging, retrieval, MCP, or source
identity before production code is created. Spike code is disposable and remains outside the future
package unless explicitly promoted by a reviewed change.

## Work order

### 1. S00 — namespace and license

1. Produce `docs/dev/spikes/S00-name-license.md` with PyPI/GitHub collision checks, import spelling,
   distribution spelling, executable name, and top alternatives.
2. Record Apache-2.0/MIT implications and the proposed third-party notice policy.
3. Use the documented temporary namespace for local engineering. Obtain maintainer decisions for
   public brand/package migration and license before release or external contributions.

### 2. S01 — schema/Vault prototype

1. First write invalid/valid golden fixtures for every v1 record and cross-reference, including
   Observation/CandidateMemory/Memory/ReviewEvent and SourceConfig/AuthorityPolicy.
2. Add failing tests for exact serialization, unknown versions, broken supersession, invalid temporal
   intervals, missing provenance/trust/retention/epoch, invalid confirmations/deletion receipts,
   interrupted writes, restore-after-purge, and v0→v1 migration.
3. Build the smallest prototype that makes tests pass.
4. Kill writes at each durability boundary and inspect the Vault.
5. Exercise multiprocess simultaneous append/supersede, stale expected version, reader during commit,
   lock-holder crash, abandoned-lock recovery, directory durability, and lost-update detection on the
   fixed Gate 0 macOS 26.2/APFS baseline. Accept one valid serial outcome and no partial/orphan state;
   unknown/network/synced filesystems must fail closed pending later admission. Invoke only
   `/opt/homebrew/bin/python3.13`; record and assert interpreter/SQLite/OS/`statfs` facts against the
   `COMPATIBILITY.md` baseline, and include negative probes (injected non-APFS, non-local, and
   synced-root `statfs`/path) that must refuse.
6. Record format, protocol/assumptions, timings, failure cases, and ADR changes in
   `docs/dev/spikes/S01-vault.md`.

### 3. S02 — plugin discovery prototype

1. Build a fixture wheel with one valid entry point and manifest.
2. Add failing probes for no-side-effect discovery, duplicate IDs, broken import, incompatible
   contract, undeclared capability, and disabled plugin.
3. Implement discovery/activation only far enough to execute the probes and record the reviewed
   manifest and complete resolved distribution closure. Clearly display that in-process activation
   grants code execution; mutate one transitive artifact and require renewed approval.
4. Record whether entry points are sufficient in `docs/dev/spikes/S02-plugins.md`.

### 4. S03 — bilingual retrieval experiment

1. Freeze and checksum a licensed/synthetic Chinese-English corpus, expected judgments, metric code,
   numeric blocking thresholds, and an untouched holdout before running any comparison.
2. Implement three isolated index/query variants defined in `SPIKES.md`.
3. Produce machine-readable metrics plus error analysis; runner exits non-zero on any missed threshold.
4. Record the precommitted thresholds, result, and ADR-0004 impact in `docs/dev/spikes/S03-fts.md`.

### 5. S04 — MCP host conformance

1. Pin the exact supported SDK version in the spike environment.
2. Define snapshot-tested tool schemas with bounded fake data and disabled modules.
3. Exercise STDIO initialization, capability negotiation, tool errors, budgets, and shutdown in
   Codex and Claude Code; probe other hosts when available.
4. Prove MCP cannot issue approval; unconfirmed consequential calls, forged principal,
   stale/replayed/mismatched confirmation, confused-deputy, disabled-module, and policy-epoch-race
   cases deny; candidate observations cannot auto-promote. Apply each adapter's ADR-0013 profile in
   the real host and run every ADR-0013 Verification case: terminal-only approval, confined agent
   approval fails closed, no `confined` claim, `not_in_effect` on core-observed escape evidence,
   `unverified` otherwise, session binding, read-deny, and quarantine. Record required keys and the
   core-observable evidence source per host version in the `COMPATIBILITY.md` table.
   Treat injection probes as defense in depth.
   **S04 acceptance note (2026-09-19).** S04 was accepted with a recorded partial real-host run. The
   following are deferred to M1.4/S12 as release-blocking probes for each host version:
   - real-host Claude built-in Read/Edit/Write deny-rule probes;
   - Apple Event canaries and `additionalDirectories`;
   - agent/SDK approve inside a confined session;
   - agent write of hook/MCP entries to project settings;
   - the workspace shadow-module/`PYTHONPATH` case.

   Codex legacy `workspace-write` protected-read denial is a disclosed limitation, never claimed.
5. Test concurrent confirmers plus crashes immediately before/after durable journal commit, external
   effect success before receipt update, restart/retry, idempotent exactly-one durable intent, and
   egress revoked between journal commit and worker execution (`cancelled_policy`, no network).
6. Run the server/application process with socket creation denied or an isolated network namespace.
   Enumerate file descriptors/destinations; unexpected server/dependency network fails. STDIO output
   is expected disclosure to the host and hosted probes use synthetic data only.
7. Record exact host versions, host/model boundary, and vendor traffic separately. `proven_local`
   admission requires core policy, pinned builtin adapter/runtime hashes, and end-to-end model egress
   evidence; Claude Code/Codex default to remote/unknown.
8. Publish matrix and ADR impact in `docs/dev/spikes/S04-mcp.md`.

### 6. S05A — common source identity contract

Before v1 schema freeze, use representative Folder/MarginNote/GitHub fixtures to prove the common
SourceLocator/Snapshot/CandidateDelta/SourceConfig extension boundary, idempotency, ambiguity,
authority conflicts, truncation, and source disappearance. Record in `docs/dev/spikes/S05A-sources.md`.

Provider-specific S05B suites run immediately before each provider ships. Sanitize fixtures; never
commit private exports or credentials. Include root/origin escape, symlink and TOCTOU,
XML/archive/document bombs, deceptive metadata/instruction injection, secret exclusions, size/time
limits, redirects, pagination, rate limits, and offline-mode canaries.

## Validation command contract

The production toolchain is intentionally not invented before S00. Each spike must include a
reproducible command in its result note, exit non-zero on failed acceptance criteria, avoid network
unless explicitly declared, and clean up disposable services.

## Exit checklist

- [ ] Each spike result distinguishes measured fact from interpretation.
- [ ] Fixtures are safe to commit and licensed.
- [ ] Blocking criteria pass or the affected ADR/roadmap is revised.
- [ ] Independent reviewer confirms conclusions follow from the evidence.
- [ ] No spike dependency leaked into the production dependency set by accident.

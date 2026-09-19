# Development Roadmap

Status labels: **must-have**, **dogfood**, **seam**, **future**, **nice-to-have**. Work packages are
ordered by the dependency graph; a later package may start only when its inputs are accepted.

## Gate 0 — Planning and proof

- [x] Research eight required upstream domains.
- [x] Draft architecture ADRs and MVP dependency graph.
- [x] Draft data-flow threat model and retention/destruction ADR after security review.
- [x] Independent architecture, privacy/security, and execution/test review (reports 07, 10, 14).
- [ ] Resolve blocking review findings (done) and accept/revise ADRs after spike results.
- [x] Record collision-checked temporary package namespace (S00).
- [ ] Run S01–S04 and common contract S05A; run S05B per source before shipping it.
- [x] Run executable relay checks and cold Codex/Claude Code continuation drills (reviews 05, 11).

**Exit:** No blocking plan findings; threat model and ADR-0010 pass security re-review;
decision-changing spikes have written results; the temporary scaffold namespace is fixed. Public
name/license remain a release gate.

## Milestone 1 — Portable Personal Context Core

### M1.1 Foundation — must-have

- Versioned Fact, Observation, CandidateMemory, Memory, ReviewEvent, Evidence, Snapshot,
  CandidateDelta, SourceConfig/AuthorityPolicy, module-policy, and plugin-manifest schemas.
- Trust/taint, policy epoch, confirmation digest, retention label, deletion receipt/ledger schemas.
- Canonical Vault repository with atomic writes, migrations, validation, audit events, and backups.
- Central fail-closed permission/retention policy.
- Provider protocols, capability/error model, builtin registry, and external fixture entry point.
- Application services plus versioned in-process SDK, public error model, InferenceProvider/structured
  host-proposal port, ADR-0013 confirmation + confinement status, durable external-operation journal, and
  canonical interaction-memory lifecycle transitions.
- Locked/reviewed dependencies, isolated build, SBOM/license/vulnerability/secret checks from the
  first scaffold.

**Exit:** Golden records/temporal and memory transitions round-trip; concurrent writers have one valid
serial outcome; migration/backup restore failure matrix passes; projection deletion cannot alter the
Vault; policy contract/mandatory port matrix passes; wheel/sdist clean-install CI passes. Linux
support is claimed only after the S01 concurrency/crash suite passes unchanged on an exact Ubuntu
LTS/ext4 CI runner (owner: M1.1 Slice 3); until then Linux is documented unsupported.

### M1.2 Ingestion — must-have + dogfood

- Ingestion coordinator: snapshot → candidate delta → validation/review → canonical commit.
- S05B admission followed by Folder Source, MarginNote Source, and GitHub Standard Source.
- Sync status, ambiguity queue, parser versioning, tombstones, and replay.
- Hardened parsers/root/origin limits plus injection, escape, bomb, secret, and egress tests.
- Dogfood fixtures made from sanitized maintainer exports/repos.

**Exit:** Idempotent and incremental fixture suites; no source disappearance silently deletes facts.

### M1.3 Builtin memory and retrieval — must-have

- Structured observation submission and candidate-memory lifecycle; no raw retention by default.
- SQLite projection and selected bilingual FTS strategy.
- Bounded Context service implementing PRD L0–L4, time/module/provenance filters, and conservative
  response-unit budgets.
- Versioned evaluation corpus/metrics/thresholds from `EVALUATION_PLAN.md` accepted before work starts.
- Privacy inventory/status showing managed copy locations, size/age, retention, egress grants, and
  exact effects of unlink, forget, purge, and uninstall, including externally controlled host
  transcripts/caches and their known/unknown deletion controls.

**Exit:** Temporal, permission, bilingual relevance, and rebuild tests pass; measured context budget.

### M1.4 Agent and human interfaces — must-have + dogfood

- CLI for init/config/sync/status/query/observe/review/export/doctor.
- MCP STDIO tools over application services; read-only resources only where supported.
- Claude Code and Codex adapters, bounded L0 card, Starter Lite and Researcher recipes.
- Guided setup + basic Plugin Advisor: language, host/environment, source consent, memory/privacy,
  recipe recommendation, key/time/privacy/trade-off preview, one final confirmation, install,
  doctor/smoke, and Vault location. Cancellation before confirmation leaves no mutation or grant.
- English and Simplified Chinese setup/help/errors.
- Claude Code/Codex are first-class M1 adapters; Cursor/Claude Desktop receive protocol compatibility
  notes only and remain later adapter work.

**Exit:** Fresh-machine scripted setup and real daily task in both hosts; S12 passes for each adapter;
MCP confirmation/replay/injection tests pass; no prior chat required; and the ADR-0013 real-host
probes deferred from S04 pass for each adapter version.

### M1.5 Release quality — must-have

- Update threat model; finalize dependency/license inventory and release hardening.
- Unit/contract/integration/E2E/evaluation suites and deterministic fixtures.
- README, bilingual quickstart, contribution/security/code-of-conduct docs.
- `SECURITY.md` names supported versions, private reporting channel, response owner, and disclosure
  process before external users/plugins.
- Reproducible build, changelog, version policy, rollback and migration drill.
- Maintainer confirms public brand/package migration and license before release/contributions.
- `CITATION.cff`, `CODEOWNERS`, `THIRD_PARTY_NOTICES.md`, and post-contract skills:
  `add-source-provider`, `run-evals`, `audit-licenses`, and `release`, each smoke-tested on a fixture.

**Exit:** Independent code/security review has no blocking findings; install/smoke tests pass.

## Milestone 2 — Daily Driver — future after M1 evidence

- Mem0 adapter after S10; hybrid retrieval; Obsidian source/interface; GitHub Deep mode.
- ADR/spike for risk-tiered automatic CandidateMemory acceptance (MVP deliberately requires the
  ADR-0013 confirmation, overriding PRD §16 for MVP); automatic Profile promotion remains separate and
  slower.
- Automatic Profile promotion, retrospective review workflow, Personal Memory recipe.
- Maintainer's full setup and longitudinal quality evaluation.

## Milestone 3 — Ecosystem — future

- Graphiti after S11; LlamaIndex retrieval; plugin scaffolds; external conformance certification.
- Community registry/catalog and advanced recipes only after governance/security design.

## Milestone 4 — Public Growth — future/nice-to-have

- Polished docs site, demos, public benchmarks/roadmap, registry distribution, showcases, releases.

## Definition of milestone completion

A milestone/slice may not start without an accepted TDD plan naming ownership, fixtures, failure
cases, exact commands, and exit evidence. Completion requires every binary acceptance check and
recorded exception to pass, executable documentation examples to run, privacy/license checks to
pass, `STATE.md`/`HANDOFF.md` to be current, and the work to be committed. Draft the next detailed
plan only after its upstream contract stabilizes.

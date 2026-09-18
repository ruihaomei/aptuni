# Execution, Test, and Repository-Quality Review

- **Date:** 2026-09-18
- **Scope:** PRD §33–§51; ADR-0001–0010; `THREAT_MODEL.md`; dependency graph; roadmap;
  spike catalog; Phase 0 and M1.1 plans; agent relay files
- **Perspective:** dependency order, executable acceptance criteria, TDD/failure paths, migration and
  rollback, installation, bilingual/cross-host coverage, restartability, and scope discipline

The plan has a strong core: it keeps the Vault canonical, delays Mem0/Graphiti/LlamaIndex, uses
failure-first tests for high-risk boundaries, and makes security remediation concrete. The following
findings are about whether a fresh agent can execute the plan and determine pass/fail without making
new architectural decisions mid-implementation.

## Blocking findings

### B1 — S04's `no content egress` criterion is not measurable at the stated boundary

**Locations:** `SPIKES.md:51-61`, `plans/00-phase-0-spikes.md:48-57`,
`THREAT_MODEL.md:16-31`, `THREAT_MODEL.md:119`

The MCP server is expected to return personal context to the host, and Claude Code/Codex may then
send that result to their model service. A process-wide canary around the whole host will therefore
observe intended host traffic, while `no content egress` literally forbids the product's intended
STDIO result. The current Gate 0 criterion can either fail for a correct implementation or pass
without proving that the MCP server and its dependencies made no undeclared network call.

**Required fix:** define separate observation boundaries and pass/fail rules:

1. Run the MCP/application process with socket creation denied or in an isolated network namespace;
   assert zero server/dependency network destinations in local-only mode.
2. Treat the bounded STDIO response as an explicit, expected disclosure to the configured host.
3. Test only synthetic canary data in hosted agents and record the host/model trust boundary and
   disclosed vendor traffic separately.
4. Replace `no content egress` with `no undeclared server-initiated egress`; enumerate expected file
   descriptors/destinations and make any unexpected one fail the spike.

### B2 — S01 does not prove the concurrency behavior that Gate 0 relies on

**Locations:** `SPIKES.md:19-28`, `plans/00-phase-0-spikes.md:21-29`,
`KNOWN_ISSUES.md` KI-006, `plans/01-foundation-tdd.md:56-66`

KI-006 says S01 must retire crash/concurrency risk before implementation, but S01 only tests
serialization, migration, and interrupted writes. Competing writers are deferred to production
Slice 3. The single-writer/lock/optimistic-version choice affects the canonical write protocol and
can invalidate the S01 result after the schema is frozen.

**Required fix:** add a multiprocess S01 matrix before Gate 0 exits: simultaneous append and
supersede, stale expected version, lock-holder crash, abandoned lock recovery, reader during commit,
directory durability, and deterministic lost-update detection. State the supported filesystem/OS
assumptions and accept only a protocol with one valid serial outcome and no orphaned partial state.

### B3 — Source identity is ordered both before and after the v1 schema freeze

**Locations:** `MVP_DEPENDENCY_GRAPH.md:8-12`, `MVP_DEPENDENCY_GRAPH.md:48-53`,
`plans/00-phase-0-spikes.md:5-9`, `plans/00-phase-0-spikes.md:59-64`,
`ROADMAP.md:15`, `SPIKES.md:63-71`

The dependency graph puts source-identity proof in Phase 0 before `Snapshot`/`CandidateDelta` v1,
but the execution plan delays every S05 variant until immediately before each M1.2 provider ships.
S05 explicitly affects ADR-0006, so a real MarginNote/GitHub result may change an already published
schema and force an avoidable migration.

**Required fix:** split S05 into (a) a Gate 0 contract spike using representative
Folder/MarginNote/GitHub identity fixtures to validate the common locator/delta envelope before v1 is
frozen, and (b) provider admission suites immediately before each provider ships. Alternatively,
document the extension/versioning boundary that guarantees provider-specific discoveries cannot
change the common v1 schema, and update the graph and all gate text to match one order.

### B4 — The required Plugin Advisor/basic install flow has no owned deliverable or acceptance test

**Locations:** `docs/product/PRD.md:2260-2289`, `docs/product/PRD.md:2366-2397`,
`MVP_DEPENDENCY_GRAPH.md:35-38`, `ROADMAP.md:55-63`

The graph labels `setup/advisor flow`, but M1.4 lists only CLI, MCP, host adapters, recipes, and
translations. Nothing owns the PRD's Plugin Advisor basic flow or the 15-step first-time Agent
installation experience. M1 can currently pass its written exit while omitting a named MVP feature.

**Required fix:** add an M1.4 deliverable and scripted E2E acceptance matrix covering language,
environment/host detection, existing sources, memory/privacy choices, Recipe recommendation,
plugin/key/time/privacy/trade-off preview, one final confirmation, install, doctor/smoke test, and
Vault-location output. Cancellation before confirmation must leave no activated plugin, source
grant, credential reference, or Vault mutation.

## High-priority findings

### H1 — Build and install verification is too weak for the first scaffold

**Locations:** `plans/01-foundation-tdd.md:34-42`, `plans/01-foundation-tdd.md:101-108`,
`ROADMAP.md:65-74`, `docs/product/PRD.md:1599-1635`

Slice 1 adds only "CI-equivalent" local commands; actual CI and a built-artifact install are not
owned until the generic M1.5 release stage. Importing from a checkout can pass while the wheel omits
schemas, entry-point metadata, translations, or package data. `Clean install works offline from the
resolved dependency set` is also ambiguous: it could mean an impossible uncached PyPI install, an
install from a prepared wheelhouse, or merely offline runtime.

**Action:** make Slice 1 build sdist+wheel, install each non-editably into a clean environment, run
import/CLI/schema/plugin-fixture smoke tests, and run the same check in CI. Declare the supported
Python/OS matrix. Define offline acceptance precisely (for example, install from an explicit local
wheelhouse, then run with sockets denied) and keep runtime no-key/no-network as a separate test.

### H2 — Migration and backup checks do not yet define recoverable failure semantics

**Locations:** `plans/00-phase-0-spikes.md:23-29`, `plans/01-foundation-tdd.md:56-68`,
`ROADMAP.md:25-33`, `ROADMAP.md:72`, `DECISIONS/ADR-0010-retention-destruction-and-restore.md:65-69`

The plan covers v0→v1 and restore-after-purge, but not failure halfway through a multi-record
migration, resumption/idempotency, corrupted newest backup, incompatible future versions, or proving
that a backup is restorable before rotation. "Backup" and "migration" can pass without a successful
ordinary restore or a defined rollback/roll-forward policy.

**Action:** define version markers and transaction boundaries; add fault injection at each migration
step, retry/idempotency, unknown-newer-version refusal, last-known-good backup restore, corrupted
generation fallback, and restore verification before rotation. Make these M1.1 exit criteria rather
than waiting for the M1.5 drill.

### H3 — Product evaluation is named but not planned as a determinable gate

**Locations:** `docs/product/PRD.md:2235-2252`, `ROADMAP.md:45-53`,
`ROADMAP.md:65-74`, `SPIKES.md:41-49`

S03 measures retrieval only. The roadmap does not assign definitions, fixtures, baselines, or
thresholds for unsupported-profile claims, provenance coverage, correction rate, memory
accept/reject rate, setup completion/decisions, plugin install success, Agent setup success, or time
to first useful personalization. A generic "evaluation suites" bullet cannot prevent declaring M1
complete with good FTS and poor personalization/provenance behavior.

**Action:** add an evaluation plan before M1.3 starts. Version the task corpus and human judgments,
define numerator/denominator and thresholds before measurement, distinguish automated gates from
dogfood telemetry/manual scorecards, and map each PRD metric to an owner and milestone exit.

### H4 — The bilingual and cross-host matrix is underspecified

**Locations:** `ROADMAP.md:55-63`, `SPIKES.md:51-61`, `SPIKES.md:87-93`,
`docs/product/PRD.md:2264-2288`

S04/S12 correctly gate Claude Code and Codex behavior, but the plan does not freeze supported host
versions or test upgrade/downgrade behavior. "English and Simplified Chinese setup/help/errors" has
no matrix for locale fallback, mixed-language queries, Unicode normalization, Chinese filenames and
Vault paths, untranslated-message detection, or byte/token budget differences.

**Action:** publish a versioned compatibility matrix (OS, Python, SQLite, host, adapter, locale),
snapshot both languages' CLI/help/error output, test CJK paths and normalization, and run the same
fresh-install/daily-task scenario in both locales and both required hosts. Mark unsupported host
versions as explicit documented gaps, not silent pass results.

### H5 — The relay's promised executable checks are unscheduled, and current state is already stale

**Locations:** `DECISIONS/ADR-0008-cross-host-development-relay.md:46-55`,
`docs/product/PRD.md:1799-1839`, `STATE.md:7-19`, `HANDOFF.md:15-27`

ADR-0008 requires an instruction-size check, stale-handoff detector, and fresh-session relay drill,
but no roadmap slice owns them. `STATE.md` still reports nine proposed ADRs although ADR-0010 exists,
and the current handoff does not record the remediation files touched or validation run. That is a
small but direct demonstration that a new host can receive stale state.

**Action:** add a Gate 0 relay check that validates ADR index/file parity, local links, required
state fields, current review verdicts, and recorded validation. Perform and record one cold Codex
and one cold Claude Code continuation drill before accepting ADR-0008. Update the harness in the
same change whenever a review remediation changes the execution state.

### H6 — The Foundation policy "done" claim cannot be proven inside the stated scope

**Locations:** `plans/01-foundation-tdd.md:7-11`, `plans/01-foundation-tdd.md:70-80`,
`THREAT_MODEL.md:16-31`, `ROADMAP.md:35-63`

M1.1 explicitly excludes application services, yet Slice 4 claims every persistence/exposure
application path requires a policy decision. A policy unit-test matrix cannot prove that later
ingestion, context, CLI, MCP, and adapter call sites cannot bypass it.

**Action:** narrow the M1.1 criterion to the policy contract and mandatory port shape. Add an
architecture/integration test gate to every later slice that enumerates all persistence/exposure
entry points and asserts deny-by-default, policy-epoch propagation, and final exposure recheck.

## Medium-priority findings

### M1 — Later MVP milestones need a plan-acceptance gate before agents may implement them

**Locations:** `ROADMAP.md:35-74`, `MVP_DEPENDENCY_GRAPH.md:68-74`,
`docs/product/PRD.md:2410-2438`

Only Phase 0 and M1.1 have executable plans. That is appropriate for near-term scope, but nothing
explicitly prevents a future agent from implementing M1.2–M1.5 directly from roadmap bullets.

**Action:** state that each milestone/slice requires an accepted TDD plan with ownership, fixtures,
failure cases, exact commands, and exit evidence before it starts. Draft the next plan only after
the preceding contract stabilizes; this preserves progressive planning without planning future
architecture prematurely.

### M2 — S03's execution order does not lock thresholds before running variants

**Locations:** `SPIKES.md:41-49`, `plans/00-phase-0-spikes.md:40-46`

The catalog says thresholds are defined before results, but the plan freezes judgments, runs all
variants, and only then says to "record thresholds, result". This permits accidental threshold
tuning to the observed winner.

**Action:** write and checksum/commit corpus, query judgments, metric code, and numeric thresholds
before any comparative run; keep one untouched holdout slice; make the runner exit non-zero when the
chosen strategy misses any blocking threshold.

### M3 — Several verification phrases are not binary acceptance criteria

**Locations:** `plans/01-foundation-tdd.md:101-108`, `ROADMAP.md:91-94`

"Mutation/property testing ... where practical", "user docs match", and "behavior and migrations
are tested" cannot be independently judged.

**Action:** name the required temporal/policy properties, minimum mutation targets or an explicit
exception record, documentation command/examples that are executed, and the artifact that records
every migration fixture/result. Avoid coverage percentages as a substitute for behavior coverage.

### M4 — Required agent skills and some repository-quality artifacts have no milestone owner

**Locations:** `docs/product/PRD.md:1641-1655`, `docs/product/PRD.md:1911-1945`,
`docs/product/PRD.md:1988-1994`, `ROADMAP.md:65-74`,
`DECISIONS/ADR-0008-cross-host-development-relay.md:38-50`

Deferring workflow skills until contracts stabilize is correct, but the roadmap never schedules the
minimum post-contract skills. M1.5 also omits `CITATION.cff`, `CODEOWNERS`, and
`THIRD_PARTY_NOTICES.md` from its explicit repository artifact list.

**Action:** assign `add-source-provider`, `run-evals`, `audit-licenses`, and `release` skills after
their contracts exist, with smoke fixtures that execute their instructions. Add the missing
repository artifacts to the release checklist or explicitly defer them with rationale.

### M5 — The foundation plan still carries an obsolete package placeholder after S00

**Locations:** `plans/01-foundation-tdd.md:3-5`, `STATE.md:21-26`, `SPIKES.md:9-17`

S00 selected `personal_context_core` for development, but the executable plan still says paths use
`<package>` until S00 fixes the namespace. A fresh agent must choose whether to substitute it and can
create the wrong tree.

**Action:** replace the placeholder with the temporary distribution/import/CLI names from the S00
result and document the future public-name migration boundary.

## Low-priority findings

No additional low-priority findings. The future-provider seams are restrained enough: the plan does
not prematurely implement Mem0, Graphiti, LlamaIndex, HTTP, registry, or UI infrastructure.

## Verdict

**BLOCK**

Gate 0 should not pass until B1–B4 are resolved and re-reviewed. In particular, S04 currently has an
unpassable privacy assertion, S01 does not test its claimed concurrency blocker, source identity has
two conflicting positions in the dependency order, and a named MVP flow can be omitted while all
current roadmap boxes are checked. The high-priority findings should be incorporated before M1.1 or
the affected milestone begins; the medium findings can be scheduled without expanding the MVP.

# Architecture Planning Review

- **Reviewer:** independent architecture planning agent
- **Date:** 2026-09-18
- **Scope:** PRD v2.1, design rationale, research synthesis, ADR-0001–0010, threat model,
  dependency graph, roadmap, spikes, execution plans, and cross-host harness
- **Verdict:** **BLOCK**

The plan has a sound core direction: one open-format source of truth, replaceable projections,
provider-neutral contracts, a deliberately small one-distribution MVP, and a repository-carried
development relay. The security remediation is architecturally consistent overall: it makes trust,
authorization, retention, purge, restore, plugin trust, and L0 lifecycle explicit without turning
optional backends into authorities.

One unresolved contract gap still prevents schema freeze. The remaining findings should also be
resolved or explicitly dispositioned before the affected public interfaces are accepted.

## Blocking findings

### B1 — The canonical interaction-memory lifecycle has no canonical record contract

**Status:** verified inconsistency, not a speculative recommendation.

The PRD makes `Interaction → Observation → Candidate Memory → Memory → possibly Profile Fact` a
distinct lifecycle and requires structured memory to persist after raw conversation is discarded
(`docs/product/PRD.md`, §14, lines 733–770). ADR-0003 says a `MemoryProvider` receives *canonical
observations/facts* and is only a projection (`ADR-0003`, lines 34–41), but ADR-0001 defines only the
canonical Fact contract (`ADR-0001`, lines 33–44). Neither a separate Observation/CandidateMemory/
Memory representation nor an explicit, lossless encoding of those states into Fact is selected.

The implementation sequence freezes schema v1 before Builtin Memory: S01 covers Fact, Evidence,
Snapshot, and CandidateDelta (`SPIKES.md`, lines 19–28); M1.1 and Foundation Slice 2 enumerate the
same domain family plus security records (`ROADMAP.md`, lines 23–33;
`plans/01-foundation-tdd.md`, lines 44–54). Only M1.3 later introduces observation submission and the
candidate-memory lifecycle (`ROADMAP.md`, lines 45–53). The dependency graph likewise moves from the
Vault directly to “Builtin Memory” without a canonical memory application service or write path
(`MVP_DEPENDENCY_GRAPH.md`, lines 10–28).

**Impact:** Implementers must either store the product's second primary data domain in a derived
provider, overload Fact ad hoc, or revise the supposedly frozen schema and Vault contract during
M1.3. The first violates canonical ownership and provider portability; the others make the provider
contract and migration plan indeterminate.

**Required fix before Gate 0 passes:**

1. Amend ADR-0001/0003 or add an ADR that defines the canonical lifecycle and identity links among
   Observation, Candidate Memory, Memory, Evidence/Episode, and optional promoted Fact. It is valid
   to use one tagged record envelope, but that choice and its invariants must be explicit.
2. Define which transitions are canonical writes versus derived provider operations, including
   idempotency, review state, contradiction/supersession, retention, and `forget`/purge interaction.
3. Add the chosen records and cross-reference failures to S01 golden fixtures and M1.1 schema work,
   or explicitly defer “schema v1 freeze” until those contracts exist.
4. Add an application-service write path to the dependency graph: host/inference proposal → policy
   → canonical observation/candidate transaction → provider projection. Rebuild must reproduce the
   same memory view from the Vault alone.

## High-priority findings

### H1 — Progressive-disclosure layer names conflict with the mandatory PRD contract

The PRD defines five layers: L0 identity, L1 context index, L2 modules, L3 facts/memories, and L4
evidence/raw source (`docs/product/PRD.md`, §18, lines 901–917). ADR-0005 and the roadmap instead
define L0/L1/L2 as identity/retrieval/evidence (`ADR-0005`, lines 54–57; `ROADMAP.md`, lines 47–50).
This is not merely a compressed implementation because the same labels now mean different data
sensitivity and expansion depth.

**Action:** Preserve the PRD's L0–L4 vocabulary in schemas, tools, tests, and docs, or obtain an
explicit PRD amendment. A tool may combine layers in one bounded response, but it should report
which canonical layers were included.

### H2 — Source authority and conflict precedence are missing from the ingestion contract

The PRD makes MarginNote primary authority for `studied` claims and requires a Folder source to carry
semantic role/`authority.primary_for` configuration (`docs/product/PRD.md`, §8 lines 401–405 and §9
lines 441–463). ADR-0006 records source IDs, confidence, ambiguity, and provenance, but not user-owned
authority configuration or deterministic conflict precedence (`ADR-0006`, lines 34–46). M1.1 does
not list a SourceConfig/AuthorityPolicy record, while M1.2 expects conflict/review application.

**Impact:** Two valid candidate deltas can disagree and the coordinator has no portable basis for
whether to apply, supersede, merge, or require review. Confidence is not a substitute for user-set
source authority.

**Action:** Add a versioned source configuration/authority contract before source schemas stabilize.
Define precedence as policy input, never provider hard-coding, and test conflicting MarginNote,
Folder, and GitHub evidence plus authority changes over time.

### H3 — The provider-neutral application API and inference boundary are not planned as components

The PRD requires a task-oriented Core API and `MCP + REST/SDK`, and defines `InferenceProvider` as a
separate extension point (`docs/product/PRD.md`, §11 lines 588–613 and §19–§20 lines 953–1004).
ADR-0003 mentions inference separation, while the dependency graph contains only ingestion/context,
CLI, and MCP nodes. “Application-service APIs” appear only as a scheduling sentence
(`MVP_DEPENDENCY_GRAPH.md`, line 71); no owned port, stable error model, or in-process SDK surface is
scheduled.

The security remediation also depends on an application-owned principal/scope store and trusted
confirmation issuer/verifier (`ADR-0005`, lines 39–48), but the plan does not assign those
responsibilities to a component. S04 can probe a fake MCP server, yet it cannot settle who issues and
consumes confirmation evidence in production.

**Action:** Add an application-services/SDK boundary between domain services and every interface.
Place authorization/confirmation ownership there, expose a versioned in-process SDK for MVP, state
whether REST is post-MVP, and define the minimal InferenceProvider/host-observation port without
requiring a model dependency.

### H4 — “Bi-temporal” is claimed without transaction-time or reverse-link semantics

ADR-0001 names bi-temporal history as a driver but lists valid-time bounds plus point timestamps
(`observed_at`, `ingested_at`) and both `supersedes` and `superseded_by` (`ADR-0001`, lines 17–40).
It does not say whether transaction history is append-only, whether `superseded_by` mutates an old
record or is derived, or how a correction differs from a later valid-world change.

**Action:** Before S01 acceptance, define valid time versus system/transaction time and the single
source of truth for supersession links. Add out-of-order observation, correction, same-valid-time
conflict, and historical “as known at” golden cases. If only valid-time history is intended, remove
the bi-temporal claim.

## Medium-priority findings

### M1 — The dependency graph places provider-specific S05 inside the global pre-schema phase

The graph's single P0 node includes “source identity” and gates canonical schemas
(`MVP_DEPENDENCY_GRAPH.md`, lines 8–12), while the roadmap and execution plan correctly make S05 a
per-provider ship gate after the global Gate 0 work (`ROADMAP.md`, lines 13–19; `SPIKES.md`, lines
63–71). As drawn, real MarginNote fixtures can block unrelated foundation work and S05 appears to run
before the CandidateDelta contract it exercises.

**Action:** Split P0 into S01–S04 and three S05 provider gates after the shared Snapshot/
CandidateDelta contract and before each provider ships.

### M2 — Plugin Advisor and consent-led onboarding lack an MVP work package and exit criteria

The dependency graph labels Recipes as “setup/advisor flow,” but M1.4 schedules recipes and bilingual
help without explicitly scheduling the PRD's Plugin Advisor basic flow, language-first questions,
privacy choice, source discovery consent, cost preview, and final confirmation (`ROADMAP.md`, lines
55–63; `docs/product/PRD.md`, §24–§29 and §48 lines 2260–2288).

**Action:** Add one bounded CLI/agent-guided setup slice and scripted acceptance journey. Reuse
plugin manifests and recipes; do not build a marketplace or separate rules engine.

### M3 — Token budgets lack portable accounting semantics

ADR-0005 requires token/result budgets and ADR-0004 promises no content outside the caller's budget,
but no document defines whether the budget is exact model tokens, a conservative estimator, bytes,
or result units. Different hosts/tokenizers make an unqualified hard token guarantee impossible.

**Action:** Define a provider-independent conservative budget contract (including metadata overhead,
truncation markers, and deterministic tie-breaking) and let adapters optionally supply a tokenizer.
S03/S04 and Context-service exits should test the same semantics.

### M4 — Initial-host scope is ambiguous

PRD §20 calls Claude Code, Codex, Cursor, and Claude Desktop the initial supported hosts, while MVP
§48 and the roadmap implement only Claude Code and Codex; S04 permits the other two to remain gaps
(`SPIKES.md`, lines 51–61). This is a reasonable MVP cut, but it is not explicitly reconciled.

**Action:** State that Milestone 1 provides first-class adapters for Claude Code/Codex and only
protocol-compatibility documentation for Cursor/Claude Desktop, or add the missing adapter work.

### M5 — Relay documents contain stale planning state

`RESEARCH_NOTES.md` still says namespace/license confirmation is required before the first scaffold
(lines 48–49), contradicting completed S00 and current release-only gating. `STATE.md` says there are
nine proposed ADRs although ADR-0010 now exists (lines 9–12). These are verified stale facts in the
mechanism intended to support cross-host relay.

**Action:** Update both in the same remediation pass and add the planned stale-state/link check.

## Low-priority findings

### L1 — A release-only decision is presented as an unchecked Gate 0 item

`ROADMAP.md` line 14 places public brand/license confirmation under Gate 0, while the exit text
correctly says it is a release gate (lines 17–19). Move it to M1.5 or mark it explicitly non-blocking
so checklist readers do not infer that local engineering remains blocked.

### L2 — ADR-0010 should state precedence over the history-preservation invariant

ADR-0010 correctly distinguishes supersession from privacy purge, and its design resolves the prior
security deletion gap. A short explicit statement that authorized privacy purge is the deliberate
exception to ADR-0001's history preservation would prevent future agents from retaining prohibited
content in the name of auditability.

## Required remediation for re-review

Gate 0 remains blocked only by **B1**. Resolve it in the ADR/schema/spike/dependency artifacts, then
request focused architecture re-review. H1–H4 should be resolved before accepting the affected ADRs;
the medium/low items may be dispositioned with documented owners and gates.

**Final judgment: BLOCK — 1 blocking, 4 high, 5 medium, and 2 low findings.**

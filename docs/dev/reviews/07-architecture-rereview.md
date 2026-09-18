# Focused Architecture Re-review

- **Reviewer:** independent architecture planning agent
- **Date:** 2026-09-18
- **Scope:** remediation of `01-architecture-review.md`, including ADR-0001/0005/0006/0010/0011/
  0012, dependency graph, roadmap, spikes, execution plans, state/handoff, and relay checks
- **Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

The original architecture blocker is closed. The current plan gives interaction memory canonical
record types and transitions before schema freeze, puts interfaces behind one application/SDK
boundary, and keeps inference proposal-only. The latest dependency graph is acyclic: Vault/policy/
provider contracts feed ingestion, memory, retrieval/context, and then the application facade; the
facade alone feeds CLI/MCP adapters. This removes the earlier `APP → MEM/CTX → APP` loop.

The added records and services are proportionate to stated requirements rather than speculative
framework work. Optional backends, remote HTTP, a registry, and marketplace remain deferred. No
blocking finding remains from the original review.

## Original finding disposition

| Finding | Result | Evidence |
|---|---|---|
| B1 canonical memory lifecycle | **Closed** | ADR-0011 defines the shared envelope, five canonical record types, valid transitions, review, contradiction, forget/purge, and provider rebuild (`ADR-0011`, lines 31–66). S01, M1.1, Foundation Slice 2/7, and the graph include the records before v1 freeze (`SPIKES.md`, lines 19–31; `ROADMAP.md`, lines 23–38; `plans/01-foundation-tdd.md`, lines 53–65 and 121–132; dependency graph lines 12–40). |
| H1 L0–L4 mismatch | **Closed** | ADR-0005 preserves the PRD's five layer names and requires included-layer markers; roadmap and graph use L0–L4 (`ADR-0005`, lines 60–63; `ROADMAP.md`, lines 50–61; graph line 36). |
| H2 source authority | **Closed** | ADR-0006 adds versioned SourceConfig/AuthorityPolicy, user-owned authority, deterministic conflict behavior, and tests across all three MVP sources (`ADR-0006`, lines 39–46 and 77–81). S05A and Foundation freeze the common contract before source admission. |
| H3 application/inference boundary | **Closed** | ADR-0012 assigns policy, transactions, confirmation, public errors, SDK, and proposal-only inference to one application boundary (`ADR-0012`, lines 31–57). Foundation Slice 7 tests the direct SDK and adapter parity; REST remains explicitly behind S21. |
| H4 temporal semantics | **Closed** | ADR-0001 now distinguishes valid time, immutable system time, source ingestion time, forward-only authoritative supersession, correction/world-change/retraction, conflicts, and “as known at” cases (`ADR-0001`, lines 36–65). |
| M1 S05 ordering | **Closed** | S05A is a pre-freeze common-contract proof; S05B is a per-provider admission gate (`SPIKES.md`, lines 76–92). The graph places S05A before schema freeze and S05B after ingestion contracts. |
| M2 onboarding/advisor | **Closed** | Roadmap M1.4 names the full guided flow, and `plans/02-onboarding-advisor.md` provides a bounded state machine, bilingual cases, cancellation, crash recovery, and a 15-step acceptance journey. It explicitly rejects a marketplace/rules engine. |
| M3 portable budgets | **Closed** | ADR-0005 defines conservative UTF-8 response units, fixed overhead, deterministic ranking/truncation, usage markers, and optional stricter tokenizer adapters (`ADR-0005`, lines 70–75). |
| M4 host scope | **Closed** | M1 first-class support is Claude Code/Codex; Cursor/Claude Desktop are compatibility notes only (`ROADMAP.md`, lines 63–76; `COMPATIBILITY.md`, supported matrix). |
| M5 stale relay state | **Closed for reported facts** | Research notes now make public naming/license release-only; STATE reports twelve ADRs and three plans. The current relay unit test, checker, and `git diff --check` all pass. A new checker-lifecycle note remains below. |
| L1 release-only Gate 0 item | **Closed** | Public brand/license moved to M1.5 (`ROADMAP.md`, lines 78–90). |
| L2 purge precedence | **Closed** | ADR-0010 explicitly makes authorized privacy purge the exception to history preservation and forbids auditability from retaining purged content (`ADR-0010`, lines 58–60). |

## Memory lifecycle and SDK consistency

- Canonical records use the same immutable `recorded_at`, valid-time, forward-link, provenance,
  retention, policy, and review semantics as ADR-0001; reverse links are derived.
- Observation and CandidateMemory stay quarantined. Only the application confirmation transaction
  can accept Memory in MVP, and optional providers cannot write Memory or Fact directly.
- ADR-0012 makes CLI/MCP adapters depend inward on versioned application commands/queries. The SDK
  and adapters share error semantics, principal/scope lookup, unit of work, and policy epoch checks.
- Inference returns typed tainted proposals only; it cannot persist, review, expose, or become a
  storage dependency. The structured-host-proposal fixture preserves the zero-extra-key route.
- The current graph has a valid topological order and no application/memory/context cycle.

## New non-blocking findings

### Medium N1 — ADR-0003 still describes the pre-remediation MemoryProvider input set

ADR-0003 says the provider receives canonical “observations/facts” and returns an unspecified
candidate (`ADR-0003`, lines 34–41). ADR-0011 requires providers to project Observation,
CandidateMemory, Memory, Fact, and ReviewEvent, and says provider output is specifically a
CandidateMemory proposal (`ADR-0011`, lines 37–49).

**Action:** Align ADR-0003 with ADR-0011 before accepting either ADR. Define whether Evidence and
revocation ReviewEvents are delivered as projection inputs and make the conformance fixture assert
the accepted/quarantined/exposure view after rebuild. This is not a Gate 0 blocker because ADR-0011,
S01, and Foundation already choose the canonical behavior.

### Medium N2 — The graph still draws concrete defaults where provider ports should be shown

The graph makes Context depend on concrete `Builtin Memory projection` and `SQLite retrieval
projection`, then draws Mem0/Graphiti from the builtin memory node and hybrid/LlamaIndex from SQLite
(`MVP_DEPENDENCY_GRAPH.md`, lines 33–39 and 51–55). That suggests alternative providers extend
concrete defaults, contrary to ADR-0003/0004 and the replaceability invariant.

**Action:** Insert abstract active `MemoryView/MemoryProvider` and `RetrieverProvider` ports. Make
Builtin/Mem0/Graphiti siblings behind the former and SQLite/hybrid/LlamaIndex siblings behind the
latter; Context depends only on the ports and hydrates canonical records. Fix before M1.3 design or
any Milestone 2 provider work.

### Medium N3 — Automatic fast memory formation is not scheduled after the safety-first MVP cut

ADR-0011 requires interactive confirmation for every CandidateMemory→Memory acceptance and says any
later auto-promotion needs a new ADR (`ADR-0011`, lines 37–45). This is a defensible MVP security
choice, but PRD §14 says memory forms quickly and the design rationale calls episodic memory
automatic, while the roadmap schedules only automatic **Profile** promotion in M2 (`ROADMAP.md`,
lines 92–96).

**Action:** Record the MVP deviation explicitly and add a Milestone 2 decision item for risk-tiered
automatic memory acceptance, or state that automatic interaction memory is intentionally removed
from scope. Any future path must keep untrusted-source candidates quarantined and preserve ADR-0005
authorization rules.

### Medium N4 — The relay checker treats every historical BLOCK as permanently current

`check_review_state` ORs `BLOCK` across every non-remediation review and never pairs a review with a
later focused re-review (`tools/check_relay.py`, lines 86–105). Once all current re-reviews approve,
removing stale “BLOCK/re-review pending” text from STATE/HANDOFF will make the checker fail; retaining
that text would make the relay stale.

**Action:** Add review lineage or an explicit current-status manifest and evaluate only the latest
verdict for each review stream. Add a unit test where an earlier BLOCK is superseded by APPROVE.

### Low N5 — Authority should be revalidated at canonical commit

ADR-0006 evaluates authority at candidate system time and says changed authority becomes reviewable.
Make the coordinator explicitly compare the candidate's AuthorityPolicy version/epoch with the
current version immediately before commit; stale candidates should be invalidated or forced to
review. This avoids an old primary-source policy superseding data after the user changes authority.

## Validation

- `python3 -m unittest tests/dev/test_check_relay.py` — **passed (3 tests)**
- `python3 tools/check_relay.py` — **passed**
- `git diff --check` — **passed before this review file**
- No production code was reviewed or authorized by this verdict; Gate 0 spikes and the remaining
  independent security/execution verdicts still govern production start.

## Final judgment

**APPROVE WITH NON-BLOCKING NOTES.** The original B1/H1–H4/M1–M5/L1–L2 findings are sufficiently
remediated, the memory/SDK design is coherent, and the latest graph is acyclic. N1–N4 should be
scheduled before the stated downstream gates; N5 is a schema/coordinator clarification.

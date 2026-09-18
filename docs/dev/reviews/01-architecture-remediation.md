# Architecture Review Remediation

- **Date:** 2026-09-18
- **Responds to:** `01-architecture-review.md`
- **Status:** planning changes complete; focused re-review pending

| Finding | Remediation |
|---|---|
| B1 canonical memory lifecycle | ADR-0011 defines Observation, CandidateMemory, Memory, Fact, ReviewEvent, transitions, idempotency, contradictions, forget/purge, and provider projection. S01, M1.1, Foundation, and dependency graph now freeze and implement it before builtin memory. |
| H1 L0–L4 conflict | ADR-0005, graph, and roadmap preserve PRD L0–L4 and require layer markers. |
| H2 source authority | ADR-0006 adds versioned SourceConfig/AuthorityPolicy and deterministic conflict/review semantics; S01/S05A and Foundation include it. |
| H3 application/inference boundary | ADR-0012 and graph add application services, versioned in-process SDK, confirmation ownership, public errors, and proposal-only InferenceProvider; REST remains post-MVP/S21. |
| H4 temporal semantics | ADR-0001 defines valid versus immutable system time, forward-only authoritative supersession, correction/world-change/retraction, conflicts, and as-known-at fixtures. |
| M1 S05 order | Graph/SPIKES/Phase 0 split Gate 0 S05A common-contract proof from per-provider S05B admission. |
| M2 onboarding | ROADMAP M1.4 and `plans/02-onboarding-advisor.md` own basic Plugin Advisor and the 15-step acceptance journey. |
| M3 budgets | ADR-0005 defines conservative UTF-8 response units, overhead, deterministic truncation/ties, and optional stricter tokenizer. |
| M4 host scope | ROADMAP/COMPATIBILITY make Claude Code/Codex first-class; Cursor/Claude Desktop are M1 compatibility notes only. |
| M5 relay staleness | RESEARCH_NOTES/STATE/HANDOFF updated; `tools/check_relay.py` now verifies ADR parity, links, state markers, review state, and instruction size. |
| L1 license gate | Moved public brand/license to M1.5 release gate; local engineering uses S00 namespace. |
| L2 purge precedence | ADR-0010 explicitly makes authorized privacy purge an exception to history preservation. |

No item is closed until independent focused re-review agrees that the contracts are sufficient.

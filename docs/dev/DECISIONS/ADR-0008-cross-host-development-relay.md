# ADR-0008: Put cross-host relay state in the repository

- **Status:** Accepted (2026-09-19, Gate 0 exit review 15)
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §36–§40, §51
- **Research refs:** `docs/research/upstream/claude-code-instructions.md`, `docs/research/upstream/codex-instructions.md`
- **Needs maintainer confirmation:** no

## Context

Claude Code and Codex sessions end, compact context, and do not share hidden state. The repository
must carry enough current truth for either host to resume safely.

## Decision drivers

- Restartability without prior chat logs
- Concise always-loaded instructions
- Verified checkpoints and explicit unresolved work

## Options considered

### A — Depend on conversation summaries

**+** No files to maintain. **−** Not portable, reviewable, or reliable.

### B — Thin instruction files plus structured state, ADRs, tests, and commits

**+** Durable and host-neutral. **−** Requires disciplined updates.

## Decision

Choose **B**. Root `AGENTS.md` is the concise cross-host contract. Root `CLAUDE.md` imports it and
contains Claude-only details. `docs/dev/STATE.md` is current truth; `HANDOFF.md` is a short-lived
operational note; ADRs hold architectural rationale; `KNOWN_ISSUES.md` records reproducible debt;
tests and commits are executable checkpoints.

Every substantial task starts by reading those files, checking Git status, and running a relevant
baseline. It ends by validating changes and updating state/handoff. Skills hold infrequent workflows
instead of expanding root instructions.

Product runtime context uses the same principle: host-specific L0 injection reads a pre-rendered,
bounded file. Claude Code uses a command hook because MCP tools are unavailable at SessionStart;
Codex receives equivalent guidance through adapter/instruction mechanisms proven by a spike.
The L0 file is a restrictive-permission, atomic, allowlisted projection with maximum size and policy
epoch. Any stale/invalid card fails closed; policy/fact changes invalidate it; purge/uninstall removes
it. It never contains source excerpts, secrets, raw interactions, or disabled modules. S12 is a ship
gate for each host adapter.

## Consequences

- **Positive:** Quota exhaustion or host switching does not erase project context.
- **Negative / risks:** Stale state can mislead; CI should check links/status where practical.
- **Follow-ups:** Add workflow skills only when their contracts stabilize.

## Verification

Fresh-session relay drill in both hosts; instruction-size checks; stale handoff detector; required
validation recorded in `STATE.md`; independent plan/code reviews stored under `docs/dev/reviews/`.

## Amendments

### 2026-09-19 — Gate 0 acceptance

Accepted. Supported by relay drills 05 and 11 and `tools/check_relay.py`. The Codex L0-guidance mechanism remains an S12 ship gate.

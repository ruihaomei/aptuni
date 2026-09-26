# Plan 20 — Beta Agent Activation UX TDD

## Goal

Ship one host-independent activation contract with exactly three user modes — Profile, Memory and
Full — while keeping ordinary Claude Code and Codex tasks Aptuni-OFF by default.

## Ownership and boundary

- `src/aptuni/application/activation.py` owns canonical activation intents and their mapping to
  existing bounded Context services. It knows no `@`, slash-command or skill syntax.
- `src/aptuni/mcp/server.py` owns one MCP-process-local session activation. Task activation is a
  single request and writes no activation state. Only Full may be session-scoped.
- `src/aptuni/adapters/manager.py` renders host-native, Aptuni-owned Claude Code and Codex skills.
  It removes the old automatic Claude SessionStart identity injection.
- Canonical Vault, retrieval, module policy, grants, provenance and budget contracts are unchanged.

## Failing-first matrix

1. An activation-required host starts OFF; direct identity/context reads fail content-free.
2. A task-scoped Profile request returns relevant exposed Facts only and leaves the next ordinary
   request OFF.
3. A task-scoped Memory request returns relevant exposed Memories only and leaves no session state.
4. Task Full may return relevant permitted Fact + Memory + Evidence, within the existing budget.
5. Session scope rejects Profile/Memory, accepts only explicit Full, is inspectable and disableable,
   and a new server process starts OFF.
6. Revoked/narrowed host grants and live module exposure changes continue to fail or filter through
   the existing service boundary.
7. Claude's generated bundle contains user-invocable plugin skills and no SessionStart personal
   context hook. Codex's bundle contains equivalent repository skills. Both map to the same three
   canonical intent values.

## Exit evidence

Focused activation/MCP/adapter tests, Ruff, strict mypy, full repository gate, real clean-bundle
host probes, independent privacy/contract review, ADR/STATE/HANDOFF update and local checkpoint.

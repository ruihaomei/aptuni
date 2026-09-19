# Milestone 1 Slice 5 — Bounded MCP STDIO

**Status:** Complete (`d4cc1fb` implementation checkpoint; relay checkpoint follows)
**Decision basis:** ADR-0005, ADR-0007, ADR-0013, S04, and Slice 4's bounded Context API.

## User-visible capability

- `aptuni-mcp` runs a local STDIO MCP server with content-free health plus bounded identity/context
  tools.
- Personal tools are admitted only by an application-layer principal/scope/module/egress contract.
  The production entry point defaults to remote/unknown with no grant, so it fails closed until an
  installed adapter supplies admitted access.

## TDD acceptance map

1. Tool schemas are task-oriented, read-only, bounded, and contain no approval, token, nonce, raw
   Vault path, or direct database/file handles.
2. Principal is process-bound and absent from every tool input. Unknown/missing scopes deny with a
   stable content-free error.
3. Remote/unknown hosts need exact per-module `host_model_egress`; `proven_local` can only arrive via
   a core-created access object, never a tool argument or environment label.
4. Context requires explicit modules for host calls; Evidence additionally requires
   `evidence.read`. Final policy/epoch race checks remain in the application service.
5. STDIO negotiation, EOF shutdown, malformed requests, budgets, and default-deny behavior pass
   against the real SDK. No resources or prompts are required.
6. The server process denies Internet/TCP sockets while allowing only CPython's internal AF_UNIX
   self-pipe creation.

## Explicit exclusions

No write/observe/review/approve tools, Streamable HTTP, host configuration mutation, or implicit
egress grant. Claude/Codex configuration and persisted informed consent belong to the next adapter
slice.

## Exit evidence

- 172 tests plus 47 subtests pass; Ruff and mypy strict are clean.
- Real SDK STDIO negotiation, health, default-deny personal read, EOF shutdown, and network canary
  pass from a clean wheel install.
- SDK 2.2.0 and its production closure are locked; runtime licenses are recorded in
  `THIRD_PARTY_NOTICES.md`.
- Production startup has no content grant. Persisted informed grants and host configuration belong
  to Slice 6; no environment or tool input can elevate a host to `proven_local`.

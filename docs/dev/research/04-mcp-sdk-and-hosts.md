# Upstream Research: MCP specification, Python SDK and host capabilities

> Researched 2026-09-18 · PRD refs: §18–§20, §31, §43, §48, §51

## Version snapshot

- Current MCP specification inspected: [`2026-07-28`](https://modelcontextprotocol.io/specification/2026-07-28).
- Official Python SDK latest release: [`v2.2.0`](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0),
  published 2026-09-07.
- Python SDK `main` inspected at
  [`6affe5c0d3588fd1705713b3703dc68015cfe3eb`](https://github.com/modelcontextprotocol/python-sdk/commit/6affe5c0d3588fd1705713b3703dc68015cfe3eb),
  2026-09-16.
- MCP specification repository `main` inspected at
  [`f56f204f6290f6531b14d5734eb3e0a10f0eb201`](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/f56f204f6290f6531b14d5734eb3e0a10f0eb201),
  2026-09-16.

These are time-sensitive facts. Lockfiles and adapter conformance results, not prose, must identify
the versions a release was tested against.

## Protocol findings

### Current core shape

The 2026-07-28 specification uses JSON-RPC 2.0 with stateless, self-contained requests and
per-request capability negotiation. Servers may offer:

- **tools** — functions the model can execute;
- **resources** — context/data for users or models;
- **prompts** — user-facing message/workflow templates.

Clients may offer **elicitation** for requesting additional information from users. Tasks, Skills
over MCP and MCP Apps are optional negotiated extensions, not baseline requirements.

The specification's security principles require explicit consent and control over data access and
tool invocation. Tool descriptions/annotations from a server are untrusted unless the server itself
is trusted.

Source: [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28).

### Important change from 2025-era MCP

The official Python SDK v2 documentation distinguishes:

- handshake-era sessions through `2025-11-25`, which can carry server-initiated requests such as
  sampling and push-style elicitation;
- the 2026-07-28 era, which uses `server/discover` and has no server-to-client push request channel.

The SDK's default `Client` negotiates modern mode and falls back for older servers. Its server can
serve the modern revision and earlier clients. If an application explicitly needs sampling or
push-style callbacks, the SDK documentation says it must use legacy mode; that is evidence that
sampling is not a portable modern-host baseline.

Source: [Python SDK protocol-version guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/protocol-versions.md).

**Implication:** this product must not require host-side sampling. Extraction/inference belongs
behind the PRD's `InferenceProvider` or is performed by the current Agent and submitted through a
normal tool call.

## Python SDK findings

The official `mcp` v2 line:

- requires Python 3.10+;
- provides server and client APIs;
- supports STDIO and Streamable HTTP, while retaining compatibility behavior for older revisions;
- renamed the v1 high-level `FastMCP` server to `MCPServer` in v2;
- exposes tools, resources and prompts;
- supports in-process connections useful for deterministic tests;
- ships OpenTelemetry tracing enabled by default according to the v2 release notes.

Sources:

- [Official Python SDK repository](https://github.com/modelcontextprotocol/python-sdk)
- [Official Python SDK releases](https://github.com/modelcontextprotocol/python-sdk/releases)

**Risk:** OpenTelemetry/default telemetry behavior needs a privacy spike and explicit configuration.
Local-first must include network-observability defaults, not only where Profile data is stored.

### Dependency recommendation

For a spike, use `mcp>=2.2,<3` and lock the exact resolved version. Do not encode v1 examples or
`FastMCP` names in the public architecture. Before the first release, run the official SDK's
conformance path and re-check the latest compatible 2.x patch. A major upgrade requires an ADR and
adapter compatibility run.

## Host capability matrix (documentation-level, not yet conformance-tested)

| Host/surface | Tools | Resources | Prompts | Elicitation / sampling | Notes |
|---|---|---|---|---|---|
| Codex CLI/Desktop/IDE | yes | yes (list/templates/read are implemented) | not established as a user-facing dependency | not established | STDIO + Streamable HTTP documented; shared host config. See research 06. |
| Claude Code | yes | yes, including `@server:uri` and list/read tools | yes, exposed as MCP slash prompts | elicitation documented; do not depend on sampling | Newer v2 runtime supports the 2026-07-28 revision; tool search lazily loads definitions. |
| Cursor | yes | not listed in current capability table | yes | elicitation yes; roots yes | Current docs list tools/prompts/roots/elicitation but omit resources; verify by live fixture. |
| Claude / Claude Desktop remote connectors | yes | yes | yes | resource subscriptions and sampling are documented as unsupported | Local Desktop/DXT behavior must be tested separately from remote connectors. |

Sources:

- [OpenAI Docs — MCP for Codex](https://developers.openai.com/docs/extend/mcp)
- [Claude Code MCP reference](https://code.claude.com/docs/en/mcp)
- [Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol)
- [Anthropic support — remote MCP connectors](https://support.anthropic.com/en/articles/11503834-building-custom-integrations-via-remote-mcp-servers)

The matrix records what documentation establishes, including omissions; it is not proof that an
unlisted feature is impossible. Product releases need executable conformance tests by host/version.

## What this means for Progressive Disclosure

### Portable baseline: tools

Implement L0–L4 retrieval through small task-oriented tools:

```text
get_identity_card()          -> tiny L0 card
search_context(query, ...)   -> compact ranked L1/L2 results under a budget
get_fact(id)                 -> L3 fact/memory
get_evidence(fact_id, ...)   -> L4 provenance, paginated/budgeted
```

Mutation tools (`observe`, `remember`, `forget`, source sync, permission changes) must be separated
from reads and carry stronger validation/authorization semantics.

### Enhancement: resources

Expose canonical/readable artifacts as resources for hosts that surface them well:

```text
profile://identity-card
profile://module/{name}
profile://fact/{id}
profile://fact/{id}/evidence
audit://pending-reviews
```

Resources should not be the only way to perform a required task. Cursor's documented matrix alone
is enough to reject a resource-only core contract.

### Optional UX: prompts

Prompts can make setup, audit and teaching workflows easier in hosts that expose them, but equivalent
CLI/skill/tool flows must exist. Prompts are UX adapters, not domain APIs.

### Not baseline: sampling and elicitation

- Sampling is protocol-era/host-dependent and absent from the modern core summary.
- Elicitation may improve an interactive setup, but non-interactive hosts and automation still need
  deterministic errors or returned questions.

## Transport and deployment

### MVP

Use **STDIO** for the local, zero-extra-service path. The host starts the server; the vault and
SQLite projection remain local; setup can install a command and write host-specific configuration.

### Architecture seam

Keep the server application independent of transport so a later **Streamable HTTP** deployment can
reuse domain services. Do not build an HTTP service, OAuth flow or cloud control plane for MVP unless
a concrete dogfooding requirement proves the value.

SSE is legacy compatibility, not the target for new design.

## Tool design constraints

- Every result is budgeted/paginated; never return the full Profile by default.
- IDs and provenance are stable; summaries are projections and may be regenerated.
- Read and write tools are distinguishable by name and metadata.
- Sensitive-module permission checks run inside the core even if the host also has approvals.
- Descriptions are concise because hosts may truncate or lazy-load them.
- Structured outputs use versioned schemas; human text is an accompaniment, not the contract.
- No tool accepts arbitrary filesystem paths after setup; sources are addressed by approved IDs.
- Do not place secrets or raw private content in errors/logs/traces.

## ADR implications

1. Adopt MCP Python SDK v2 behind an internal adapter; lock exact versions and test compatibility.
2. Define **tools** as the minimum portable Agent contract; resources and prompts are optional host
   enhancements.
3. Do not depend on MCP sampling, elicitation, tasks, skills or Apps for core correctness.
4. Choose STDIO for Starter Lite/MVP; retain a transport boundary for future Streamable HTTP.
5. Treat host capability support as versioned test data, not an architectural assumption.
6. Add an explicit telemetry/observability privacy decision before using SDK defaults in production.

## PoC spikes

- **M1 — SDK skeleton:** pin SDK v2, expose one typed tool/resource/prompt over STDIO, test in process
  and over a real subprocess; record wire revision negotiated by each host.
- **M2 — host matrix:** connect the same fixture server to pinned Codex, Claude Code, Cursor and
  Claude Desktop versions; verify tools, resource/list/read/templates, prompts, structured output,
  pagination, errors and Unicode.
- **M3 — telemetry/privacy:** run the SDK with no network credentials in a monitored environment;
  document emitted spans/network attempts and implement a local-first-safe default.
- **M4 — budget enforcement:** generate oversized L0/search/evidence results and prove truncation or
  pagination occurs inside the server before host-specific limits.
- **M5 — compatibility:** exercise at least one 2025-era client against the v2 server, or explicitly
  define the minimum supported host versions if backward compatibility costs outweigh value.

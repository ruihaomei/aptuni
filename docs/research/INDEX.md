# Research memory

Development agents' shared research memory: repo-native, human-readable, thin. Plain Markdown, no
database. Read the relevant entry before researching again. Add to it when you learn something a
later Claude Code or Codex session would otherwise have to rediscover.

This is *not* Aptuni's user-facing Memory Provider. It is project knowledge for the people and
agents building Aptuni.

## Upstream projects (`upstream/`)

| Topic | Note | One-line takeaway |
|---|---|---|
| Mem0 | [upstream/mem0.md](upstream/mem0.md) | Optional M2 projection. A no-key path needs local inference; disable telemetry; do not inherit raw-message retention. |
| LlamaIndex | [upstream/llamaindex.md](upstream/llamaindex.md) | Borrow core/integration separation and conformance tests, not its package sprawl. |
| Graphiti | [upstream/graphiti.md](upstream/graphiti.md) | Optional M3 temporal-graph projection. Its data model is never canonical. |
| MCP SDK and hosts | [upstream/mcp-sdk-and-hosts.md](upstream/mcp-sdk-and-hosts.md) | Task-oriented tools over STDIO are the portable baseline. |
| Claude Code | [upstream/claude-code-instructions.md](upstream/claude-code-instructions.md) | `CLAUDE.md` imports `AGENTS.md`; the SessionStart L0 card uses a command hook over a pre-rendered file. |
| Codex | [upstream/codex-instructions.md](upstream/codex-instructions.md) | `AGENTS.md`, skills, repo state and git checkpoints form the relay. |
| Retrieval and packaging | [upstream/local-retrieval-and-packaging.md](upstream/local-retrieval-and-packaging.md) | One `src/` distribution, entry points at the external seam, SQLite as a projection. |
| Source identity | [upstream/source-identities-and-deltas.md](upstream/source-identities-and-deltas.md) | Immutable snapshots plus candidate deltas; OPML IDs are unproven. |
| Claude-Mem | not yet researched | Referenced for progressive disclosure (PRD §18). Research it when the Context API slice needs it. |
| Khoj, memU | not yet researched | PRD §32 secondary references (Obsidian UX, wiki-first memory). |

## Decisions and rejected approaches (`decisions/`)

- [decisions/rejected-approaches.md](decisions/rejected-approaches.md) — options that were
  considered and rejected, with the evidence. Settled decisions themselves live in
  `docs/dev/DECISIONS/` (ADRs).

## Findings and pitfalls (`findings/`)

- [findings/pitfalls.md](findings/pitfalls.md) — traps already hit while building. Read it before
  running host probes, shell loops or history operations.
- Spike evidence: `docs/dev/spikes/` (S01–S05A results and their reviews).

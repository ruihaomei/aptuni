# Research Synthesis

> The research memory now lives in [`docs/research/INDEX.md`](../research/INDEX.md). This page keeps
> the original synthesis table for reference.

This is the durable synthesis of the eight upstream studies required by PRD §51. Detailed evidence,
links, inspected commits/releases, caveats, and proposed spikes remain in `docs/dev/research/`.

## Snapshot

| Area | Planning conclusion | Durable artifact |
|---|---|---|
| Mem0 | Optional Milestone 2 projection. A no-extra-key path requires local inference; disable telemetry and do not inherit raw-message retention. | `docs/research/upstream/mem0.md` |
| LlamaIndex | Borrow contract separation and affected-dependant testing, not its hundreds-of-packages topology. Use explicit entry-point discovery and conformance tests. | `docs/research/upstream/llamaindex.md` |
| Graphiti | Optional Milestone 3 temporal graph projection. Its mutable node attributes and incomplete locator provenance cannot be canonical. | `docs/research/upstream/graphiti.md` |
| MCP | Portable baseline is task-oriented tools. Resources are an enhancement; prompts are host UX; sampling/elicitation are not core dependencies. Start with STDIO. | `docs/research/upstream/mcp-sdk-and-hosts.md` |
| Claude Code | Root `CLAUDE.md` imports `AGENTS.md`. Session-start L0 injection must use a command hook over a pre-rendered card because MCP is not yet connected. | `docs/research/upstream/claude-code-instructions.md` |
| Codex | `AGENTS.md`, skills, repository state, tests, and Git checkpoints form the relay. Sessions are not durable project state. | `docs/research/upstream/codex-instructions.md` |
| Retrieval/packaging | One `src/` Python distribution for MVP, standard entry points at the external seam, SQLite as a rebuildable projection. Built-in FTS needs a Chinese/English spike. | `docs/research/upstream/local-retrieval-and-packaging.md` |
| Source identity/deltas | Preserve immutable source snapshots and explicit candidate deltas. Never assume OPML outline IDs are stable; reconcile conservatively and surface ambiguity. | `docs/research/upstream/source-identities-and-deltas.md` |

## Cross-cutting conclusions

1. **The open-format vault is the only authority.** SQLite, Mem0, Graphiti, embeddings, and caches
   must be deletable and reconstructable without losing user-owned truth.
2. **Loss is named, not hidden.** Every projection declares unsupported canonical fields and keeps
   a projection ledger when one-to-one reconstruction is impossible.
3. **MVP stays small.** Builtin memory, SQLite retrieval, Folder/MarginNote/GitHub Standard sources,
   MCP tools, CLI, and two host adapters come first. Mem0, Graphiti, LlamaIndex, hybrid retrieval,
   and a plugin registry remain behind stable seams.
4. **Host-assisted inference is separate from storage.** A host agent may submit structured
   observations, but storage contracts never require a host, a cloud key, or a specific model.
5. **Raw conversations are off by default.** Structured observations can persist; raw interaction
   content is discarded unless a scoped, explicit retention policy permits it.
6. **Activation is explicit.** Installed plugins are discovered but not automatically trusted or
   enabled. Capability, privacy, dependency, and version metadata is machine-readable.
7. **Portable interaction uses tools.** Host-specific resources, prompts, hooks, and skills improve
   experience but cannot be required for core correctness.
8. **The repository carries the relay.** `STATE.md`, `HANDOFF.md`, ADRs, tests, and commits must let a
   fresh Claude Code or Codex session resume without the prior chat.

## Research-bounded uncertainties

- MarginNote 4 node identity and re-export behavior need fixtures from real exports.
- Chinese/English FTS quality needs a representative query corpus and scored comparison.
- Current MCP host behavior needs executable conformance probes, not documentation alone.
- Mem0 local/offline operation, retention, telemetry, and export must be verified in an isolated
  environment before its adapter is production-ready.
- Graphiti mapping, invalidation, out-of-order corrections, and provenance require a disposable
  database spike before accepting the provider.
- S00 selected temporary development namespace `personal_context_core`; public brand/package
  migration and repository license require maintainer confirmation before release/contributions.

## Source discipline

- Upstream observations are time-stamped snapshots, not timeless claims.
- Prefer dependency or adapter use over source copying.
- Any copied implementation requires license and copyright review plus
  `THIRD_PARTY_NOTICES.md`.
- Re-run targeted upstream research when an adapter's pinned version changes materially.

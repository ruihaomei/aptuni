# MVP Dependency Graph

This graph turns PRD §48 into implementation order. Arrows mean “must be stable enough before.”
Dashed nodes are seams or later milestones, not MVP implementation work.

```mermaid
flowchart TD
    D0[Temporary namespace<br/>S00 complete] --> DRAFT[Draft canonical + application + provider contracts]
    R[Research + proposed ADRs] --> DRAFT
    DRAFT --> P0[S01–S04<br/>schema/Vault/concurrency · plugins · FTS · MCP]
    DRAFT --> S05A[S05A common source-identity contract<br/>representative Folder · MarginNote · GitHub fixtures]
    P0 --> S[Freeze v1 schemas<br/>Fact · Observation · CandidateMemory · Memory · Evidence<br/>Snapshot · CandidateDelta · SourceConfig · security records]
    S05A --> S
    S --> V[Vault repository<br/>atomic writes · migrations · audit]
    S --> C[Provider contracts<br/>manifests · capabilities · errors]
    V --> POL[Policy service<br/>ingest · expose · retention · deletion]
    C --> POL
    V --> APP[Application services + versioned in-process SDK<br/>transactions · auth/confirmation · errors]
    C --> APP
    POL --> APP
    INF[InferenceProvider / structured host proposal port] --> APP
    V --> ING
    C --> ING
    POL --> ING
    ING[Ingestion coordinator] --> APP
    ING --> F05[S05B Folder admission] --> FOLDER[Folder Source]
    ING --> M05[S05B MarginNote admission] --> MN[MarginNote Source]
    ING --> G05[S05B GitHub admission] --> GH[GitHub Standard Source]
    V --> MEM
    C --> MEM
    POL --> MEM
    MEM[Canonical interaction-memory lifecycle service] --> APP
    MEM --> MPORT[Active MemoryProvider / MemoryView port]
    BM[Builtin Memory projection] --> MPORT
    V --> RIDX[SQLite retrieval projection]
    POL --> RIDX
    RIDX --> RPORT[Active RetrieverProvider port]
    RPORT --> CTX[Context service<br/>L0–L4 · conservative budgets]
    V --> CTX
    POL --> CTX
    MPORT --> CTX
    CTX --> APP
    APP --> MCP[MCP STDIO adapter]
    CONFINE[Host confinement profile + doctor status<br/>ADR-0013] --> APP
    APP --> CLI[CLI adapter + confirmation subcommands]
    MCP --> CLAUDE[Claude Code adapter]
    MCP --> CODEX[Codex adapter]
    CLI --> ADVISOR[Guided setup + Plugin Advisor<br/>Starter Lite + Researcher recipes]
    CLAUDE --> E2E[Dogfood + bilingual E2E + evals]
    CODEX --> E2E
    ADVISOR --> E2E

    C -. stable seam .-> EP[External entry-point fixture]
    MEM0[Mem0 provider] -. Milestone 2 .-> MPORT
    HYBRID[Hybrid retrieval] -. Milestone 2 .-> RPORT
    ING -. Milestone 2 .-> OBS[Obsidian source/interface]
    GRAPH[Graphiti projection] -. Milestone 3 .-> MPORT
    LLAMA[LlamaIndex retrieval] -. Milestone 3 .-> RPORT
```

## Critical path

1. Use the S00 temporary namespace; confirm public name/license before release.
2. Complete S01–S04 and common source-contract S05A; accept/revise ADRs.
3. Freeze canonical schema v1 (including interaction memory) and provider/application contracts v1.
4. Implement Vault + policy before any source, memory, or retrieval provider.
5. Implement application services, canonical memory lifecycle, ingestion, and builtin projections.
6. Expose bounded context through CLI/MCP, then host adapters.
7. Dogfood real sources; pass portability, privacy, temporal, and bilingual evaluation gates.

## Classification

| Class | Included work |
|---|---|
| Must-have MVP | schemas, Vault, policy, application SDK, canonical memory lifecycle, three source providers, builtin memory, SQLite retrieval, context service, CLI/MCP, guided setup/Plugin Advisor, two host adapters, bilingual docs/tests |
| Dogfooding feature | maintainer source fixtures, Starter Lite/Researcher recipes, L0 card, sync/review/status UX |
| Architecture seam | provider protocols, manifests, entry-point fixture, transport boundary, projection ledger |
| Future extension | Mem0, Graphiti, LlamaIndex, hybrid retrieval, Obsidian, HTTP service, registry |
| Nice-to-have | visual catalog, rich dashboard, native tokenizer extension, broad auto-discovery |

## Rules that prevent false parallelism

- Source adapters may proceed in parallel only after Snapshot/CandidateDelta contracts stabilize.
- CLI and MCP may proceed in parallel only after application-service APIs and error semantics stabilize.
- Host adapters may proceed in parallel after MCP schemas are snapshot-tested.
- Optional backend implementation cannot begin merely because its interface exists; its milestone and
  spikes must be approved.

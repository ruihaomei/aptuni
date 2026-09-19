# Upstream Research: Mem0 repository, memory engine, and agent UX

> Researched 2026-09-18 · PRD refs: §13, §14, §31, §32, §41, §46, §51 · Researcher: subagent `research_mem0`

## Snapshot and method

- Official repository: [`mem0ai/mem0`](https://github.com/mem0ai/mem0).
- Inspected default branch commit: [`84bf468176f0c5e82493bb95aec5484eb2d92bc1`](https://github.com/mem0ai/mem0/commit/84bf468176f0c5e82493bb95aec5484eb2d92bc1), committed 2026-09-18 01:24:04 UTC. Repository tree and source links below are pinned to this SHA.
- Inspected released Python SDK tag: [`v2.0.20`](https://github.com/mem0ai/mem0/releases/tag/v2.0.20), commit [`9a7924b`](https://github.com/mem0ai/mem0/commit/9a7924befd7026e41e445ba809370009e5e985a6), published 2026-09-02. The same commit carries TypeScript tag `ts-v3.1.8`.
- GitHub API snapshot at research time: 65,547 stars; license metadata `Apache-2.0`.
- Method: `gh api` against the official repository, reading the recursive tree and source files without cloning. Official Mem0 documentation is stored in the same repository under `docs/`, so pinned source links are preferred over mutable rendered-doc URLs.

## Executive finding

Mem0 is a strong **execution and adapter benchmark**, but it should remain a replaceable derived-memory backend for this project, exactly as the PRD says.

The most useful patterns are its three-path onboarding (library / self-hosted / cloud), one-command agent signup, provider factories, sync/async CRUD surface, explicit user/agent/run scopes, focused agent MCP tool, lifecycle hooks, local evidence queue, and extensive integration/skill packaging. The most important reasons not to copy its product architecture are equally concrete: memory text lives primarily inside a vector-store-specific payload, history is a separate SQLite sidecar, there is no lossless cross-backend export contract, telemetry is enabled by default, the turnkey coding-agent plugins use the hosted Platform, and both the OSS engine and the agent plugin retain raw conversational evidence locally in ways that conflict with this PRD's raw-conversation-retention-off default.

## Verified facts

Everything in this section is directly supported by the pinned official repository. Interpretations and recommendations are separated later.

### 1. Repository and package structure

The repository is a multi-surface monorepo. Its top-level tree contains:

- `mem0/`: Python package. [`mem0/__init__.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/__init__.py) exports local `Memory` / `AsyncMemory` and hosted `MemoryClient` / `AsyncMemoryClient` from one package.
- `mem0-ts/`: TypeScript SDK. Its [`package.json`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0-ts/package.json) exposes the managed client at `mem0ai` and the OSS engine at `mem0ai/oss`; most non-default providers are optional peer dependencies.
- `server/`: FastAPI REST API, Docker Compose stack, Postgres/pgvector, auth, request log, Alembic migrations, and a web dashboard. The REST routes include configure, add, list, get, search, update, history, delete, delete-all, and reset. See [`server/main.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/server/main.py) and [`server/docker-compose.yaml`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/server/docker-compose.yaml).
- `cli/python/` and `cli/node/`: two implementations of the Mem0 CLI, with parity tests and their own release workflows.
- `integrations/`: shared `agent-plugin-core` plus Claude Code, Codex, Cursor, OpenCode, OpenClaw, Pi, n8n, Vercel AI SDK and other adapters. See the pinned [`integrations/` tree](https://github.com/mem0ai/mem0/tree/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations).
- `skills/`: reference and pipeline skills (`mem0`, `mem0-cli`, `mem0-integrate`, `mem0-test-integration`, `mem0-oss-to-platform`, `mem0-vercel-ai-sdk`). See [`skills/README.md`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/skills/README.md).
- `docs/`, `examples/`, `tests/`, `.github/`, plus root and subtree `AGENTS.md` / `CLAUDE.md` files and multiple agent-plugin marketplace manifests. The full pinned root is [here](https://github.com/mem0ai/mem0/tree/84bf468176f0c5e82493bb95aec5484eb2d92bc1).

The Python package at the inspected commit is version `2.0.20`, requires Python `>=3.10,<4.0`, and has hard dependencies on Qdrant client, OpenAI client, PostHog, SQLAlchemy, Pydantic and HTTPX. Optional groups add NLP, vector stores, LLM SDKs and extras. Source: [`pyproject.toml`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/pyproject.toml).

### 2. Quickstart and agent-oriented installation UX

The root README gives three explicitly differentiated deployment paths:

| Path | Official first step | Default dependency shape |
|---|---|---|
| Library | `pip install mem0ai` / `npm install mem0ai` | In-process engine; Python defaults to OpenAI LLM + OpenAI embeddings + embedded Qdrant + SQLite history |
| Self-hosted server | `cd server && make bootstrap` | Docker stack, dashboard, auth/API keys, Postgres/pgvector, external LLM/embedder provider |
| Cloud Platform | Create account/API key | Managed memory service and advanced features |

Sources: pinned [`README.md`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/README.md), [`Open Source Overview`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/open-source/overview.mdx), and [`Self-Hosted Setup`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/open-source/setup.mdx).

The default Python quickstart is short but **does require an OpenAI API key**. `Memory()` defaults to OpenAI `gpt-5-mini`, OpenAI `text-embedding-3-small`, on-disk Qdrant at `/tmp/qdrant`, and SQLite history at `~/.mem0/history.db`. Source: [`docs/open-source/python-quickstart.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/open-source/python-quickstart.mdx).

Mem0's hosted CLI has a notably agent-friendly bootstrap:

```bash
npm install -g @mem0/cli       # or pip install mem0-cli
mem0 init --agent --agent-caller codex
mem0 add "Prefers explicit error types"
mem0 search "preferred error style"
```

`mem0 init --agent` creates a hosted account and API key without email, saves the key to `~/.mem0/config.json` with mode `0600`, chooses a default `user_id`, and allows a human to claim the same account later without changing the key or losing memories. Unclaimed agent accounts use the normal free-tier quota and agent-mode signups are limited to five per IP per day. Sources: [`agent-signup.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/platform/agent-signup.mdx) and the Python CLI [`init_cmd.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/cli/python/src/mem0_cli/commands/init_cmd.py).

This is a low-friction **cloud credential minting flow**, not a local/no-key flow.

The current Claude Code and Codex packages are version `0.3.1` in their manifests. Their recommended installation is through Mem0's own plugin marketplace. The Codex docs also offer a direct hosted MCP connection. The full plugin adds capture/recall lifecycle hooks and six memory skills; direct MCP exposes nine hosted CRUD/entity tools but no lifecycle hooks. Sources: [Claude marketplace manifest](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/.claude-plugin/marketplace.json), [Codex marketplace manifest](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/.codex-plugin/marketplace.json), [`docs/integrations/claude-code.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/integrations/claude-code.mdx), and [`docs/integrations/codex.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/integrations/codex.mdx).

The plugin's MCP process is local stdio, but its search and flush implementations call hosted `/v3/memories/search/` and `/v3/memories/add/` endpoints and require `MEM0_API_KEY`. Sources: [plugin `.mcp.json`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations/codex-plugin/.mcp.json), [`memory_core.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations/agent-plugin-core/python/memory_core.py), and [`mcp_server.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations/agent-plugin-core/python/mcp_server.py).

### 3. Local and zero-additional-key feasibility

**Feasible for the OSS library, with qualifications.** Mem0 supports local Ollama for both the extraction LLM and embeddings. The official component docs describe each provider separately; combining both configs with the default embedded Qdrant and SQLite removes the need for an external model API key. Sources: [Ollama LLM doc](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/components/llms/models/ollama.mdx), [Ollama embedder doc](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/components/embedders/models/ollama.mdx), [`mem0/llms/ollama.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/llms/ollama.py), and [`mem0/embeddings/ollama.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/embeddings/ollama.py).

The qualifications are material:

1. The user must install and run Ollama and download an extraction model plus an embedding model; `mem0ai` does not bundle them. The Ollama Python client is also not a core dependency.
2. `Memory.__init__` always constructs an LLM, embedder, vector store, and SQLite history manager. Even if the caller uses `infer=False`, a valid LLM provider must still initialize. Sources: [`Memory.__init__`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L487-L552) and [`_add_to_vector_store`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L879-L1206).
3. The official combined quickstart still optimizes for OpenAI defaults; there is no current one-command, fully local, keyless quickstart equivalent to Agent Mode.
4. Anonymous PostHog telemetry is enabled by default. A strict local/offline installation must set `MEM0_TELEMETRY=false`; otherwise the OSS library can make outbound telemetry calls even while model and storage providers are local. Source: [`mem0/memory/telemetry.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/telemetry.py).
5. The official Claude/Codex automatic-memory plugins are hosted-Platform adapters; they are not a frontend for a local `Memory` instance.

A fully local illustrative configuration, inferred by combining two documented provider configs, is:

```python
from mem0 import Memory

m = Memory.from_config({
    "llm": {"provider": "ollama", "config": {"model": "llama3.1:8b"}},
    "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text"}},
    "vector_store": {"provider": "qdrant", "config": {"path": "/local/path/qdrant"}},
    "history_db_path": "/local/path/history.db",
})
```

This snippet is an integration inference, not copied verbatim from an official combined example; it must be validated by the PoC below.

### 4. Memory lifecycle and API

The Python OSS engine exposes synchronous and asynchronous variants of:

- `add`
- `get`
- `get_all`
- `search`
- `update`
- `delete`
- `delete_all`
- `history`
- `reset`

The hosted client adds batch update/delete, project operations, webhooks, feedback, and memory-export jobs. Sources: [`mem0/memory/main.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py) and [`mem0/client/main.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/client/main.py).

Scope semantics are explicit but asymmetric:

- `add()` accepts `user_id`, `agent_id`, and `run_id` as top-level parameters.
- `search()` and `get_all()` require a `filters` object containing at least one of those IDs and reject the corresponding top-level arguments.
- Current coding-agent integrations additionally use `app_id` at the hosted v3 API layer to scope personal and shared project lanes. Sources: [`Memory.add`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L760-L878), [`Memory.get_all`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L1255-L1378), [`Memory.search`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L1379-L1523), and agent-plugin [`memory_core.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations/agent-plugin-core/python/memory_core.py).

At the inspected commit, inferred `add()` uses a phased additive pipeline:

1. Load the latest 10 raw messages for the current session scope from SQLite.
2. Retrieve up to 10 existing memories from the vector store.
3. Make one LLM extraction call using the new messages, recent messages, and retrieved memories.
4. Batch-embed extracted facts.
5. Exact-deduplicate by MD5 text hash.
6. Insert new vector records and `ADD` history records.
7. Extract/link entities in a second vector collection.
8. Save recent raw messages and return new memories.

Automatic extraction is therefore **additive** at this commit: it does not automatically rewrite or delete prior memories. However, explicit `update()` and `delete()` APIs still exist and write `UPDATE` / `DELETE` history records. The `add()` docstring still says the LLM may add/update/delete, so source behavior and inline documentation are not fully aligned. Sources: [`_add_to_vector_store`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L879-L1206), [`update/delete/history`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L1815-L1959), and the README's [April 2026 algorithm note](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/README.md).

`infer=False` bypasses extraction and stores each non-system message verbatim as a memory, preserving its role and optional actor name. It still embeds and writes the text. Source: [`_add_to_vector_store`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L879-L921) and [`Direct Import`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/platform/features/direct-import.mdx).

Storage is split:

- Current memory text, identity scope, timestamps, hashes and arbitrary metadata are vector-store payloads.
- SQLite stores change history (`old_memory`, `new_memory`, event, timestamps, deletion flag, actor, role) and the last 10 raw messages per session scope.
- Expired memories are hidden by default rather than immediately deleted.

Sources: [`MemoryConfig`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/configs/base.py), [`SQLiteManager`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/storage.py), and [`Memory._create/_update/_delete_memory`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L1961-L2129).

The coding-agent plugin has a separate lifecycle. Hooks capture prompts, assistant results and selected tool outcomes into a local `evidence.sqlite3`; periodic/idle/end/compact hooks launch a detached worker, redact recognizable secrets, send message batches to hosted Mem0 for extraction, and automatically search on the next session's first sufficiently long prompt. The plugin exposes only one focused local MCP tool, `search_memories`, while writes happen through hooks. Sources: [`docs/integrations/claude-code.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/integrations/claude-code.mdx), [`memory_core.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations/agent-plugin-core/python/memory_core.py), and [`mcp_server.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations/agent-plugin-core/python/mcp_server.py).

### 5. Provider model and telemetry

The Python engine uses factories for LLM, embedder, vector store and reranker. The inspected mappings include:

- LLMs: OpenAI, Ollama, Anthropic, Gemini, Bedrock, Azure, LiteLLM, LM Studio, vLLM, LangChain and others.
- Embedders: OpenAI, Ollama, Hugging Face, FastEmbed, Gemini, Bedrock, LM Studio and others.
- Vector stores: Qdrant, Chroma, pgvector, Pinecone, MongoDB, Redis, FAISS, Elasticsearch, OpenSearch, Supabase, Weaviate and others.
- Rerankers: Cohere, sentence-transformers, ZeroEntropy, LLM and Hugging Face.

Source: [`mem0/utils/factory.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/utils/factory.py) and [`docs/open-source/configuration.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/open-source/configuration.mdx).

This is not a uniformly open plugin ABI. `LlmFactory` has a runtime `register_provider`; the other factories use in-repository static mappings, and vector-store config validation also has a static provider-to-config table. Adding many provider types therefore requires modifying Mem0 core. Sources: [`factory.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/utils/factory.py) and [`vector_stores/configs.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/vector_stores/configs.py).

OSS telemetry facts:

- Enabled by default through `MEM0_TELEMETRY=True`; users can disable it with the environment variable.
- Uses PostHog at `https://us.i.posthog.com`.
- Lifecycle events are unsampled; hot-path events default to a 10% sample rate.
- Common properties include client/package version, Python version, OS/release/architecture and configured provider class names. Operation telemetry includes function name, vector size/store, LLM, embedder and filter-key names; `user_id`, `agent_id` and `run_id` are MD5-hashed before being attached.
- Telemetry failure is designed to fail open and not break memory operations.

Sources: [`mem0/memory/telemetry.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/telemetry.py), [`mem0/memory/setup.py`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/setup.py), and [`process_telemetry_filters`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/utils.py#L235-L250).

### 6. Export and portability

There are three different mechanisms that should not be conflated:

1. **OSS enumeration:** `get_all(filters=..., top_k=...)` returns current memories from the configured vector store. It defaults to 20 and has no portable continuation-token/pagination contract in the OSS method. Source: [`Memory.get_all`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/main.py#L1255-L1378).
2. **Platform Memory Export:** `create_memory_export(schema, filters...)` submits an asynchronous job that asks the Platform to transform memories into a caller-defined JSON schema; `get_memory_export` returns the generated projection. This is a semantic/analytics export, not a documented raw backup. Sources: [`memory-export.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/platform/features/memory-export.mdx) and [`MemoryClient.create/get_memory_export`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/client/main.py#L624-L668).
3. **OSS-to-Platform migration:** the official one-command migration currently supports hosted Qdrant only; local Qdrant, pgvector and other stores are explicitly not supported by that script. Source: [`docs/migration/oss-to-platform.mdx`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/docs/migration/oss-to-platform.mdx).

No inspected interface exports a complete, backend-neutral package containing stable memory IDs, memory text, full metadata, every history event, evidence/provenance, embeddings or re-embedding instructions, tombstones, expiration state, and source links. Rehydrating with `infer=False` can preserve text and selected metadata but creates new storage-specific IDs/embeddings and does not recreate the original SQLite history.

### 7. Raw-data retention relevant to PRD §14

Two source-level facts conflict with this project's desired default of discarding raw conversation after structured extraction:

- The OSS engine saves the latest 10 raw messages per session scope in its history SQLite database. Source: [`SQLiteManager.save_messages`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0/memory/storage.py).
- The coding-agent plugin stores hook evidence, including prompt/assistant text, in the local `events.payload_json` table before extraction. In the inspected `memory_core.py`, successful flush marks rows through `flush_id` and status records; no deletion/TTL path for flushed event payloads was found. The absence of a path is a bounded source-inspection finding, not a guarantee that no external cleanup exists. Source: [`EvidenceStore` schema and flush code](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/integrations/agent-plugin-core/python/memory_core.py).

The plugin performs regex-based redaction before remote extraction, but redaction is not equivalent to user-controlled retention, complete DLP, or evidence minimization.

### 8. License

The repository and both SDK package manifests declare Apache License 2.0. The root contains the standard Apache 2.0 license text. Sources: [`LICENSE`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/LICENSE), [`pyproject.toml`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/pyproject.toml), and [`mem0-ts/package.json`](https://github.com/mem0ai/mem0/blob/84bf468176f0c5e82493bb95aec5484eb2d92bc1/mem0-ts/package.json).

Apache-2.0 permits reuse and modification subject to its notice/license conditions. This research recommends borrowing patterns and API ideas, not copying source. Any future copied or modified implementation must go through the PRD §41 provenance workflow and preserve the required notices.

## Source inconsistencies and caveats

These are verified documentation/source mismatches that should prevent us from treating a single Mem0 page as a stable contract:

1. The current `add()` source is additive-only for inferred extraction, but its docstring still says the LLM may add, update or delete.
2. The OSS-to-Platform migration guide says Platform `update()` is unavailable and recommends delete+add, while the inspected Python `MemoryClient` still implements `update()`. Treat the SDK source and live API schema as authoritative during integration.
3. The README's benchmark table explicitly says its scores represent the managed Platform and proprietary optimizations; they should not be used as OSS-engine acceptance thresholds.
4. Python and TypeScript major versions differ (`2.x` vs `3.x`), and their local-provider capabilities/default stores differ. Our provider conformance tests must not assume behavioral identity between SDK languages.

## Interpretation for this project

This section is analysis, not upstream fact.

### What to borrow

- **Three explicit deployment paths** with a one-minute comparison table. Our equivalent should distinguish built-in local, optional external memory provider, and optional managed service without hiding keys or infrastructure.
- **Agent-first bootstrap UX**, but adapt it to local-first ownership: a single `init` should detect the agent host, create local canonical storage, install the adapter, run a smoke test, and explain every file/credential created.
- **Small automatic recall + explicit search.** Mem0's coding plugin automatically recalls a handful of memories on the first prompt and exposes one focused read-only search tool. This closely matches the PRD's minimal L0 injection plus tool-search design.
- **Hook capture -> durable local queue -> detached extraction worker.** The local queue, retry state, idempotent packet IDs and fail-open hooks are useful reliability patterns.
- **Separate personal and shared project lanes** and explicit `user_id` / `agent_id` / `app_id` / `run_id` dimensions. We should map these concepts to our own stable subject/source/session identifiers rather than inherit Mem0's names as canonical schema.
- **Provider conformance and dependency isolation.** Lazy/optional provider imports and a common CRUD/search contract are worth adopting, while moving each integration behind our own plugin boundary.
- **Sync + async APIs**, direct import, scoped deletion, history, expiration, telemetry-off switch, and a visible status/doctor command.
- **Repository execution quality:** examples, skills, integration tests, marketplace manifests, subtree instructions, release workflows, contributor docs, and a test-first integration skill.

### What not to copy

- Do not make vector-store payloads or a provider's history DB canonical truth.
- Do not adopt Mem0 Platform IDs as stable user-owned IDs.
- Do not call schema-transformed cloud output a backup/export.
- Do not enable outbound telemetry by default in a privacy-first personal system.
- Do not retain raw conversations merely because the provider/plugin needs an extraction queue. The queue needs explicit TTL, deletion-on-success, pause/inspect controls, and per-source policy.
- Do not make the default coding-agent adapter dependent on Mem0 cloud or a newly minted API key.
- Do not expose every provider capability through the core. Keep a deliberately small provider contract and capability negotiation; provider-only functions belong behind namespaced extensions.
- Do not couple automatic memory formation to implicit LLM rewrite/delete decisions. Candidate deltas should be auditable and applied by our lifecycle policy.
- Do not present managed-platform benchmark scores as evidence that the OSS package or our adapter meets retrieval targets.

## ADR implications

### ADR candidate: Canonical truth remains provider-independent

Decision implication: Mem0 receives a materialized projection of approved memories and/or interaction observations; it never owns Profile, evidence, source manifests, stable IDs, or revision history. Every Mem0 record must carry our canonical object ID, schema version, source/evidence refs, and provider-sync generation in metadata.

### ADR candidate: `MemoryProvider` contract is narrower than Mem0's API

Minimum portable contract should be defined in our terms:

```text
upsert_projection(canonical_memory)
delete_projection(canonical_id, tombstone)
search(query, scope, filters, limit) -> ranked canonical IDs + provider score
get_projection(canonical_id)
health/capabilities
export_provider_state()        # diagnostic, not canonical backup
rebuild_from_canonical()
```

`history`, graph/entity links, reranking, async events and cloud exports should be optional capabilities. The core should not encode Mem0's top-level-add vs filter-search asymmetry.

### ADR candidate: Two Mem0 modes, both optional

1. **Mem0 OSS adapter:** local library/self-host, configurable providers, telemetry forced off unless the user opts in.
2. **Mem0 Platform adapter:** explicit network/credential consent and clear data-egress warning.

The adapter metadata should not claim `local_only_supported: true` unless the selected LLM, embedder, vector store, telemetry and every retry/notice path have passed an offline integration test.

### ADR candidate: Host-assisted extraction is separate from Mem0 storage

For users who want no extra model API key, let Claude/Codex (already authorized by the host) propose a `candidate_delta.yaml`. Once accepted, store canonical memory locally and optionally send normalized text to Mem0 with `infer=False`. A local embedder is still required for Mem0 search. This makes extraction provenance visible and avoids paying a second LLM provider, but it does not eliminate local model/dependency costs.

### ADR candidate: Raw interaction buffer policy

Use a dedicated encrypted/local interaction buffer with a short TTL and delete-on-success. The default must be raw retention off after extraction. Provider adapters may not silently persist full prompts/responses in their own SQLite files. Status and audit views must show buffered item count, oldest age, last flush, and last deletion.

### ADR candidate: Portable export is round-trippable

Define our export before implementing the Mem0 adapter. It should include canonical IDs, revisions, timestamps, statements, scope, confidence, status/tombstones, evidence links, source IDs, retention labels and provider sync metadata. A round-trip test must rebuild a fresh backend and compare canonical records. Embeddings are disposable and should normally be regenerated.

### ADR candidate: Telemetry is opt-in and schema-audited

Provider initialization should set `MEM0_TELEMETRY=false` by default. If users opt in, our wrapper should document the exact upstream events/properties and pin the reviewed SDK version; upgrades that change telemetry code require re-review.

## Minimal PoC spikes before production implementation

### M0-1 — Fully local offline smoke test (highest priority)

**Goal:** prove or falsify the plugin metadata claim `local_only_supported: true`.

- Install `mem0ai==2.0.20`, Ollama client/runtime and two local models in an isolated environment.
- Set `MEM0_TELEMETRY=false` and block outbound network after model download.
- Use Ollama LLM + Ollama embedder + embedded Qdrant + SQLite.
- Run add/search/get/update/history/delete/reset and restart persistence tests.
- Record install size, model download size, cold start, add latency, search latency, RAM, disk paths and every attempted outbound connection.
- Repeat one add with `infer=False` from a host-produced candidate delta.

**Pass condition:** no external API key, no outbound call, deterministic data paths, restart persistence, and a complete uninstall/data-removal inventory.

### M0-2 — Provider adapter contract spike

**Goal:** implement the smallest `MemoryProvider` wrapper without leaking Mem0 types.

- Map one canonical memory to Mem0 metadata with stable canonical ID.
- Exercise create/rebuild/search/delete with both OSS `Memory` and a fake provider.
- Verify provider scores never become canonical confidence.
- Detect API drift between Python `v2.0.20` and current main.

**Pass condition:** swapping the fake provider and Mem0 changes no canonical files, Context API response schema, or stable IDs.

### M0-3 — Lossless rebuild and export gap

**Goal:** demonstrate portability rather than assume it.

- Seed memories with metadata, expiration, updates and deletion.
- Export using only public OSS methods and separately inspect Qdrant + history SQLite.
- Rebuild a fresh Mem0 instance from our canonical export with `infer=False`.
- Compare text, metadata, scopes, tombstones, history and search behavior.

**Expected result:** public OSS enumeration alone is insufficient for a lossless Mem0-native round trip; our canonical export plus rebuild path should still pass.

### M0-4 — Raw-retention audit

**Goal:** quantify and control every raw copy.

- Run the OSS engine and coding-agent plugin on synthetic conversations containing marker secrets.
- Locate Qdrant payloads, `history.db`, `evidence.sqlite3`, plugin data, logs and telemetry queue files.
- Verify redaction boundaries, deletion after successful extraction, pause/resume, crash recovery and uninstall behavior.

**Pass condition for our product:** the default leaves no raw marker after successful structured extraction; failures respect the documented TTL and remain inspectable/deletable.

### M0-5 — Agent install UX comparison

**Goal:** borrow the speed of Mem0 Agent Mode without hidden cloud coupling.

- Time fresh installs for built-in local, Mem0 OSS local and Mem0 Platform.
- From one command, detect Claude/Codex, install the adapter, print created files and run add/search smoke tests.
- Test non-interactive CI, missing runtime, invalid key, offline, duplicate MCP registration and rollback.

**Pass condition:** the local default works without account creation; choosing Platform requires explicit consent and clearly labels data egress.

### M0-6 — Additive lifecycle / contradiction behavior

**Goal:** see how current Mem0 retrieval behaves when facts change without automatic update/delete.

- Add dated contradictory preferences and employment/location facts.
- Compare semantic search, explicit update/delete, expiration, metadata dates and our canonical temporal resolution.
- Verify that Mem0 is used for candidate retrieval only and cannot override canonical `valid_from` / `valid_to` decisions.

## Recommended planning conclusion

Proceed with `memory-mem0` as a Milestone 2 provider seam and dogfooding option, not an MVP canonical store. In Milestone 1, implement the built-in file/SQLite memory and the provider-neutral contract/export/rebuild tests first. Run M0-1, M0-2 and M0-3 before accepting any Mem0-specific production dependency. The coding-agent adapter may borrow Mem0's focused search tool and local durable queue design, but must use this project's own retention, provenance and consent rules.

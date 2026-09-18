# Upstream Research: Graphiti data model, temporal semantics, and projection boundary

> Researched 2026-09-18 · PRD refs: §5, §13, §32, §51 · Scope: official `getzep/graphiti` repository and Zep/Graphiti documentation only

## Executive conclusion

Graphiti is a strong **optional temporal-relationship projection**, but it must not own the project's canonical facts.

The fit is strongest when a canonical fact can be represented as a binary relationship and the desired behavior is incremental entity/edge extraction, semantic retrieval, and automatic invalidation of contradictory relationship facts. The fit is materially weaker for unary/entity attributes, exact source metadata, explicit supersession chains, review state, confidence, and deterministic round-trip export.

The decisive upstream boundary is confirmed by both source and a maintainer:

- relationship facts are `EntityEdge` records with `valid_at`, `invalid_at`, `created_at`, `expired_at`, `reference_time`, and episode IDs;
- entity attributes and summaries are mutable current-state properties;
- Graphiti does **not** currently version node properties. Maintainer Daniel Chalef states: “Node summaries are intended to be mutable. We haven't yet implemented the concept of versioned node properties.” ([issue #1166 maintainer comment](https://github.com/getzep/graphiti/issues/1166#issuecomment-3828900342)).

Recommended architecture: retain open-format Canonical Facts as source of truth, maintain an explicit projection ledger, and treat all Graphiti output as rebuildable. Do not infer canonical supersession, confidence, or provenance solely from Graphiti state.

---

## Research snapshot and reproducibility

| Item | Observed value |
|---|---|
| Repository | [`getzep/graphiti`](https://github.com/getzep/graphiti) |
| Default branch inspected | `main` |
| `main` commit | [`de8eb5b896c05ed1b5b329d4cb52015446d65e21`](https://github.com/getzep/graphiti/commit/de8eb5b896c05ed1b5b329d4cb52015446d65e21), committed 2026-09-17 08:18:45 UTC |
| Latest release observed | [`v0.30.2`](https://github.com/getzep/graphiti/releases/tag/v0.30.2), published 2026-09-08 20:38:41 UTC |
| Release commit | [`eaa4128681bc53487138a4bbc22d58336ebe70d2`](https://github.com/getzep/graphiti/commit/eaa4128681bc53487138a4bbc22d58336ebe70d2) |
| Difference relevant to core | At inspection time `main` was 9 commits ahead, but the compare API listed no changed `graphiti_core/**` files; all code permalinks below use the inspected `main` SHA. |
| Package version in source | `graphiti-core 0.30.2` ([`pyproject.toml` lines 1–20](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/pyproject.toml#L1-L20)) |
| License | Apache-2.0 ([project declaration](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/pyproject.toml#L1-L12), [license text](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/LICENSE)) |

This is a point-in-time assessment. Pin the adapter's tested Graphiti version; do not code against `main` implicitly.

---

## 1. Current graph data model — verified facts

### 1.1 Nodes

All node types inherit `uuid`, `name`, `group_id`, `labels`, and `created_at`. `group_id` is the graph partition key. ([`Node`](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L93-L109))

| Node | Important fields | Meaning / caveat |
|---|---|---|
| `EpisodicNode` | `source`, `source_description`, `content`, `valid_at`, `entity_edges`, `episode_metadata` | Raw ingested artifact and provenance anchor. `valid_at` is documented in the model as when the original document was created. `episode_metadata` is declared but is not persisted in the inspected code. ([model](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L318-L354)) |
| `EntityNode` | `name_embedding`, `summary`, `attributes` | Entity current view. Custom attributes are schema-dependent and, except on Kuzu, flattened into graph node properties when saved. ([model/save](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L499-L582)) |
| `CommunityNode` | `name_embedding`, `summary` | Derived cluster/community summary. ([source](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L687-L715)) |
| `SagaNode` | `summary`, first/last episode IDs, summary watermarks | Optional ordered episode grouping. It separates wall-clock summary watermark from maximum episode `valid_at`. ([source](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L867-L900)) |

Episode input types are `message`, `json`, `text`, and `fact_triple`. ([`EpisodeType`](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L54-L90))

### 1.2 Edges

All edge models inherit `uuid`, `group_id`, source/target node UUIDs, and `created_at`. ([`Edge`](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/edges.py#L49-L57))

| Edge / relation | Important fields | Role |
|---|---|---|
| `EpisodicEdge` / `MENTIONS` | base edge fields | Connects an episode to an entity. The persistence query is explicit `(:Episodic)-[:MENTIONS]->(:Entity)`. ([query](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/models/edges/edge_db_queries.py#L19-L27)) |
| `EntityEdge` / `RELATES_TO` | `name`, `fact`, embedding, `episodes`, `valid_at`, `invalid_at`, `created_at`, `expired_at`, `reference_time`, custom `attributes` | The temporal fact record. ([model](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/edges.py#L263-L285)) |
| `CommunityEdge` / `HAS_MEMBER` | base fields | Derived community membership. ([query](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/models/edges/edge_db_queries.py#L250-L296)) |
| `HasEpisodeEdge` / `HAS_EPISODE` | base fields | Saga-to-episode membership. ([query](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/models/edges/edge_db_queries.py#L308-L324)) |
| `NextEpisodeEdge` / `NEXT_EPISODE` | base fields | Orders episodes in a saga. ([query](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/models/edges/edge_db_queries.py#L327-L343)) |

Graphiti's README describes the same conceptual split: entities have evolving summaries, fact/relationship edges have temporal validity windows, and episodes are raw provenance. ([README lines 60–77](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/README.md#L60-L77))

---

## 2. Temporal semantics — verified facts

Graphiti's useful temporal model is concentrated on `EntityEdge`:

| Field | Source-level semantics | Closest PRD concept |
|---|---|---|
| `valid_at` | Real-world time at which the edge fact became true. The extraction prompt resolves explicit/relative dates and, for ongoing present-tense facts, uses the episode reference time. ([model](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/edges.py#L274-L279), [prompt rules](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/prompts/extract_edges.py#L168-L175)) | `valid_from` |
| `invalid_at` | Real-world time at which the edge fact stopped being true. ([same model](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/edges.py#L274-L279)) | `valid_until` |
| `created_at` | Wall-clock creation/ingestion time for the graph artifact. `add_episode()` captures `utc_now()` and stores it on the episode while storing caller `reference_time` as episode `valid_at`. ([construction](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1130-L1169)); extracted edges likewise use `utc_now()`. ([edge construction](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L299-L314)) | approximately `ingested_at` |
| `expired_at` | Wall-clock time when Graphiti learned/decided that an edge was invalid and marked it expired; contradiction handling sets it to `utc_now()`. ([invalidation](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L538-L573), [new-edge handling](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L820-L844)) | no direct PRD field; useful system-time audit |
| `reference_time` | Timestamp of the episode used to produce the edge; populated from the attributed episode's `valid_at`. ([construction](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L290-L314)) | sometimes `observed_at`, but not equivalent in all source types |

Search filters expose all four edge lifecycle timestamps (`valid_at`, `invalid_at`, `created_at`, `expired_at`) plus edge UUID, type, labels, and custom properties. ([`SearchFilters`](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/search/search_filters.py#L55-L67))

### What automatic invalidation actually does

**Fact:** candidate duplicate/contradiction selection is LLM-assisted. The resolver supplies existing facts and invalidation candidates to a prompt, then validates returned indexes. ([resolver](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L684-L776))

**Fact:** after a contradiction is selected, date ordering controls which edge gets `invalid_at` and `expired_at`; older overlapping facts are closed at the newer fact's `valid_at`. ([algorithm](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L538-L573))

**Inference:** temporal correctness therefore depends on both model extraction/judgment and timestamp quality. Graphiti invalidation is valuable retrieval enrichment, not a safe replacement for an explicit canonical `supersedes` decision.

---

## 3. Incremental ingest and public surfaces — verified facts

### Python library

1. `add_episode(...)` accepts raw content, source description/type, caller reference time, optional stable episode UUID, group ID, custom entity/edge schemas, extraction instructions, prior episode IDs, and optional saga. It extracts/deduplicates nodes and edges, hydrates attributes/summaries, invalidates contradictions, and persists results. ([signature and pipeline](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1043-L1061), [pipeline body](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1130-L1283))
2. Upstream recommends sequentially awaiting episodes rather than concurrently ingesting them into the same evolving graph. ([notes](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1113-L1128))
3. `add_episode_bulk(...)` accepts `RawEpisode` records (`name`, optional UUID, content, source description/type, reference time). ([`RawEpisode`](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/bulk_utils.py#L101-L108), [bulk API](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1290-L1300))
4. In the inspected source, the bulk path flows through edge resolution and persists invalidated edges. ([bulk notes and implementation](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1335-L1353), [persistence](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1437-L1465))
5. `add_triplet(source_node, edge, target_node)` permits preconstructed nodes and a relationship edge, but still performs retrieval, LLM-assisted deduplication/contradiction handling, embedding, and upsert. ([implementation](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1704-L1822))

### Service surfaces

- The repository includes a FastAPI service. Its `/messages` endpoint returns `202`, enqueues each message, then calls `add_episode`; it is asynchronous and the shown router does not expose a per-job completion/status resource. ([router](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/server/graph_service/routers/ingest.py#L13-L70))
- The official MCP server advertises `add_episode`, `search_facts`, `search_nodes`, `get_episodes`, `delete_episode`, and `clear_graph`. ([official MCP guide](https://help.getzep.com/graphiti/getting-started/mcp-server))

### Documentation discrepancy to resolve in PoC

The official “Adding Episodes” page currently says bulk ingestion should be used only on empty graphs or when edge invalidation is not required, because the bulk pipeline does not invalidate edges. ([official guide](https://help.getzep.com/v2/graphiti/core-concepts/adding-episodes)) The inspected `v0.30.2` source says and implements the opposite. Treat source at the pinned version as authoritative, and add a regression test; do not encode the older documentation statement as an architectural assumption.

---

## 4. Provenance — verified facts and limits

### What Graphiti preserves

- Episodes store raw content by default; `store_raw_episode_content=False` deliberately blanks content immediately before persistence. ([constructor option](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L137-L176), [blanking path](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L742-L758))
- Episode-to-entity lineage is represented by `MENTIONS` edges. For multi-episode extraction, Graphiti asks the model for episode indexes and maps entities/facts back to those episodes. ([entity attribution context](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/node_operations.py#L109-L128), [fact attribution](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L170-L200))
- Each `EntityEdge` carries an `episodes: list[str]`; repeated equivalent facts can append an additional episode ID. ([model](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/edges.py#L263-L282), [duplicate reuse](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L684-L695))
- `get_nodes_and_edges_by_episode()` reconstructs derived nodes and edges for supplied episode UUIDs. ([source](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1690-L1702))

### Current provenance gaps

1. **No source span/page/section schema.** Core provenance is episode-level: free-form `source_description`, raw `content`, timestamps, and IDs. Fine-grained canonical evidence locators need to remain in the vault or adapter ledger.
2. **`episode_metadata` does not round-trip in inspected code.** The Pydantic field exists, but `EpisodicNode.save()` omits it, persistence queries hard-code other fields, and read reconstruction omits it. ([model/save](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L318-L359), [save/return queries](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/models/nodes/node_db_queries.py#L30-L66), [open issue #1769](https://github.com/getzep/graphiti/issues/1769))
3. **Attribution is model-mediated.** In multi-episode input, the LLM returns `episode_indices`; code clamps invalid indexes and falls back to all episodes if none remain. ([edge mapping](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L290-L314)) This is useful lineage, not exact evidentiary citation.
4. **`add_triplet` provenance needs a spike.** The method creates a synthetic `EpisodicNode` for resolution but does not save it; duplicate reuse can append that synthetic UUID to an existing edge's `episodes`. This is a source-derived risk, not an upstream guarantee. ([synthetic episode](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L1799-L1814), [duplicate append](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/edge_operations.py#L684-L695))

---

## 5. Node attribute history — exact answer

### Verified facts

- Entity custom attributes are a single dictionary on the current `EntityNode`; there is no per-attribute `valid_at`, `invalid_at`, version UUID, or history list. ([model](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L499-L504))
- Current extraction uses an overlay merge: omitted or cap-dropped keys retain prior values, but a newly emitted value for an existing key replaces that key in the current dictionary. ([merge contract](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/attribute_utils.py#L46-L59), [implementation](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/utils/maintenance/attribute_utils.py#L220-L253))
- Save is an upsert by UUID. Neo4j and FalkorDB use `MERGE` followed by `SET n = ...`, leaving only the new current property map; Kuzu updates its fixed fields including serialized attributes. ([single-save queries](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/models/nodes/node_db_queries.py#L137-L190), [bulk queries](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/models/nodes/node_db_queries.py#L194-L270))
- The maintainer explicitly confirms node properties are not versioned. ([issue #1166](https://github.com/getzep/graphiti/issues/1166#issuecomment-3828900342))

### Precise interpretation

Graphiti no longer blindly clears all prior node attributes when no type applies—the current code preserves them—but it **does overwrite the prior value of a changed key without retaining that key's history**. Mutable summary text behaves similarly. Therefore a changing property such as `career_interest`, `location`, or `employee_count` must be represented as a temporal relationship fact (or remain canonical outside Graphiti) if historical reconstruction matters.

---

## 6. Canonical Fact → Graphiti projection

### 6.1 Field mapping

| Canonical Fact field | Candidate Graphiti projection | Fidelity |
|---|---|---|
| `id` | `EntityEdge.uuid`; also keep it in an external projection ledger | High only if adapter creates stable edges and Graphiti does not deduplicate to another UUID |
| `module` | `group_id`, labels, or a custom property | Semantic mismatch; `group_id` is partitioning, not module taxonomy |
| `type` | edge `name` / relation type, sometimes entity labels | Usually useful, not lossless for unary fact types |
| `statement` | `EntityEdge.fact` | Good text carrier, but ingestion may paraphrase it; direct `add_triplet` is more deterministic |
| `valid_from` | edge `valid_at` | Direct |
| `valid_until` | edge `invalid_at` | Direct |
| `observed_at` | edge `reference_time` or episode `valid_at` | Partial; source-document reference time is not always observation time |
| `ingested_at` | edge/episode `created_at` | Direct enough for projection ingest time, but Graphiti assigns it |
| `supersedes` / `superseded_by` | no first-class field | Lost unless external ledger/custom property preserves it; Graphiti's contradiction invalidation is implicit and LLM-mediated |
| `source` | episode raw JSON/text + `source_description` + external ledger | Episode-level only; structured episode metadata is currently broken |
| `episode` | edge `episodes[]` and `MENTIONS` | Good for episode IDs, but not guaranteed exact citation span |
| `confidence` | custom edge property or external ledger | No core semantic behavior; can be cleared/changed by edge-resolution paths unless tested |
| `review_status` | custom edge property or external ledger | No core workflow or query convention |

### 6.2 Structural loss points

1. Graphiti facts are primarily **binary edges between two distinct entities**. The extraction prompt rejects same-entity facts and attempts to convert concrete unary details into a relation to a second entity. ([prompt rules](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/prompts/extract_edges.py#L131-L160)) A canonical unary scalar cannot be projected without either creating a value/entity node or using mutable node attributes.
2. One canonical statement can yield zero, one, or multiple nodes/edges after extraction and deduplication. The mapping is not intrinsically one-to-one.
3. Graphiti can paraphrase facts and normalize relation names. Round-trip equality of canonical statement text is not a supported invariant.
4. Deduplication can reuse an existing edge UUID and append provenance, so canonical ID → Graphiti UUID may be many-to-one.
5. Contradiction handling records temporal closure but no explicit edge-to-edge supersession pointer.
6. Custom properties are provider-dependent: Kuzu serializes an `attributes` JSON string, while Neo4j/FalkorDB/Neptune flatten properties; nested values can violate property-graph storage constraints. Kuzu is also deprecated upstream. ([entity save paths](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/nodes.py#L546-L578), [README warning](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/README.md#L206-L220))

### 6.3 Recommended projection contract

This is an architectural inference/recommendation, not an upstream feature:

```text
Canonical Fact / Evidence
        │
        ├── deterministic projection envelope (version + canonical hash)
        │       ├── stable canonical_fact_id
        │       ├── stable canonical_episode_id
        │       ├── projection revision / Graphiti version
        │       └── expected node/edge IDs
        │
        ├── Graphiti episode(s) + entity edge(s)
        └── adapter-owned projection ledger
                canonical IDs ↔ actual Graphiti IDs + warnings/losses
```

The ledger must be sufficient to delete and rebuild the entire Graphiti projection without reading truth back from Graphiti. Store confidence, review status, exact evidence locators, supersession links, and canonical hashes outside the graph even if some are duplicated into custom properties for filtering.

---

## 7. Backend dependencies and local operation

### Verified requirements

- Python `>=3.10,<4`; required Python dependencies include Pydantic, Neo4j driver, OpenAI client, Tenacity, NumPy, dotenv, and PostHog. ([`pyproject.toml`](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/pyproject.toml#L1-L21))
- Supported graph providers in the driver abstraction are Neo4j, FalkorDB, Kuzu, and Neptune. ([enum](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/driver/driver.py#L59-L64))
- README requirements are Neo4j 5.26, FalkorDB 1.1.2, Neptune plus OpenSearch Serverless, or deprecated Kuzu. Defaults are Neo4j plus OpenAI LLM, embeddings, and reranker. ([README requirements](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/README.md#L154-L170), [constructor defaults](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/graphiti_core/graphiti.py#L207-L240))
- FalkorDB support is an optional extra; embedded FalkorDB Lite requires Python 3.12+. ([extras](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/pyproject.toml#L27-L40))
- Local OpenAI-compatible LLM and embeddings are possible (the official example uses Ollama), but upstream warns that structured-output reliability varies and smaller models often fail extraction. ([README local-provider guide](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/README.md#L536-L610), [official LLM configuration](https://help.getzep.com/graphiti/configuration/llm-configuration))
- The root Docker Compose starts the Graphiti service plus Neo4j by default, or a FalkorDB profile. ([compose](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/docker-compose.yml))
- Telemetry is opt-out; upstream says it sends an anonymous ID, system/version, and provider/backend choices—not graph contents—and can be disabled with `GRAPHITI_TELEMETRY_ENABLED=false`. ([README telemetry](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/README.md#L618-L669))

### Product implication

Graphiti cannot satisfy the PRD's zero-friction default backend: it needs a graph database plus LLM/embedding infrastructure and operational tuning. Keep it in the advanced/temporal recipe, disabled by default. For privacy-oriented local mode, require an explicit telemetry-off setting and document that local extraction quality is model-dependent.

---

## 8. License implications

**Verified:** Graphiti itself is Apache-2.0, including an express patent grant and redistribution conditions. ([license](https://github.com/getzep/graphiti/blob/de8eb5b896c05ed1b5b329d4cb52015446d65e21/LICENSE))

**Implications:**

- A separately packaged optional provider can depend on or adapt Graphiti under Apache-2.0.
- Preserve the license, copyright/attribution notices, and notices on modified upstream files if any code is copied or modified.
- Prefer a clean adapter calling public APIs over copying Graphiti internals; this reduces upgrade and provenance burden.
- Graphiti's license does not settle the licenses/terms of Neo4j editions, FalkorDB, hosted LLMs, or model weights. The plugin manifest/install UX must report those separately.
- This is engineering license provenance, not legal advice.

---

## 9. ADR implications

### ADR-GRAPHITI-001 — Graphiti is a rebuildable optional projection

**Proposed decision:** accept.

- Canonical open-format facts and evidence remain authoritative.
- No migration may require exporting truth from Graphiti to preserve the user.
- Provider deletion/rebuild is a supported operation.

### ADR-GRAPHITI-002 — Historical facts must be edges, not node attributes

**Proposed decision:** accept.

- Use node attributes only for derived/current convenience fields.
- Any field whose prior value matters becomes a canonical temporal Fact and projects to an edge/value node pattern.
- Never rely on entity summary or attributes for historical audit.

### ADR-GRAPHITI-003 — Adapter-owned projection ledger

**Proposed decision:** accept.

Minimum ledger fields:

```yaml
canonical_fact_id:
canonical_episode_id:
canonical_hash:
projection_schema_version:
graphiti_version:
graphiti_group_id:
graphiti_episode_uuids: []
graphiti_node_uuids: []
graphiti_edge_uuids: []
projected_at:
loss_flags: []
```

### ADR-GRAPHITI-004 — Version pin and capability probe

**Proposed decision:** accept.

- Pin a tested minor/patch version.
- On startup verify backend, package version, indices/constraints, embedding dimension, and required APIs.
- Feature-gate known moving surfaces such as `episode_metadata`, bulk invalidation, saga support, and `fact_triple` behavior.

### ADR-GRAPHITI-005 — No Graphiti dependency in MVP core

**Proposed decision:** accept.

- Builtin memory remains the default.
- The Graphiti provider may ship later behind an extra/package boundary and advanced recipe.
- Core schemas must nevertheless retain bi-temporal and supersession fields from Day 1.

---

## 10. Required PoC spikes before implementation

### Spike A — Changed node attribute history

Ingest the same company/person in two dated episodes with a changed scalar attribute.

Pass criteria:

- demonstrate that only the latest node property remains;
- demonstrate that equivalent relationship-edge modeling retains both facts and closes the earlier edge;
- capture exact Neo4j/FalkorDB queries and results as a regression fixture.

### Spike B — Deterministic Canonical Fact projection

Project a fixed canonical fact twice with stable IDs, once through `add_episode` and once through `add_triplet` in isolated graphs.

Measure:

- actual edge/node/episode IDs;
- paraphrase/relation-name drift;
- dedupe behavior;
- custom attribute survival;
- LLM call count and token cost;
- whether the second run is idempotent.

Pass criterion: choose one supported adapter path and record its unavoidable losses. Do not assume either path is idempotent before this test.

### Spike C — Provenance round-trip

Use one fact with multiple evidence locators and one episode supporting multiple facts.

Verify:

- `EntityEdge.episodes` membership;
- `MENTIONS` links;
- delete/re-ingest behavior;
- `get_nodes_and_edges_by_episode()`;
- behavior of `episode_metadata` at the pinned version;
- absence of dangling episode UUIDs after `add_triplet` dedupe.

Pass criterion: exact source locators remain recoverable from the canonical ledger even if Graphiti loses them.

### Spike D — Out-of-order correction / bi-temporal behavior

Ingest 2026 state, then a late-arriving 2025 correction, then a 2027 change.

Verify `valid_at`, `invalid_at`, `created_at`, `expired_at`, current-as-of query behavior, and explicit canonical supersession. Test both single and bulk ingest because official docs and current source disagree on bulk invalidation.

### Spike E — Local privacy deployment

Test Neo4j and FalkorDB separately with:

- telemetry disabled;
- a fully local OpenAI-compatible LLM/embedder/reranker stack;
- restart persistence;
- backup/restore;
- representative Chinese and English personal-context episodes;
- malformed structured-output recovery.

Pass criterion: publish measured resource requirements and extraction error rates; “local supported” alone is insufficient.

### Spike F — Provider portability / rebuild

Starting from only the Canonical Vault and projection ledger schema, build Graphiti on backend A, delete it, rebuild on backend B, and compare canonical-ID coverage plus retrieval results.

Pass criterion: zero canonical data loss; projection drift is reported rather than silently accepted.

---

## Final planning recommendation

Graphiti should remain an advanced provider planned for a post-MVP milestone. Design the seam now, but implement only:

1. canonical bi-temporal fact fields;
2. stable fact/episode IDs;
3. provider-neutral projection events;
4. a projection ledger interface;
5. conformance tests that a future Graphiti adapter must pass.

Do not add Neo4j/FalkorDB, Graphiti, or Graphiti-specific graph entities to the MVP core merely to be “ready.” Readiness means a loss-aware adapter boundary and rebuildable canonical source—not prepaying the backend's operational complexity.

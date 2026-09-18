# Upstream Research: LlamaIndex core / integrations architecture

> Researched 2026-09-18 · PRD refs: §11, §12, §13, §32, §35, §48, §51 · Researcher: Codex subagent (`research_llamaindex`)

## Executive summary

- LlamaIndex's real split is **one substantial core distribution plus hundreds of separately versioned integration distributions**. At the pinned source snapshot, `llama-index-core` contains contracts, orchestration, schemas, serialization, in-process implementations and many storage/retrieval facilities; integrations depend inward on core and provide concrete vendor/source implementations. It is not a micro-kernel with all behavior outside core. [Core package metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/pyproject.toml) · [core tree](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core)
- The Python distribution/import design uses **independent distributions sharing the `llama_index` implicit namespace**: core imports are under `llama_index.core.*`; integrations use paths such as `llama_index.readers.obsidian` and `llama_index.memory.mem0`. The distribution name and import path are intentionally different. [Repository README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/README.md) · [PyPA namespace guidance](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/)
- This snapshot does **not** expose a general runtime plugin registry based on Python entry points. Package discovery inside the monorepo is filesystem scanning for `pyproject.toml`; application code normally imports an integration explicitly. A few core deserializers use fixed registries and optional `try/except ImportError` imports, which is not equivalent to generic plugin discovery. [`llama-dev` package discovery](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/utils.py) · [embedding loader](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/embeddings/loading.py)
- `[tool.llamahub]` in integration `pyproject.toml` is **build-time documentation metadata** (`import_path`, exported class authors, example flag). The docs build scans it to generate API-reference pages. It is too thin to satisfy the PRD's capability/setup/privacy/trade-off manifest and should not be copied as the product's canonical registry. [Obsidian metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/pyproject.toml) · [docs generator](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/docs/scripts/prepare_for_build.py)
- LlamaIndex's change-aware test runner is worth borrowing: it identifies changed packages and direct dependants, runs package-local pytest jobs in parallel, and CI asks remote-system tests to use mocks. However, no shared integration conformance suite was found; the PRD explicitly needs one. [`llama-dev test`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/test/__init__.py) · [contribution guide](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/CONTRIBUTING.md)
- The current contribution model has changed: fixes to existing integrations are welcome, but **new integration packages are no longer accepted in the monorepo**; contributors are directed to maintain new integrations in their own repositories and publish them independently to PyPI. A workflow automatically closes PRs adding a new `pyproject.toml`. [Contribution guide](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/CONTRIBUTING.md) · [enforcement workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/close_new_integration_prs.yml)
- For this project's MVP, borrow the **dependency direction, explicit contracts, selective installation, independent plugin versions, generated docs and affected-package testing**. Do not borrow the 600-package scale, top-level namespace fragility, OpenAI-oriented starter defaults, thin metadata, or absence of a universal conformance layer.

---

## Research snapshot and method

### Pinned upstream state

| Item | Pinned value | Official source |
|---|---|---|
| Repository | `run-llama/llama_index` | [GitHub repository](https://github.com/run-llama/llama_index) |
| Default branch snapshot | `c60937d3099b89e66ff9040f1c45030bc4e407e9` | [commit](https://github.com/run-llama/llama_index/commit/c60937d3099b89e66ff9040f1c45030bc4e407e9) |
| Snapshot commit date | 2026-09-17 19:30:58 UTC | [commit](https://github.com/run-llama/llama_index/commit/c60937d3099b89e66ff9040f1c45030bc4e407e9) |
| Latest GitHub release observed | `v0.14.24`, published 2026-08-19 | [release](https://github.com/run-llama/llama_index/releases/tag/v0.14.24) |
| Release commit | `9ba74b8628712e68d16955d9492b5192bd7e6f00`, 2026-08-19 18:46:08 UTC | [commit](https://github.com/run-llama/llama_index/commit/9ba74b8628712e68d16955d9492b5192bd7e6f00) |
| Distance from release to researched HEAD | 38 commits ahead | [comparison](https://github.com/run-llama/llama_index/compare/v0.14.24...c60937d3099b89e66ff9040f1c45030bc4e407e9) |

The repository was not cloned. Directory enumeration and file reads used authenticated GitHub REST API calls against the pinned SHA. The recursive tree contained 13,560 entries and was not truncated. The integration-package count below is a deterministic count of paths matching `llama-index-integrations/**/pyproject.toml` in that tree. [Pinned Git Trees API response](https://api.github.com/repos/run-llama/llama_index/git/trees/c60937d3099b89e66ff9040f1c45030bc4e407e9?recursive=1)

### Fact / inference convention

- **Fact** means directly observed in the pinned official repository, an official release, or official documentation.
- **Inference** means a design conclusion for this project. It is intentionally separated from upstream facts.
- Counts and negative findings are snapshot-scoped; they are not claims about all historical or future LlamaIndex releases.

---

## 1. Core and integration packages: the real boundary

### Observed facts

1. **The repository is a Python monorepo, not a single distribution.** At top level it has `llama-index-core/`, `llama-index-integrations/`, `llama-index-instrumentation/`, `llama-index-utils/`, `llama-dev/`, docs and release workflows. The integrations README says integrations are categorized by type and each is its own Python package. [Pinned repository tree](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9) · [integrations README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/README.md)

2. **There were 606 integration distributions at the snapshot**, counted by `pyproject.toml`, across 26 top-level categories:

   | Category | Packages | Category | Packages |
   |---|---:|---|---:|
   | readers | 149 | llms | 102 |
   | vector_stores | 78 | tools | 67 |
   | embeddings | 66 | storage | 50 |
   | postprocessor | 26 | retrievers | 14 |
   | callbacks | 10 | indices | 9 |
   | graph_stores | 7 | node_parser | 6 |
   | program | 3 | voice_agents | 3 |
   | agent | 2 | extractors | 2 |
   | memory | 2 | output_parsers | 2 |
   | graph_rag, ingestion, observability, protocols, question_gen, response_synthesizers, selectors, sparse_embeddings | 1 each | **Total** | **606** |

   Source: deterministic path count over the [pinned Git tree](https://api.github.com/repos/run-llama/llama_index/git/trees/c60937d3099b89e66ff9040f1c45030bc4e407e9?recursive=1). The root README's prose says "over 300" integrations; the exact source-tree count is therefore more current and more precise than the marketing shorthand. [README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/README.md)

3. **Core owns contracts and cross-cutting execution behavior.** Examples include `BaseReader`, resource-reading mixins, `BaseRetriever`, `BaseMemory`, schema/document types, settings, instrumentation, callbacks, ingestion, query engines, storage protocols and serialization. `BaseReader` supplies sync/async convenience behavior; `BaseRetriever` wraps subclass retrieval with callbacks, instrumentation and recursive handling; `BaseMemory` defines `get`, `put`, `set`, `reset` and async wrappers. [reader contract](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/readers/base.py) · [retriever contract](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/base/base_retriever.py) · [memory contract](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/memory/types.py)

4. **Core also contains concrete built-ins; it is not interface-only.** It includes file/JSON/string readers, mock embeddings, chat-memory buffers, vector memory, simple and SQL chat stores, simple document/index/KV stores and substantial orchestration logic. Its published dependency set includes SQLAlchemy, `fsspec`, HTTP clients, NLTK, NumPy, `tiktoken`, NetworkX, Pillow, Pydantic, workflow support and more. [core source tree](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core) · [core `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/pyproject.toml)

5. **Integration distributions depend inward on core and vendor libraries.** For example, `llama-index-memory-mem0` depends on `llama-index-core>=0.13.0,<0.15` and `mem0ai>=2.0.0,<3.0.0`; its implementation subclasses `BaseMemory`, composes the core `Memory`, then adapts Mem0 search/add operations into LlamaIndex chat-memory behavior. [Mem0 package metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/memory/llama-index-memory-mem0/pyproject.toml) · [Mem0 adapter](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/memory/llama-index-memory-mem0/llama_index/memory/mem0/base.py)

6. **An integration can depend on other integrations, not only core.** The Obsidian reader depends on `llama-index-readers-file` and `llama-index-embeddings-openai` in addition to core. This demonstrates that the upstream graph permits integration-to-integration edges and can pull in arguably surprising transitive dependencies. [Obsidian `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/pyproject.toml)

7. **The LlamaIndex memory contract is narrower than this PRD.** `BaseMemory` is chat-message oriented (`get/get_all/put/set/reset`). It does not define the PRD's evidence provenance, candidate promotion, confidence, temporal validity, review audit or permission semantics. [memory contract](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/memory/types.py)

### Inferences for this project

- Keep the **dependency rule**: provider packages depend on a stable core contract; core must never import a concrete provider as a required dependency.
- Do not interpret "core + integrations" as "empty core + everything is a plugin." This product's core should own canonical truth, evidence/provenance types, temporal semantics, policy enforcement, plugin contracts, and the minimal local implementation needed for a no-key path.
- Integration-to-integration dependencies should be disallowed by default. If composition is needed, express it as optional capabilities or a recipe so installing a source adapter does not unexpectedly install a model provider.
- A Mem0/Graphiti adapter may wrap a backend's native episodic mechanism, as LlamaIndex's Mem0 adapter wraps Mem0, but it must translate into this project's richer canonical operations and cannot redefine truth/provenance semantics.

---

## 2. Python distributions, namespaces and discovery

### Observed facts

1. **Two installation modes are first-class.** The umbrella distribution `llama-index` provides a starter bundle; advanced users can install `llama-index-core` plus selected integration distributions. The official install docs describe the ecosystem as a collection of namespaced Python packages. [README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/README.md) · [installation docs](https://developers.llamaindex.ai/python/framework/getting_started/installation/)

2. **Distribution names map to shared namespace import paths.** Examples:

   | Distribution | Import path |
   |---|---|
   | `llama-index-core` | `llama_index.core` |
   | `llama-index-readers-obsidian` | `llama_index.readers.obsidian` |
   | `llama-index-memory-mem0` | `llama_index.memory.mem0` |
   | `llama-index-llms-openai` | `llama_index.llms.openai` |

   The README explicitly documents the rule that imports containing `.core` belong to core while paths without `.core` generally belong to integrations. [README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/README.md) · [Obsidian package](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian) · [Mem0 package](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/memory/llama-index-memory-mem0)

3. **The shared top-level package is an implicit namespace.** In the normal core and integration layouts, `llama_index/` itself has no `__init__.py`; regular leaf packages such as `llama_index/readers/obsidian/` do. PyPA documents this as the PEP 420 native-namespace pattern and warns that every participating distribution must use a compatible approach, otherwise other portions may become unimportable. [core package tree](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index) · [Obsidian package tree](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/llama_index) · [PyPA namespace guidance](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/)

4. **Normal use is explicit import, not automatic activation.** Installing `llama-index-readers-obsidian` makes `llama_index.readers.obsidian.ObsidianReader` importable, but an application still imports and configures it. The integration `__init__.py` exports the public class with `__all__`. [Obsidian `__init__.py`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/llama_index/readers/obsidian/__init__.py) · [Obsidian README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/README.md)

5. **Monorepo package discovery is filesystem-based.** `llama-dev` treats a directory containing `pyproject.toml` as a package, recursively scans category directories (with special recursion for `storage`), and adds core/instrumentation/utils. This is a development/release inventory, not installed-plugin discovery. [`llama-dev` utilities](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/utils.py)

6. **The observed integration metadata does not declare Python entry-point groups.** Representative integration `pyproject.toml` files use `[tool.llamahub]`, while runtime loaders in core use fixed dictionaries and selected optional imports. For comparison, PyPA lists naming convention, namespace scanning and package-metadata entry points as the three common plugin-discovery strategies, and recommends `importlib.metadata.entry_points()` for metadata-based discovery. [Obsidian metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/pyproject.toml) · [embedding loader](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/embeddings/loading.py) · [PyPA plugin discovery](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)

7. **Some internal loaders are closed registries.** `core/readers/loading.py` recognizes only classes in its `ALL_READERS` dict; `core/embeddings/loading.py` recognizes the mock embedding and a small set of optionally importable integrations. These support serialization/reloading of known components, not an ecosystem-wide registry. [reader loader](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/readers/loading.py) · [embedding loader](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/embeddings/loading.py)

### Inferences for this project

- Use **distribution metadata entry points for installed-plugin discovery**, plus a project-defined manifest for capability/policy data. Entry points are explicit, inspectable without importing every package and supported by the Python standard library.
- Avoid making the project's primary top-level import package a community-writable namespace. PyPA specifically warns that a bad plugin can break the main namespace. Prefer independent plugin import packages (for example, a normalized project prefix) that register entry points into a core-owned group.
- Separate three concepts that LlamaIndex partly conflates:
  1. installed distribution inventory;
  2. runtime activation/configuration;
  3. public registry/advisor metadata.
- The CLI should report all three states: **installed**, **enabled**, and **available/recommended**. Merely being importable must not silently grant access to personal data.

---

## 3. Integration metadata and registry behavior

### Observed facts

1. **Integration package metadata has two layers.** Standard `[project]` metadata carries name, version, Python range, dependencies, license and maintainers; `[tool.llamahub]` adds `contains_example` and `import_path`, while `[tool.llamahub.class_authors]` maps exported classes to authors. [Obsidian `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/pyproject.toml) · [Mem0 `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/memory/llama-index-memory-mem0/pyproject.toml)

2. **The docs builder scans every integration `pyproject.toml`.** It reads `tool.llamahub.import_path` and `class_authors`, generates MkDocs API-reference stubs, and adds package paths to the documentation build. This is a concrete, useful example of generating docs from package-owned metadata. [docs generator](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/docs/scripts/prepare_for_build.py)

3. **The public integrations page is primarily a curated documentation index.** It points readers and tools to repository directories and links to generated component pages. It does not present the PRD's setup-time, API-key, local-only, privacy, capability, maturity or trade-off fields. [official integrations page](https://developers.llamaindex.ai/python/framework/community/integrations/)

4. **Package metadata quality is not uniformly strong.** At the pinned SHA, the Obsidian integration still has placeholder `[project].authors` (`Your Name`, `you@example.com`) while maintainers are real handles; its package version is `0.8.0`, but its checked-in changelog only records `0.1.2` from 2024. These are snapshot facts about one package, not a claim that every LlamaIndex integration has stale metadata. [Obsidian `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/pyproject.toml) · [Obsidian changelog](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/CHANGELOG.md)

### Inferences for this project

- Treat the PRD plugin manifest as a **versioned public contract**, not optional docs decoration.
- Validate manifests in CI against JSON Schema/Pydantic, including stable plugin ID, category, entry point, contract version, permissions, data egress, secrets/API keys, local-only support, setup estimate, capabilities, maturity, maintainers, license and documentation URL.
- Generate the plugin catalog, advisor cards, documentation tables and compatibility matrix from the same manifest to prevent drift.
- Registry publication should reject placeholder ownership fields, missing changelog/release provenance, undeclared network access and ambiguous license data.

---

## 4. Tests, compatibility and version/release strategy

### Observed facts

1. **Tests are package-local.** Core has a broad `tests/` tree; each integration may have its own tests. The Obsidian integration tests inheritance plus source-specific semantics such as file metadata, wikilinks, tasks and backlinks. [core tests](https://github.com/run-llama/llama_index/tree/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/tests) · [Obsidian tests](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/tests/test_readers_obsidian.py)

2. **The development tool performs affected-package testing.** `llama-dev test` maps changed files to packages, computes packages whose declared dependencies point to changed packages, and tests both changed packages and dependants in parallel. It skips incompatible Python versions and packages without tests. [test runner](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/test/__init__.py) · [dependency graph helpers](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/utils.py)

3. **PR CI tests Python 3.10–3.12 and separately tests core on 3.14.** A coverage workflow runs changed-package tests with diff coverage configured at 50%. The contribution guide instructs integrations with remote systems to mock them. [unit-test workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/unit_test.yml) · [coverage workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/coverage_check.yml) · [contribution guide](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/CONTRIBUTING.md)

4. **No ecosystem-wide integration conformance suite was found at this snapshot.** The inspected CI invokes each package's own pytest suite; a repository code search for `conformance` under `llama-index-integrations` returned no result. Therefore LlamaIndex's tests demonstrate inheritance and provider behavior, but do not provide the PRD's common plugin contract suite. This is a bounded negative finding, not proof that no unpublished checks exist. [test runner](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/test/__init__.py) · [GitHub code search](https://github.com/search?q=repo%3Arun-llama%2Fllama_index+conformance+path%3Allama-index-integrations&type=code)

5. **Core/umbrella versions move together; integrations version independently.** At researched HEAD, the umbrella and core are both `0.14.24`; the release helper bumps both together and rewrites the umbrella's compatible core range. In contrast, observed integration versions include Obsidian `0.8.0` and Mem0 `2.1.0`, each declaring its own core compatibility range. [root metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/pyproject.toml) · [core metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/pyproject.toml) · [release preparation](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/release/prepare.py)

6. **Independent subpackages publish on package-metadata changes.** The subpackage workflow finds changed integration `pyproject.toml` files, builds and publishes versions missing from PyPI, and can scan all packages in manual recovery mode. Core has a separate release path that runs core tests, builds provenance attestations for bundled static assets, publishes core, waits for PyPI, then publishes the umbrella package and creates a GitHub release. [subpackage publishing](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/publish_sub_package.yml) · [core/umbrella release](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/release.yml)

7. **The starter dependency surface and docs can drift.** The current root `pyproject.toml` directly depends on core, OpenAI LLM, OpenAI embeddings and NLTK; the official installation page additionally lists `llama-index-readers-file` in the starter bundle. This report treats the pinned package metadata as the build source of truth and records the docs mismatch as a maintenance warning. [root `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/pyproject.toml) · [installation docs](https://developers.llamaindex.ai/python/framework/getting_started/installation/)

### Inferences for this project

- Maintain **core contract version** separately from plugin package version. A plugin manifest should declare a supported contract range even if core package releases faster.
- Test changed packages and dependants, but add what LlamaIndex lacks: a shared conformance suite parametrized by plugin category.
- Networked provider tests should default to deterministic fakes/fixtures; a separate opt-in integration job can exercise live services with secrets.
- Publishing should require an explicit version/changelog change and manifest validation. Do not infer release intent solely from any `pyproject.toml` edit.
- A starter bundle must be local-first and no-key. Cloud/model-provider integrations should be explicit extras, never surprise dependencies.

---

## 5. Community contribution path and governance

### Observed facts

1. Existing core and integration packages accept fixes, refactors, documentation and tests through normal fork/branch/PR flow. The project uses `uv`, pre-commit, package-local editable environments and pytest. [contribution guide](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/CONTRIBUTING.md)

2. The repository explicitly states that it no longer accepts **new** integration packages. New integrations should live in their own repositories and be independently published to PyPI. [contribution guide](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/CONTRIBUTING.md)

3. Enforcement is automated: a `pull_request_target` workflow inspects added files ending in `pyproject.toml`, comments on the PR and closes it. [close-new-integration workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/close_new_integration_prs.yml)

4. The retired `run-llama/llama-hub` repository was archived in 2024 after integrations moved into the main monorepo. The present policy has now moved new packages back outside the main monorepo, showing that integration-governance topology changes as scale and maintenance cost change. [archived LlamaHub README](https://github.com/run-llama/llama-hub/blob/main/README.md)

### Inferences for this project

- Define governance early:
  - **official flagship integrations**: owned and released from the main monorepo;
  - **verified community integrations**: external repositories, registry listing after conformance/security/metadata checks;
  - **unverified local plugins**: installable by explicit user choice but not promoted by the advisor.
- A `plugin-template/` and reusable conformance package matter more than accepting all plugin source into the core repository.
- Registry admission and source-code hosting should be independent decisions. A plugin can appear in the registry without transferring maintenance ownership to the core team.
- Require a named maintainer, support policy and provenance for verified status; avoid the metadata decay visible in long-tail packages.

---

## 6. What to borrow—and what not to borrow—for the MVP

### Suitable patterns

| Pattern | Why it fits this PRD | MVP application |
|---|---|---|
| Stable contracts in core, concrete adapters outside | Protects canonical truth while allowing provider choice | Define the six PRD plugin interfaces in core; ship built-in implementations behind the same contracts |
| One-way provider dependency on core | Prevents core from becoming provider-coupled | CI import-layer check; no concrete backend imports in core |
| Selective installs plus a starter bundle | Supports progressive disclosure and low setup burden | Local-first starter; optional extras/distributions for Mem0, Graphiti, Obsidian, etc. |
| Independent plugin versions with core compatibility range | Lets adapters release fixes without forcing a core release | Manifest fields `plugin_version`, `contract_version`, `requires_core` |
| Package-owned metadata drives generated docs | Reduces manual catalog drift | Generate advisor cards, docs and registry records from one validated manifest |
| Change-aware tests of dependants | Scales monorepo CI | Build dependency graph from package metadata and run impacted packages |
| Source-specific semantic tests | Matches flagship-plugin quality bar | MarginNote fixtures must test hierarchy, annotations, incremental updates and provenance |
| External community packages at ecosystem scale | Limits maintainer burden | Keep verified community plugins external after the official template stabilizes |

### Patterns not suitable for this MVP

| Upstream pattern / condition | Why not copy it |
|---|---|
| 606 separately published integrations from day one | Operational complexity would dominate the product before contracts are proven |
| Main top-level package as a shared community namespace | Namespace mistakes/collisions can break imports; ownership and security boundaries are weak |
| Implicit importability as plugin discovery | Does not express enabled state, permissions, privacy or advisor metadata |
| Thin `[tool.llamahub]` metadata | Cannot power PRD §12/§26 capability and experience requirements |
| Integration-to-integration dependencies by default | Creates surprising transitive installs and blurs provider boundaries |
| Package-local tests without common conformance tests | Cannot guarantee interchangeable providers |
| Heavy core dependency footprint | Conflicts with a small, auditable, no-extra-key MVP |
| OpenAI-oriented starter defaults | Conflicts with the required no-extra-API-key path and user-controlled providers |
| Automatic publish inferred from `pyproject.toml` changes | Too easy to publish accidentally; explicit release intent is safer |
| Copying LlamaIndex `BaseMemory` as the product contract | It lacks provenance, temporal facts, promotion/review and permissions required by this PRD |

---

## 7. ADR implications

The following are implications to carry into architecture ADRs; they are not final decisions in this research note.

| Candidate ADR | Proposed direction | Evidence / reason |
|---|---|---|
| Core vs integration boundary | Core owns canonical models, evidence/provenance, temporal rules, permissions, contract protocols, registry validation and minimal local providers; integrations own source/backend/vendor I/O | LlamaIndex proves the one-way boundary works, but its large core shows “core” can contain real behavior |
| Python packaging topology | MVP may use a monorepo with separately buildable official packages, but avoid hundreds of distributions until demand exists | LlamaIndex's package count and later rejection of new monorepo integrations show scaling cost |
| Plugin discovery | Use `importlib.metadata` entry-point groups for installed plugins; use project manifest for metadata; require explicit enablement | PyPA-standard discovery is more precise than namespace scanning; LlamaIndex has no general runtime registry |
| Import namespace | Keep core import package regular and core-owned; community plugins use independent import packages and entry points | Avoid a plugin breaking the main namespace, per PyPA warning |
| Manifest schema | One versioned manifest is canonical for runtime validation, docs, advisor and registry | LlamaIndex's docs generation is useful; its metadata is too thin |
| Dependency policy | Core ← plugin only; plugin-to-plugin edges exceptional and declared | Obsidian's OpenAI integration dependency illustrates surprise coupling risk |
| Compatibility/versioning | Plugin SemVer independent of core; explicit core/contract ranges; deprecation window for contract changes | Mirrors independent integrations while decoupling API contract from release cadence |
| Test policy | Category-specific conformance suite + plugin semantic tests + impact analysis + offline default | Combines LlamaIndex's strongest testing patterns with the PRD's missing guarantee |
| Distribution channels | Main repo for official flagship plugins; external repos for community packages; registry verification independent of hosting | Aligns with LlamaIndex's current contribution policy without abandoning discoverability |
| Starter install | Local/no-key defaults only; cloud/provider packages opt-in | Corrects LlamaIndex's OpenAI-oriented starter for this product's privacy promise |
| Backend-native memory | Adapters may delegate storage/retrieval to Mem0/Graphiti, but canonical evidence and promotion rules remain core-owned | LlamaIndex Mem0 adapter is a useful composition precedent; its contract is too narrow to own product truth |

### Recommended dependency shape

```text
canonical schemas + policy + evidence + temporal model
                         │
                  plugin contracts
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
 built-in local     official adapters   community adapters
 providers          (separate pkg)      (external pkg)
       │                 │                  │
       └──────────── entry point + manifest ┘
                         │
              explicit user enablement
                         │
          registry/advisor/docs generated view
```

No plugin may mutate canonical files except through validated core operations. Discovery never equals authorization.

---

## 8. Proof-of-concept spikes

### S1 — Installed-plugin discovery and safe activation

**Question:** Can two separately built wheels register provider factories and rich manifests without sharing the core namespace?

**Prototype:** core package + two toy plugin wheels using one project-specific `[project.entry-points]` group; enumerate with `importlib.metadata.entry_points()`, validate manifest before loading, and require explicit enablement.

**Pass criteria:**

- discovery works in clean Python 3.10–3.14 environments;
- metadata can be inspected without importing provider/vendor SDKs;
- duplicate IDs and incompatible contract ranges fail deterministically;
- a broken plugin cannot prevent importing core;
- disabled plugin code is never imported.

### S2 — Namespace-package comparison

**Question:** Is a shared import namespace worth its ergonomics for official packages?

**Prototype:** compare two official toy packages under a PEP 420 namespace with the entry-point/independent-package design from S1; intentionally add a conflicting `__init__.py` distribution.

**Pass criteria:** document failure modes, wheel contents, IDE/type-checker behavior and uninstall behavior. Default to independent import packages unless the namespace option has a material user benefit.

### S3 — Contract conformance harness

**Question:** Can one reusable test package enforce behavior for `SourceProvider`, `MemoryProvider` and `RetrieverProvider` without over-constraining implementations?

**Prototype:** pytest contract fixtures for the built-in provider plus one fake external package; include sync/async behavior, stable IDs, provenance, incremental update/delete, permission denial, deterministic serialization and error taxonomy.

**Pass criteria:** a conforming external plugin passes without access to core internals; seeded broken implementations fail with actionable messages; live network is unnecessary.

### S4 — Manifest-to-registry/docs generation

**Question:** Can one manifest power runtime validation, the Plugin Advisor and public documentation?

**Prototype:** JSON Schema or Pydantic model; generate catalog JSON and a Markdown integration page; validate license, API-key, network, local-only, setup-time, capability, maturity and maintainer fields.

**Pass criteria:** generated artifacts are reproducible; placeholder authors and undeclared egress fail CI; schema migrations are versioned; docs cannot silently diverge from package metadata.

### S5 — Version compatibility matrix and release gate

**Question:** How should independent plugin versions relate to core and contract versions?

**Prototype:** build core N/N-1 plus toy plugins declaring compatible/incompatible ranges; exercise installation resolution and runtime manifest checks; dry-run release automation.

**Pass criteria:** incompatible combinations fail before provider execution; one plugin patch can release without a core bump; release requires explicit version + changelog + manifest validation.

### S6 — Native backend memory adapter seam

**Question:** Can a backend-native episodic memory mechanism be reused without surrendering canonical evidence, temporal facts and promotion policy?

**Prototype:** fake Mem0-like backend adapter that returns backend records while core separately stores provenance and candidate deltas; run add/search/delete/replay and backend-unavailable scenarios.

**Pass criteria:** canonical state can be reconstructed without treating backend summaries as truth; backend IDs/version data are preserved; provider swap does not change public context API semantics; all writes pass core validation.

### Suggested order

`S1 → S4 → S3 → S5 → S6`; run `S2` only if shared-namespace ergonomics remain desirable. S1/S4/S3 answer the highest-risk architectural questions before production code.

---

## 9. Source index

### Official LlamaIndex repository and release sources

- [Pinned repository commit](https://github.com/run-llama/llama_index/commit/c60937d3099b89e66ff9040f1c45030bc4e407e9)
- [Pinned recursive Git tree](https://api.github.com/repos/run-llama/llama_index/git/trees/c60937d3099b89e66ff9040f1c45030bc4e407e9?recursive=1)
- [Repository README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/README.md)
- [Root umbrella `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/pyproject.toml)
- [Core `pyproject.toml`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/pyproject.toml)
- [Integrations README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/README.md)
- [Contribution guide](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/CONTRIBUTING.md)
- [`v0.14.24` release](https://github.com/run-llama/llama_index/releases/tag/v0.14.24)

### Core and integration source evidence

- [`BaseReader`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/readers/base.py)
- [`BaseRetriever`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/base/base_retriever.py)
- [`BaseMemory`](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/memory/types.py)
- [reader loader](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/readers/loading.py)
- [embedding loader](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-core/llama_index/core/embeddings/loading.py)
- [Obsidian integration metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/pyproject.toml)
- [Obsidian tests](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/readers/llama-index-readers-obsidian/tests/test_readers_obsidian.py)
- [Mem0 integration metadata](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/memory/llama-index-memory-mem0/pyproject.toml)
- [Mem0 adapter implementation](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-index-integrations/memory/llama-index-memory-mem0/llama_index/memory/mem0/base.py)

### Development, CI and release sources

- [`llama-dev` README](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/README.md)
- [`llama-dev` discovery/dependency helpers](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/utils.py)
- [`llama-dev` test runner](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/llama-dev/llama_dev/test/__init__.py)
- [unit-test workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/unit_test.yml)
- [coverage workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/coverage_check.yml)
- [subpackage publishing workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/publish_sub_package.yml)
- [core/umbrella release workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/release.yml)
- [new-integration closure workflow](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/.github/workflows/close_new_integration_prs.yml)
- [docs API-reference generator](https://github.com/run-llama/llama_index/blob/c60937d3099b89e66ff9040f1c45030bc4e407e9/docs/scripts/prepare_for_build.py)

### Official documentation / standards

- [LlamaIndex installation and setup](https://developers.llamaindex.ai/python/framework/getting_started/installation/)
- [LlamaIndex integrations page](https://developers.llamaindex.ai/python/framework/community/integrations/)
- [PyPA: packaging namespace packages](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/)
- [PyPA: creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)

---

## Confidence and open gaps

### High confidence

- repository/package topology at the pinned SHA;
- core vs concrete integration dependency direction;
- namespace import layout;
- monorepo package discovery logic;
- test-impact logic, version examples and release workflows;
- current policy rejecting new integration packages.

### Medium confidence / bounded negative findings

- "no general runtime registry" is based on representative package metadata, loaders and repository code search at the pinned snapshot. A separate private registry service could exist outside this repository.
- "no common conformance suite" is based on repository paths, CI implementation and code search; it does not rule out unpublished maintainer checks.
- exact integration count is source-tree-specific and will change. Preserve the SHA whenever quoting `606`.

### Questions intentionally deferred to ADR/PoC

- Whether official packages should share a PEP 420 namespace or use independent import packages.
- Whether the MVP should publish multiple wheels immediately or keep separately buildable packages unreleased until Milestone 2/3.
- Registry trust levels, signing/attestation policy and revocation mechanics.
- The minimum stable surface of each of the six PRD plugin categories.

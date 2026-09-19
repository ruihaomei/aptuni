# Upstream Research: local retrieval, packaging and plugin discovery

> Researched 2026-09-18 · PRD refs: §11–§12, §18, §30, §42–§43, §48, §51

## TL;DR

- Use ordinary Python protocols/ABCs for provider contracts and
  [`importlib.metadata.entry_points()`](https://docs.python.org/3/library/importlib.metadata.html#entry-points)
  for discovery of independently installed plugins. This is a standard-library mechanism; Pluggy
  is unnecessary until the project actually needs multi-implementation hook dispatch.
- Do not split the MVP into many publishable workspace packages merely to match PRD §42. Start with
  one installable `src/` package and explicit internal provider modules, while making the public
  contract and entry-point group extraction-ready.
- SQLite FTS5 `unicode61` is good for Latin-script word search but treats a contiguous Chinese run
  as one token. FTS5 `trigram` makes CJK substring search workable for queries of at least three
  Unicode characters, but two-character queries do not match through `MATCH` and English substring
  behavior is noisier than word search.
- The zero-extra-key path needs a deterministic bilingual lexical spike. The strongest MVP candidate
  is a dual representation: `unicode61` word text plus application-generated CJK n-gram lexemes,
  with original text stored separately for display/provenance.

## Sources and environment

- [Python `importlib.metadata` documentation](https://docs.python.org/3/library/importlib.metadata.html)
- [PyPA guide: creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
- [PyPA entry-points specification](https://packaging.python.org/en/latest/specifications/entry-points/)
- [uv workspace documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [SQLite FTS5 documentation](https://www.sqlite.org/fts5.html)
- Local experiment: Python 3.13.3 linked to SQLite 3.53.2 with `ENABLE_FTS5=1`; system `sqlite3`
  CLI 3.51.0. `uv` was not installed on this host at research time.

## Packaging and plugin discovery

### Verified facts

Python's `importlib.metadata` discovers metadata for **installed distributions** and exposes
entry-point groups. An entry point has a `name`, `group`, object-reference `value`, and `.load()`.
Distribution names and import package names are not necessarily identical.

The PyPA guide documents three plugin-discovery approaches: naming conventions, namespace
packages, and package metadata. It explicitly shows metadata entry points for separately distributed
plugins. The PyPA entry-point specification is build-backend independent.

uv workspaces provide:

- a `pyproject.toml` per member;
- one shared lockfile;
- editable dependencies between members;
- `uv run --package`/`uv sync --package` targeting;
- one intersected `requires-python` range and one shared environment by default.

uv warns that workspaces do not provide dependency isolation between members, and recommends not
using them when members need conflicting requirements or separate environments.

### Architectural inference

Entry points are a better MVP discovery primitive than either import-name scanning or namespace
packages:

- they advertise an explicit contract category and identifier;
- third-party packages need not live under the core import namespace;
- plugin metadata can be inspected before loading plugin code;
- the core can reject duplicate IDs or incompatible contract versions deterministically.

An entry-point group shape can eventually be:

```toml
[project.entry-points."<namespace>.source_providers"]
zotero = "vendor_zotero.plugin:plugin"
```

`<namespace>` is intentionally unresolved until the codename/import-name ADR. Loading arbitrary
installed entry points executes third-party Python code, so discovery and activation must remain
separate: list/validate metadata first; import only enabled plugins.

Pluggy would add value only if the contract becomes a hook relay with multiple implementations per
call, ordering, wrappers, historic calls, or first-result semantics. The current PRD describes typed
providers selected by Recipe/configuration; standard protocols plus entry points are sufficient.

### Recommendation

For Milestone 1:

1. one installable Python distribution with `src/<namespace>/`;
2. internal modules for core, CLI, MCP and built-in providers;
3. provider contracts that do not import implementation packages;
4. entry-point discovery behind a small registry interface;
5. a fixture third-party plugin distribution used only in contract tests;
6. postpone a multi-member uv workspace until at least two packages genuinely need independent
   release/dependency boundaries.

This preserves the LlamaIndex-style ecosystem seam without paying monorepo/package overhead before
it creates user value.

## Bilingual SQLite FTS5

### What the built-in tokenizers do

SQLite documents four built-in FTS5 tokenizers:

- `unicode61` (default): each contiguous run of Unicode letters/numbers/private-use characters is
  one token; punctuation/space separates tokens; Latin diacritics are removed by default;
- `ascii`;
- `porter`, intended for English stemming;
- `trigram`, which indexes each contiguous three-character sequence for substring matching.

Consequently, `unicode61` does not segment a sentence written without spaces in Chinese. This is
not a bug in our environment; it follows its documented contiguous-run rule.

SQLite's documented trigram limitations matter:

- `MATCH` substrings shorter than three Unicode characters produce no rows;
- indexed `LIKE`/`GLOB` is supported under documented option constraints, but short wildcard
  patterns may fall back to a linear scan;
- `detail=none`/`detail=column` impose query-token limitations that need benchmarking before use.

### Reproducible local probe

Input row:

```text
机器学习和生存分析 personal memory retrieval
```

Observed results:

| Tokenizer/query | `unicode61 MATCH` | `trigram MATCH` |
|---|---:|---:|
| `机器学习` | no | yes |
| `机器` | no | no |
| `生存分析` | no | yes |
| `memory` | yes | yes |
| `memo` | no | yes |

`LIKE '%机器%'` returned the row for both tables, but the query plan identified the unicode61 path
as a virtual-table scan; the trigram path used its LIKE index marker. Results and query plans must be
re-tested on the minimum supported SQLite build, not only the maintainer's machine.

### Candidate designs

#### A. Trigram-only FTS

**Pros:** built into modern SQLite; handles mixed Chinese/English substring search; no model or
tokenizer dependency. **Cons:** two-character CJK gap, noisier substring semantics for English,
larger index, and ranking differs from word retrieval.

#### B. `unicode61` plus deterministic application-level CJK n-gram lexemes

Store original text outside the generated lexical column. For each contiguous CJK run, produce
overlapping bigrams (and optionally trigrams) separated by spaces; preserve Latin word tokens.

**Pros:** pure Python + built-in FTS5, supports two-character terms, deterministic/offline, easy to
rebuild as a projection. **Cons:** not linguistic segmentation; generated query/document lexemes
must use identical versioned normalization; index growth and ranking need evaluation.

#### C. Jieba or another segmentation dependency

**Pros:** more word-like Chinese tokens. **Cons:** additional dependency and dictionaries, domain
vocabulary drift, update/reproducibility questions, and still needs fallback for unknown terms.

#### D. Native SQLite tokenizer extension

**Pros:** strongest integration/performance potential. **Cons:** violates the MVP's light,
cross-platform zero-friction direction and increases distribution/security burden.

### Recommendation pending spike

Spike **B** against **A**, not C/D, using a small bilingual retrieval fixture. Select the simpler
design only after measuring:

- exact and partial CJK recall, including two-character concepts;
- English word precision versus substring false positives;
- mixed-language queries;
- index size and sync latency;
- BM25 ranking stability;
- minimum supported macOS/Linux/Windows Python SQLite capabilities.

The lexical index remains a rebuildable projection. Neither generated lexemes nor FTS rows are
canonical Profile facts.

## ADR implications

1. Plugin discovery: standard Python entry points plus typed provider contracts; no Pluggy in MVP.
2. Packaging: one distribution initially; package extraction is permitted only behind stable
   contracts and requires its own ADR when introduced.
3. Environment management: uv may be the contributor workflow and lockfile manager, but choosing a
   uv workspace is separate from choosing uv itself.
4. Retrieval: accept FTS5 as the zero-key baseline only after bilingual/minimum-version spike;
   expose tokenizer/index version so projections can be rebuilt safely.
5. Security: plugin discovery must not imply automatic import/activation of every installed entry
   point.

## PoC spikes

- **P1 — entry-point contract:** build a core registry and one fixture plugin wheel; test discovery,
  duplicate IDs, incompatible contract version, disabled plugin not imported, and failure isolation.
- **P2 — package shape:** compare one-package install/test commands with a two-member uv workspace;
  choose the smallest shape that still validates external plugin installation.
- **R1 — bilingual lexical retrieval:** benchmark trigram-only vs deterministic CJK n-gram lexemes
  on a checked-in EN/zh-CN query corpus.
- **R2 — SQLite floor:** run capability tests on every supported OS/Python pair and produce a clear
  setup error or fallback when FTS5/trigram is unavailable.

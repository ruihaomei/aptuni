# Plugin platform friction found while building Top-Down Learning

Recorded 2026-09-27 while refining Flagship Plugin #1 (ADR-0026). Each item says whether it was
fixed in the plugin, is a general platform gap, or needs no change. None required a Core change for
the Beta; they are candidates for a later public-API slice with independent review.

| Area | Friction | Status |
|---|---|---|
| Task-scoped retrieval | `query_context` does exact-token FTS with AND semantics and no stemming: `explanation` misses "explanations" and a multi-word preference query returns nothing. The plugin issues one query per evidence term and eight single-token preference queries, then filters locally. | Platform gap: an OR/any-term mode or a bounded "list relevant items in module X" call would cut calls and remove plugin-side lexicons. |
| Relevance vs evidence strength | Items expose `canonical_id`, `module` and `text` but no per-item support signal a plugin can use to separate "mentions Python" from "demonstrated Python"; the plugin counts distinct negation-free records (≥2 strong, 1 familiar). | Platform gap: an evidence-strength or corroboration count on `ContextItem` would be reusable by every plugin. |
| Capability/grant declarations | No way to declare an optional module (for example `goals` for learning targets) without making it required in the grant. | Platform gap; not needed for the Beta flagship. |
| Portable context | Every plugin that exports personal context needs redaction of paths, emails, credentials and tokens. Implemented in the plugin (`portable.py`). | Candidate public helper once a second plugin needs it. |
| Verification of user confirmation | A stdio MCP tool cannot tell a human reply from a model-written one (ADR-0025). The plugin binds confirmation to a content digest and rejects negative/corrective replies. | Accepted boundary; documented. |
| Host plugin invocation | Claude user-only frontmatter is invalid in a Codex skill, so the shared workflow body is duplicated into two thin wrappers with a parity test. | Works; a generator could remove the duplication. |
| Developer tooling | Checking the standalone plugin needs `MYPYPATH=src:examples/plugins/top_down_learning/src mypy --strict -p top_down_learning`, and the Codex validators need PyYAML (`uv run --no-project --with pyyaml`). | Documented here; a `aptuni developer check` command would help plugin authors. |
| Packaging | A manifest version bump changes the grant digest, so an upgraded plugin needs a new owner grant. This is correct but surprising. | Needs no change; say so in upgrade notes (done in the plugin README). |

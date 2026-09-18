# S00 Result — Development Namespace and License Boundary

- **Date:** 2026-09-18
- **Result:** development namespace resolved; public brand and license remain maintainer decisions

## Development namespace

Use the deliberately descriptive temporary distribution name `personal-context-core` and import
namespace `personal_context_core` until the public brand workflow is complete.

Collision probe on 2026-09-18:

```text
GET https://pypi.org/pypi/personal-context-core/json → 404
GitHub repository search: "personal-context-core in:name" → total_count 0
```

The checks show no exact collision at that moment; they do not create a reservation or establish
trademark clearance. Re-check immediately before publication. Internal code must not embed this as a
user-facing brand. A future rename requires a planned package/import migration before stable public
API guarantees.

## License boundary

Current inspected upstream licenses include Apache-2.0 (Mem0, Graphiti, Codex) and MIT
(LlamaIndex, MCP Python SDK). The project will depend on/adapt these projects rather than copy their
source. This does not determine the project's own license.

ADR-0009 proposes Apache-2.0, but the maintainer must confirm it. Lack of a public license does not
block private/local Phase 0 or Milestone 1 engineering; it blocks public release, accepting external
contributions, and representing the repository as open source. Do not add a placeholder LICENSE.

## Reproducibility

```sh
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://pypi.org/pypi/personal-context-core/json
gh api -X GET search/repositories \
  -f 'q=personal-context-core in:name' -f per_page=5 \
  --jq '{total_count, names: [.items[].full_name]}'
```

## ADR impact

- ADR-0002 can use the temporary namespace for scaffolding; public naming remains out of scope.
- ADR-0009 stays Proposed and is a release/contribution gate, not a local engineering gate.

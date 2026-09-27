# Aptuni Developer API v1

`aptuni.api.v1` is Aptuni's supported Python extension boundary. It exposes task-oriented context,
not storage primitives. Everything under `aptuni.application`, `aptuni.domain`, `aptuni.vault`,
`aptuni.retrieval`, `aptuni.policy`, and `aptuni.sources` is internal.

## Capabilities

| Capability | Public operation | Guardrail |
|---|---|---|
| `profile.read` | `get_profile` | bounded exposed L0 identity only |
| `memory.read` | `search_memories` | only current exposed Memory rows are returned |
| `context.read` | `query_context` | exact granted modules; current exposure policy |
| `evidence.read` | `query_context(..., include_evidence=True)` | also requires `context.read`; minimized Evidence only |
| `memory.propose` | `propose_memory` | protected-content filter, ingest policy, quarantine and owner review |
| `memory.review.read` | `pending_memory_reviews` | read-only bounded queue; no decision method |

The API has no direct Vault, projection, source, permission, deletion, Fact-write or owner-review
decision method. Results use immutable `aptuni.api@1` models and preserve canonical IDs, source
provenance, trust, taint, review state, Vault sequence, policy epoch and response budgets.

## Connect

First validate and authorize an exact local manifest from the owner's terminal:

```sh
aptuni developer inspect ./aptuni-plugin.toml
aptuni developer grant plan ./aptuni-plugin.toml \
  --capability context.read --module knowledge
aptuni developer grant apply act-0123456789abcdef
```

The last command shows the exact plugin/version/capabilities/modules and requires `APPLY`. It does
not import or execute plugin code. The preview expires after ten minutes and is consumed on apply.
Audit or remove authority with:

```sh
aptuni developer grant list
aptuni developer grant cancel act-0123456789abcdef
aptuni developer grant revoke grant-0123456789abcdef
```

Then the plugin host loads its own code and connects the exact manifest to the returned grant:

```python
from pathlib import Path

from aptuni.api.v1 import connect, load_manifest

manifest = load_manifest(Path("aptuni-plugin.toml"))
api = connect(manifest, "grant-0123456789abcdef")
result = api.query_context(
    "What foundation matters for this task?",
    modules=("knowledge",),
    max_units=1500,
)
```

Manifest or version drift invalidates the grant. Module exposure can still narrow a valid grant at
read time, and module ingest can reject a valid proposal at write time. SDK operations and grant
changes are serialized across processes: an operation already in flight completes before revocation,
and once revoke or privacy purge completes the already-connected client is stopped without restart.
Applying the same preview concurrently or retrying after interrupted publication resolves to the
same single grant generation.

For new Agent plugins, declare the same capability set as required and optional intent:

```toml
[aptuni]
required = ["context.read"]
optional = ["memory.propose"]
```

Planning fails if an owner selection omits a required capability. Optional capabilities may be
withheld without invalidating the grant, and an attempted optional operation then fails with
`plugin_capability_denied`. Exact modules remain independently narrowed. The old top-level
`capabilities` field remains supported with its original digest and semantics, but cannot be mixed
with `[aptuni]`.

API v1 is an authorization protocol, not an activation runtime. Aptuni does not discover, import or
execute manifest entry points. A reviewed host is responsible for loading the client code and its
dependency closure.

## Compatibility

`aptuni.api.v1` and `aptuni.plugin@1` are additive-only within major version 1. Existing fields,
capability meanings and error codes will not be removed or redefined. A breaking change requires a
new major namespace/contract. New optional fields or capabilities may appear when old consumers
continue to validate and behave unchanged.

All expected failures are `AptuniAPIError` with a stable `code` and a human `message`. Do not parse
message text.

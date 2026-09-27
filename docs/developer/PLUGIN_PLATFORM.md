# Aptuni Plugin Platform

An Aptuni v1 plugin is a local Python SDK client with an `aptuni.plugin@1` manifest. The manifest
asks for authority; it grants none. An owner grant binds the exact manifest digest to a narrowed set
of capabilities and Profile modules.

## Create a plugin

```sh
aptuni developer scaffold ./my-plugin \
  --id dev.example.my_plugin \
  --name "My Plugin"
```

The generated project contains a strict TOML manifest, a declared `aptuni.plugins.v1` package entry
point, public-API-only starter, test and README. Scaffolding creates no Vault, grant, source access
or network permission. Aptuni v1 records but does not discover, import or execute that entry point;
the reviewed host loads its own client code.

New manifests declare:

- exact plugin id, semantic version, API version and entry point;
- required Aptuni context capabilities, optional capabilities and Profile modules;
- egress and retention behavior.

```toml
[aptuni]
required = ["context.read"]
optional = ["memory.read", "evidence.read"]
```

Required means the plugin cannot run under a grant that omits that capability. Optional authority
is owner-selectable. Both use the same public capability vocabulary and the same exact, revocable
grant; the declaration itself grants nothing. The legacy top-level `capabilities = [...]` form
remains valid for existing v1 plugins but cannot be mixed with `[aptuni]`.

V1 authorizes only `egress = ["none"]`. A plugin that sends personal context to a host model, cloud
API or source origin must use Aptuni's separately confirmed MCP/adapter egress path. A manifest is
not a sandbox: installed Python runs with the user's process privileges and is trusted code. Review
its source and complete dependency closure before running it. Automatic third-party-code activation
is outside API v1.

Grant previews expire after ten minutes and are consumed when applied. Use `aptuni developer grant
list` to audit grants, `grant cancel ACTION_ID` to discard a preview, and `grant revoke GRANT_ID` to
remove authority. Calls and grant changes are serialized; after revocation completes, an existing
client cannot start another authorized operation.

Invoking an approved Agent plugin does not require a separate Aptuni Profile/Memory/Full activation.
The reviewed plugin receives context only by making bounded public API calls under its exact grant
for the current task. Aptuni still does not discover or execute the entry point; the reviewed host
owns plugin loading.

## Review and memory boundaries

Plugins may submit a bounded memory proposal only when explicitly granted `memory.propose`. It is
stored as a host proposal, stays hidden, and requires owner review. Plugins cannot accept, reject,
pin, forget, promote or delete their own proposals through API v1.

Local SDK grant and pending-plan files appear in `aptuni privacy status`. A privacy purge revokes
the exact plugin grants and pending plans frozen into its preview; grants created after that preview
are not deleted by the older action.

## Flagship Plugin #1: Top-Down Learning

[`examples/plugins/top_down_learning`](../../examples/plugins/top_down_learning/) is Aptuni's first
flagship plugin and the reference for building a personalized product on the platform. It starts
from a learner's target and runs task-scoped retrieval under its exact grant. The learner verifies
a draft before any teaching begins, and learning then continues through a portable
`top_down_learning_context.md` (ADR-0026) that local and cloud Agents can both use. It imports only
`aptuni.api.v1`; Aptuni Core contains no learning special case.

Patterns worth reusing in other plugins:

- **Minimize before writing.** Query per concept and keep labels, levels and relevant lines; never
  copy raw items, canonical identifiers or provenance into plugin artifacts.
- **Separate stable and dynamic state.** Bind user verification to a digest of the stable part only.
- **Use Aptuni only where needed.** Keep every other step a pure transformation of user-owned
  state, so a delivery or export choice cannot widen authority.
- **Write explicitly.** Propose memory only on request, quarantined, with the capability optional.

Its Claude Code invocation is `/top-down-learning:top-down-study`; its Codex invocation is
`$top-down-study`. Both are manual-only and use the same no-egress STDIO tools.

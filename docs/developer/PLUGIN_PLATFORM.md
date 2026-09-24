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

The manifest declares:

- exact plugin id, semantic version, API version and entry point;
- requested capabilities and Profile modules;
- egress and retention behavior.

V1 authorizes only `egress = ["none"]`. A plugin that sends personal context to a host model, cloud
API or source origin must use Aptuni's separately confirmed MCP/adapter egress path. A manifest is
not a sandbox: installed Python runs with the user's process privileges and is trusted code. Review
its source and complete dependency closure before running it. Automatic third-party-code activation
is outside API v1.

Grant previews expire after ten minutes and are consumed when applied. Use `aptuni developer grant
list` to audit grants, `grant cancel ACTION_ID` to discard a preview, and `grant revoke GRANT_ID` to
remove authority. Calls and grant changes are serialized; after revocation completes, an existing
client cannot start another authorized operation.

## Review and memory boundaries

Plugins may submit a bounded memory proposal only when explicitly granted `memory.propose`. It is
stored as a host proposal, stays hidden, and requires owner review. Plugins cannot accept, reject,
pin, forget, promote or delete their own proposals through API v1.

Local SDK grant and pending-plan files appear in `aptuni privacy status`. A privacy purge revokes
the exact plugin grants and pending plans frozen into its preview; grants created after that preview
are not deleted by the older action.

## Flagship example

[`examples/plugins/top_down_learning`](../../examples/plugins/top_down_learning/) is a complete
contract pressure test. It reads granted goals, foundation and teaching preferences; derives a
plugin-owned prerequisite map for an intelligent parking system; alternates short explanation with
project action; checks learner output; advances or repeats; and optionally submits an explicit gap
for owner review. It imports only `aptuni.api.v1`; Aptuni core contains no learning special case.

# Top-Down Learning — Aptuni plugin MVP

This external-style example starts from a concrete target, reads only owner-granted Aptuni context,
derives the missing prerequisites, couples each explanation to a project action, checks learner
output, and advances or repeats. The included catalogue demonstrates an intelligent parking system;
other domains provide another tuple of `PrerequisiteTemplate` values without changing Aptuni core.

The plugin imports only `aptuni.api.v1`. It never opens the Profile Vault, reads sources, changes
permissions, accepts its own memory proposals, or stores raw conversations. `record_gap` is an
explicit action and produces a quarantined proposal for owner review.

Its `[aptuni]` manifest requires only `context.read`; `memory.propose` is optional. The complete
learning and learner-check journey therefore works when the owner withholds memory capture, while
`record_gap` fails closed. Invoking this plugin does not require a separate Aptuni activation: its
public API client receives only task-relevant context through the exact owner grant.

The Aptuni manifest is `src/top_down_learning/aptuni-plugin.toml`. Inspect and grant that exact file
before configuring `APTUNI_TOP_DOWN_GRANT_ID` for the plugin MCP server.

## Install and authorize

From an Aptuni source checkout after the Beta version is selected:

```sh
uv tool install /path/to/aptuni
uv tool install /path/to/aptuni/examples/plugins/top_down_learning \
  --with-editable /path/to/aptuni
aptuni developer inspect /path/to/aptuni/examples/plugins/top_down_learning/src/top_down_learning/aptuni-plugin.toml
aptuni developer grant plan /path/to/aptuni/examples/plugins/top_down_learning/src/top_down_learning/aptuni-plugin.toml
aptuni developer grant apply ACT_ID
export APTUNI_TOP_DOWN_GRANT_ID=GRANT_ID
```

The plan grants the required `context.read` plus optional `memory.propose` by default. To withhold
memory capture, add `--capability context.read` to `grant plan`. No separate Aptuni Profile, Memory,
or Full activation is needed when the skill runs; the plugin's exact grant is its only authority.

## Invoke in Claude Code

```sh
claude --plugin-dir /path/to/aptuni/examples/plugins/top_down_learning/claude
```

Invoke `/top-down-learning:top-down-study`, then give one concrete goal. The Claude skill is
user-only and has no automatic session hook.

## Invoke in Codex

Install the repository skill and MCP entry in the project where you want to learn:

```sh
mkdir -p .agents/skills
cp -R /path/to/aptuni/examples/plugins/top_down_learning/skills/top-down-study .agents/skills/
codex mcp add top_down_study \
  --env APTUNI_TOP_DOWN_GRANT_ID="$APTUNI_TOP_DOWN_GRANT_ID" \
  -- top-down-study-mcp
```

If `APTUNI_STATE_DIR` is not the default, add it with another `--env`. Invoke `$top-down-study` and
give one concrete goal. Codex metadata disables implicit invocation.

Both hosts call the same three MCP tools. Learning progress remains bounded host task state; the
plugin writes no transcript or session file. Revoking the grant stops the next tool call.

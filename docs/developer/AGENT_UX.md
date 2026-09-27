# Aptuni Agent UX

Aptuni starts OFF for ordinary Agent tasks. Through the official activation-required integration,
OFF means no new Profile, Memory or Evidence retrieval, no new Aptuni memory capture, and no further
Aptuni disclosure until Aptuni is reactivated through one of three modes:

| Mode | Meaning | Default scope |
|---|---|---|
| Profile | Know me — relevant stable Profile, preferences, skills, knowledge and goals | current task |
| Memory | Remember our work — relevant interaction/project Memory | current task |
| Full | Use everything relevant — permitted Profile + Memory + minimized Evidence | current task |

Full still uses retrieval relevance, module exposure, the exact host grant and response budgets. It
never dumps the Vault.

## Claude Code

The generated Claude bundle is a native Claude Code plugin. Load or install the bundle, then invoke:

```text
/aptuni:profile
/aptuni:memory
/aptuni:full
```

Each is task-scoped. To opt in for the current Claude Code session, invoke `/aptuni:full` and say
“for this session.” Use `/aptuni:session` to inspect the current session mode or turn Aptuni off.
The bundle has no SessionStart personal-context hook.

For a generated bundle at `BUNDLE`, a development smoke can load it with:

```sh
claude --plugin-dir BUNDLE
```

## Codex

The generated Codex bundle uses repository Agent Skills. Install its `.agents/skills/` directory
and merge the generated MCP stanza from `config.toml` into the trusted project configuration, then
invoke:

```text
$aptuni-profile
$aptuni-memory
$aptuni-full
```

Each is task-scoped. Say “for this session” while invoking `$aptuni-full` for explicit session Full.
Use `$aptuni-session` to inspect or disable it.

## Host-independent contract

The host spellings above are only adapter UX. Both map to `aptuni.profile`, `aptuni.memory`, or
`aptuni.full`. Task activation performs one bounded retrieval and stores no activation state. Only
Full may be session-scoped; the state lives in that MCP process, begins OFF, and disappears when the
process ends. Revocation, module policy, exposure policy and privacy cleanup are revalidated live.

Task scope prevents later Aptuni retrieval; it does not erase context already retained by Claude
Code or Codex in the current conversation transcript, and disabling or revoking Aptuni cannot recall
information already delivered to that capable host. Start a new host task, chat or session before
unrelated work when strict transcript isolation matters.

Manual-only skills are an activation and UX safeguard. They reduce accidental activation, but they
are not a security boundary and do not prove that a human initiated a model-visible MCP tool call.
The capable host remains inside the trust boundary described by ADR-0013.

## Flagship Agent plugin: Top-Down Learning

The external-style Top-Down Learning package is in
`examples/plugins/top_down_learning/`. After its manifest is owner-granted, it receives context
through `aptuni.api.v1`; do not activate Aptuni Profile/Memory/Full separately.

- Claude Code: load its `claude/` plugin bundle and invoke
  `/top-down-learning:top-down-study`.
- Codex: install its repository skill plus MCP entry and invoke `$top-down-study`.

Both invocations are manual-only UX safeguards. The workflow starts from a concrete goal, returns
one missing prerequisite and project action, waits for active learner output, then repeats or
advances. Optional gap capture is a separate explicit action and remains quarantined for owner
review. Exact install and grant commands are in the plugin README.

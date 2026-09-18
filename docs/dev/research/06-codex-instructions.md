# Upstream Research: Codex instructions, skills, MCP and relay mechanics

> Researched 2026-09-18 · PRD refs: §20, §36–§40, §51 · Researcher: Codex takeover agent

## Snapshot and scope

- Local host: `codex-cli 0.153.4` from the ChatGPT desktop bundle.
- Upstream inspected: `openai/codex` commit
  [`7498521d288b9b3b96ffba4eedf089d8d6e06a84`](https://github.com/openai/codex/commit/7498521d288b9b3b96ffba4eedf089d8d6e06a84),
  committed 2026-09-18.
- Primary sources are current OpenAI documentation and the upstream Codex repository. Product
  behavior is version-sensitive; re-check it before shipping an adapter.

## Verified findings

### 1. `AGENTS.md` is the durable, hierarchical Codex contract

OpenAI documents the load order as:

1. global `$CODEX_HOME/AGENTS.override.md`, otherwise global `$CODEX_HOME/AGENTS.md`;
2. one instruction file per directory from repository root down to the working directory;
3. in each project directory, `AGENTS.override.md` wins over `AGENTS.md`, followed by configured
   fallback names;
4. files nearer the working directory are concatenated later and therefore take precedence.

Empty files are skipped. The documented default combined project-instruction budget is 32 KiB via
`project_doc_max_bytes`. Instructions are assembled at process/session start, so a restarted session
is the reliable way to pick up changes.

Sources:

- [OpenAI Docs — custom instructions with AGENTS.md](https://developers.openai.com/docs/agent-configuration/agents-md)
- [Codex global instruction loader at inspected commit](https://github.com/openai/codex/blob/7498521d288b9b3b96ffba4eedf089d8d6e06a84/codex-rs/codex-home/src/instructions/mod.rs)
- [Codex prompt representation for AGENTS.md](https://github.com/openai/codex/blob/7498521d288b9b3b96ffba4eedf089d8d6e06a84/codex-rs/core/src/context/user_instructions.rs)

**Implication:** the root `AGENTS.md` should contain only invariants and routing: product principles,
canonical commands, safety rules, definition of done, and where to read current state. Milestone
status, handoff prose, and long architecture explanations belong under `docs/dev/` and are linked,
not copied into every prompt.

### 2. Skills are progressively disclosed reusable workflows

Codex discovers repository skills under `.agents/skills` between the current working directory and
repository root. A skill is a directory with required `SKILL.md`; optional `scripts/`, `references/`,
`assets/`, and `agents/openai.yaml` provide executable support, detailed references, templates and
host/dependency metadata.

Codex can activate skills explicitly (`$skill-name`, or via `/skills`) or implicitly when the task
matches the skill description. The host initially exposes metadata rather than every skill body,
then loads the selected `SKILL.md` and only the needed references/scripts. Current documentation
states that the initial catalog is bounded to 2% of the model context window, or 8,000 characters
when the window is unknown.

Skills use the open Agent Skills format. Plugins are the installable distribution unit when skills
need to be shared beyond one repository or bundled with connectors.

Sources:

- [OpenAI Docs — build skills](https://developers.openai.com/docs/build-skills)
- [OpenAI Docs — customization overview](https://developers.openai.com/docs/customization/overview)
- [Upstream skill loader implementation](https://github.com/openai/codex/tree/7498521d288b9b3b96ffba4eedf089d8d6e06a84/codex-rs/ext/skills/src/loader)

**Implication:** PRD §39 workflows should become small, sharply triggered skills. Do not put full
workflow bodies into `AGENTS.md`. Cross-host reuse needs an explicit packaging decision because
Codex's repository location (`.agents/skills`) differs from Claude Code's (`.claude/skills`). The
portable common denominator is the Agent Skills schema, not either host's extra frontmatter.

### 3. Codex supports local STDIO and remote Streamable HTTP MCP servers

Current OpenAI documentation verifies:

- local STDIO servers with command, args and controlled environment variables;
- Streamable HTTP servers with bearer tokens or OAuth;
- project configuration at `.codex/config.toml` for trusted projects, or user configuration at
  `~/.codex/config.toml`;
- the desktop app, CLI and IDE extension on one Codex host share MCP configuration;
- server-level `instructions` returned during initialization are read by Codex; the first 512
  characters should be self-contained because they may be used for tool-selection guidance.

The local CLI exposes `codex mcp list|get|add|remove|login|logout`. The upstream source also defines
model-facing `list_mcp_resources`, `list_mcp_resource_templates`, and `read_mcp_resource` tools, so
Codex resource support is not merely inferred from the protocol.

Sources:

- [OpenAI Docs — MCP for Codex](https://developers.openai.com/docs/extend/mcp)
- [Codex MCP resource tool definitions at inspected commit](https://github.com/openai/codex/blob/7498521d288b9b3b96ffba4eedf089d8d6e06a84/codex-rs/core/src/tools/handlers/mcp_resource_spec.rs)

**Implication:** the product's MCP server should expose task-oriented tools as the compatibility
baseline. Resources can provide inspectable evidence/profile artifacts for Codex, but the core
workflow must not require a host to surface resources automatically. Host capability differences
belong in adapter conformance tests, not in canonical domain logic.

### 4. The repository, not a Codex session, must carry the relay

Codex can resume/fork its own sessions, but those session mechanisms do not create a portable relay
to Claude Code. The cross-vendor handoff therefore has to consist of versioned repository state:

- `AGENTS.md` for stable shared rules;
- `CLAUDE.md` importing `@AGENTS.md` plus Claude-only details;
- `docs/dev/STATE.md` for current truth;
- `docs/dev/HANDOFF.md` for short-lived operational context;
- ADRs for durable architecture decisions;
- tests and commits for executable evidence;
- host-specific skill discovery surfaces generated from or checked against common skill sources.

This conclusion is an architectural inference from the verified host mechanisms, not an OpenAI
product guarantee.

## Recommended harness contract

```text
AGENTS.md                         # concise shared invariant/routing contract
CLAUDE.md                         # @AGENTS.md + Claude-only notes
.agents/skills/                   # Codex discovery surface
.claude/skills/                   # Claude Code discovery surface
skills/ or tooling manifest       # optional canonical source; decide by ADR/spike
docs/dev/STATE.md                 # current milestone + validation status
docs/dev/HANDOFF.md               # short-lived continuation note
docs/dev/DECISIONS/               # durable decisions
docs/dev/KNOWN_ISSUES.md          # confirmed limitations
```

Avoid two independently edited copies of each skill. Decide whether the canonical source is a
shared directory with generated host surfaces, a packaging step, or deliberately small duplicated
wrappers around shared references/scripts.

## Assumptions and gaps

- **Not yet verified:** whether every intended Codex deployment surface exposes MCP prompts or
  sampling in a way useful to this product. Tool and resource support are verified; do not make the
  MVP depend on prompts or sampling.
- **Not yet verified:** behavior of project `.codex/config.toml` across local, worktree, and cloud
  tasks. Treat it as adapter configuration rather than user-owned canonical data.
- **Version skew:** the bundled local CLI (`0.153.4`) may not match documentation or upstream HEAD.
  Adapter conformance should record both host version and server version.
- **Security:** project MCP configuration executes or connects to external systems. Setup must show
  exact commands/URLs, required secrets, and trust consequences before enabling it.

## ADR implications

1. Accept root `AGENTS.md` as the shared development contract and keep it intentionally short.
2. Keep operational state out of `AGENTS.md`; route agents to `STATE.md`, `HANDOFF.md`, ADRs and
   relevant plans.
3. Define task-oriented MCP tools as the minimum host contract; resources are an enhancement.
4. Define a cross-host skill source/distribution strategy and test that both Codex and Claude Code
   discover the same workflow semantics.
5. Version the agent-adapter capability matrix; never assume all MCP hosts expose every protocol
   feature identically.

## PoC spikes

- **Harness discovery spike:** create a tiny shared rule plus one nested override; verify loaded
  instructions from the repository root and a nested directory in the installed Codex version.
- **Cross-host skill spike:** implement one no-op `run-evals` skill from a common source and verify
  explicit and implicit discovery in Codex and Claude Code without manually divergent bodies.
- **MCP capability spike:** a fixture server exposes one tool, one static resource, one resource
  template and one prompt; record what Codex CLI/Desktop, Claude Code, Cursor and Claude Desktop can
  list/call/read.
- **Relay spike:** stop midway through a fixture change, update only repository state, and confirm a
  fresh session in the other host can continue and reproduce validation without chat history.

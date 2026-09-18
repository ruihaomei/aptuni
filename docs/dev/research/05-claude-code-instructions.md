# Upstream Research: Claude Code instruction & extensibility mechanisms

> Researched 2026-09-18 · PRD refs: §36–§40 · Researcher: subagent (claude-code-guide)

## TL;DR

- **CLAUDE.md** loads hierarchically (managed policy → user → project → local) across directory tree; supports `@path` imports (relative, max 4 hops); **AGENTS.md** not natively read but import it via `@AGENTS.md` in CLAUDE.md. [[memory.md](https://code.claude.com/docs/en/memory.md)]
- **Rules in `.claude/rules/*.md`** load at launch (unconditional) or on demand (with `paths:` YAML frontmatter); symlinks + external imports supported. [[memory.md](https://code.claude.com/docs/en/memory.md)]
- **Skills (`.claude/skills/<name>/SKILL.md`)** use YAML frontmatter for `description`, `arguments`, `allowed-tools`, `disable-model-invocation`, `model`, etc.; Claude Code extends AgentSkills spec but only standard fields distribute outside Claude Code. [[skills.md](https://code.claude.com/docs/en/skills.md)]
- **Hooks** (~30 events: `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, `InstructionsLoaded`, etc.) configured in `.claude/settings.json` or plugin `hooks/hooks.json`; exit code 2 blocks, JSON output controls decisions. [[hooks.md](https://code.claude.com/docs/en/hooks.md)]
- **Plugins** bundle skills, agents, hooks, MCP servers via `.claude-plugin/plugin.json` manifest; install, version, test with `--plugin-dir`; distribute via marketplaces. [[plugins.md](https://code.claude.com/docs/en/plugins.md)]
- **MCP scopes**: project `.mcp.json` (team-shared), user `~/.claude.json`, local; env-var expansion supported; tool output default 25K tokens, warning at 10K. [[mcp.md](https://code.claude.com/docs/en/mcp.md)]
- **Best practices**: context management as #1 constraint; verification gates (tests, build, screenshot diffs); CLAUDE.md ≤200 lines; separation of exploration/planning/code phases. [[best-practices.md](https://code.claude.com/docs/en/best-practices.md)]

---

## Sources

- [memory.md](https://code.claude.com/docs/en/memory.md) – CLAUDE.md load order, rules, imports, AGENTS.md integration
- [skills.md](https://code.claude.com/docs/en/skills.md) – SKILL.md frontmatter, AgentSkills spec alignment
- [hooks.md](https://code.claude.com/docs/en/hooks.md) – All 30+ hook events, JSON schema, exit codes
- [plugins.md](https://code.claude.com/docs/en/plugins.md) – Plugin structure, distribution, testing
- [mcp.md](https://code.claude.com/docs/en/mcp.md) – MCP scopes, .mcp.json format, token limits
- [best-practices.md](https://code.claude.com/docs/en/best-practices.md) – Context management, verification, prompt design
- [agents.md](https://code.claude.com/docs/en/agents.md) – Subagent types, parallel work coordination
- [sub-agents.md](https://code.claude.com/docs/en/sub-agents.md) – Subagent file-based config, frontmatter fields

---

## Findings

### A. CLAUDE.md: Load Order, Scopes, Import Syntax

**Load order** (broadest to most specific): [[memory.md](https://code.claude.com/docs/en/memory.md)]
1. Managed policy (`/Library/Application Support/ClaudeCode/CLAUDE.md` on macOS; `/etc/claude-code/` on Linux/WSL; `C:\Program Files\ClaudeCode\` on Windows)
2. User `~/.claude/CLAUDE.md`
3. Ancestor `CLAUDE.md` files (root down to cwd)
4. Project `.claude/CLAUDE.md` or `./CLAUDE.md`
5. Project `CLAUDE.local.md` (last, gitignored)
6. Nested subdirectory `.claude/CLAUDE.md` (lazy-loaded when Claude accesses files in that dir)

**@-imports**: relative or absolute paths; supports recursive import (max 4 hops); skips imports within backticks (`` `@path` `` is literal); imported files load at launch alongside referencing file. [[memory.md](https://code.claude.com/docs/en/memory.md)]

**AGENTS.md support**: Claude Code reads `CLAUDE.md`, not `AGENTS.md`. Create `./CLAUDE.md` with `@AGENTS.md` import or symlink (requires Administrator/Dev Mode on Windows). [[memory.md](https://code.claude.com/docs/en/memory.md)]

**Size guidance**: target ≤200 lines per file; consumed as context every session; runs `/init` to bootstrap; `--add-dir` + `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` to load memory from external dirs. [[memory.md](https://code.claude.com/docs/en/memory.md)]

**CLAUDE.local.md**: project-level personal preferences; add to `.gitignore`; loads after CLAUDE.md at same level; external imports disabled in Cowork sessions on desktop. [[memory.md](https://code.claude.com/docs/en/memory.md)]

### B. Rules, Skills, Subagents

**`.claude/rules/` (path-scoped rules)**: YAML frontmatter with `paths:` (glob patterns); load unconditionally at launch (no `paths:`) or on demand (with `paths:`); symlinks supported; shared via symlink to `~/.claude/rules/` (user scope). [[memory.md](https://code.claude.com/docs/en/memory.md)]

**Skills (.claude/skills/<name>/SKILL.md)**: [[skills.md](https://code.claude.com/docs/en/skills.md)]
- Frontmatter: `name`, `description`, `when_to_use`, `arguments` (for `$name` substitution), `disable-model-invocation` (user-only), `user-invocable: false` (Claude-only), `allowed-tools`, `disallowed-tools`, `model`, `effort`, `paths:` (glob), `hooks:`, `metadata:`
- Dynamic context: `` !`command` `` injects shell output before Claude reads skill
- AgentSkills standard: Claude Code supports standard fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) for cross-agent distribution; Claude-only extensions (`disable-model-invocation`, `arguments`, `when_to_use`, `paths:`, `hooks:`, etc.) cause packaging errors outside Claude Code

**Subagents (`.claude/agents/<name>.md`)**: [[sub-agents.md](https://code.claude.com/docs/en/sub-agents.md)]
- Frontmatter: `name`, `description`, `tools:` list, `disallowedTools:`, `model` (`sonnet`, `opus`, `haiku`, `inherit`), `permissionMode:`, `memory:` (`user`/`project`/`local`), `isolation: worktree`, `maxTurns:`, `hooks:`, `mcpServers:`
- Loaded from managed settings (priority 1), CLI `--agents` (2), `.claude/agents/` project (3), `~/.claude/agents/` user (4), plugin `agents/` (5)

### C. Hooks: Events, Configuration, Exit Codes

**All hook events** (~30): [[hooks.md](https://code.claude.com/docs/en/hooks.md)]
- Session: `SessionStart`, `SessionEnd`, `Setup`
- Turn: `UserPromptSubmit`, `UserPromptExpansion`, `Stop`, `StopFailure`
- Tool: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `PermissionRequest`, `PermissionDenied`
- Agent: `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`
- Context: `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `FileChanged`, `PreCompact`, `PostCompact`, `PreModelSwitch`
- MCP: `Elicitation`, `ElicitationResult`

**Configuration**: JSON in `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json`, managed policy, or plugin `hooks/hooks.json`. [[hooks.md](https://code.claude.com/docs/en/hooks.md)]

**Handler types**: `command` (shell + JSON stdin/stdout), `http` (POST JSON), `mcp_tool` (call MCP), `prompt` (Claude judges), `agent` (subagent verification). [[hooks.md](https://code.claude.com/docs/en/hooks.md)]

**Exit codes & JSON**: exit 0 = success (read JSON); exit 2 = block (prevent action); other = non-blocking error. JSON output: `hookSpecificOutput.permissionDecision` (`"allow"`, `"deny"`, `"defer"`), `additionalContext`, `updatedInput` (for PreToolUse). [[hooks.md](https://code.claude.com/docs/en/hooks.md)]

**Path variables**: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`. [[hooks.md](https://code.claude.com/docs/en/hooks.md)]

### D. Plugins: Structure, Distribution, End-User MCP Integration

**Plugin.json manifest**: `.claude-plugin/plugin.json` with `name`, `description`, `version` (optional; if omitted, uses fallback), `author.name`. [[plugins.md](https://code.claude.com/docs/en/plugins.md)]

**Bundle components**: [[plugins.md](https://code.claude.com/docs/en/plugins.md)]
- `skills/` directory (preferred) or flat `commands/` (deprecated)
- `agents/` custom subagents
- `hooks/hooks.json` event handlers
- `.mcp.json` MCP server configs
- `.lsp.json` LSP server configs
- `monitors/monitors.json` background watchers
- `bin/` executables (not for marketplace distribution)
- `settings.json` default config (only `agent`, `subagentStatusLine` keys)

**Distribution**: private repo marketplace, public `anthropics/claude-plugins-community`, or `anthropics/claude-plugins-official` (curated); submit via claude.ai or platform.claude.com. Run `claude plugin validate ./plugin` before submit. [[plugins.md](https://code.claude.com/docs/en/plugins.md)]

**Testing**: `--plugin-dir ./plugin`, `--plugin-url https://example.com/plugin.zip`; use `claude plugin eval` for test suites. [[plugins.md](https://code.claude.com/docs/en/plugins.md)]

### E. MCP in Claude Code

**Scopes**: [[mcp.md](https://code.claude.com/docs/en/mcp.md)]
- Project `.mcp.json` (team-shared, checked in)
- User `~/.claude.json` (personal, cross-project)
- Local `~/.claude.json` (default, personal)

**.mcp.json format**: `mcpServers: { "name": { "type": "http|sse|ws|stdio", "url": "...", "env": {...} } }` with env-var expansion (`${VAR}`, `${VAR:-default}`). [[mcp.md](https://code.claude.com/docs/en/mcp.md)]

**Tool output limits**: default warning 10K tokens, limit 25K tokens, hard ceiling 500K chars. Set `MAX_MCP_OUTPUT_TOKENS` env var globally or `_meta.anthropic/maxResultSizeChars` per tool in MCP server. [[mcp.md](https://code.claude.com/docs/en/mcp.md)]

### F. Best Practices for Long-Running Agent Work

**Context management (#1 constraint)**: [[best-practices.md](https://code.claude.com/docs/en/best-practices.md)]
- Monitor with `/context` (memory files, cwd, loaded rules)
- Track usage with custom status line
- Run `/clear` between unrelated tasks; `/compact` for controlled trimming
- Use subagents to isolate research context

**Verification gates**: [[best-practices.md](https://code.claude.com/docs/en/best-practices.md)]
- In-prompt: run check + iterate same turn
- `/goal`: separate evaluator re-checks after every turn
- `Stop` hook: deterministic gate (blocks until passes; max 8 blocks)
- Verification subagent: fresh model refutes claims

**Exploration → Planning → Code phase separation**: [[best-practices.md](https://code.claude.com/docs/en/best-practices.md)]
- Plan mode (`claude --permission-mode plan`) for reads-only exploration
- Write detailed plan; edit with `Ctrl+G`
- Switch out of plan mode to implement

**CLAUDE.md best practice**: ≤200 lines; include build commands, code style, workflows; exclude info Claude can derive from code. Run `/doctor` to propose trims. [[best-practices.md](https://code.claude.com/docs/en/best-practices.md)]

---

## Implications for our framework

### Recommended layout for AGENTS.md ↔ CLAUDE.md integration

```
root/
├── AGENTS.md                          # Cross-agent contract (all vendors)
├── CLAUDE.md                          # Import @AGENTS.md + Claude-specific guidance
├── .claude/
│   ├── CLAUDE.md                      # (optional) nested project directives
│   ├── rules/
│   │   ├── code-style.md              # Enforce ML coding standards (paths: "src/**")
│   │   ├── security.md                # Secret blocking hook (paths: "**")
│   │   └── experiment-reproducibility.md  # Seed/checkpoint rules
│   ├── agents/
│   │   ├── code-auditor.md            # Read-only policy checker
│   │   └── experiment-validator.md    # Ablation analysis specialist
│   ├── skills/
│   │   ├── add-source-provider/SKILL.md
│   │   ├── add-memory-provider/SKILL.md
│   │   ├── run-evals/SKILL.md
│   │   ├── audit-licenses/SKILL.md
│   │   └── release/SKILL.md
│   ├── settings.json                  # Hooks for schema validation, secret blocking, test-on-Stop
│   └── settings.local.json            # (gitignored) local API keys, sandbox toggles
├── docs/dev/
│   ├── STATE.md                       # Progress, handoff, blockers
│   ├── HANDOFF.md                     # From Codex to Claude
│   ├── ROADMAP.md
│   ├── DECISIONS/                     # ADRs (e.g., why MCP over direct API)
│   └── KNOWN_ISSUES.md
└── .mcp.json                          # Local MCP config (team's private server URL)
```

### End-user Claude Code adapter (plugin for PRODUCT)

Our PRODUCT (the Personal Context & Memory Framework) ships as a Claude Code plugin:

```
our-product-plugin/
├── .claude-plugin/plugin.json         # name: "our-product", version: "1.0.0"
├── skills/
│   ├── setup/SKILL.md                 # /our-product:setup – register our MCP server
│   └── init-session/SKILL.md          # /our-product:init-session – load identity card
├── .mcp.json                          # Register our MCP server (stdio or HTTP)
└── hooks/hooks.json                   # SessionStart hook injects identity card context
```

**SessionStart hook example** (from [hooks.md](https://code.claude.com/docs/en/hooks.md)):
- Injects `additionalContext: "Your persona: [L0 identity card from our MCP server]"` at session start
- Uses `"type": "mcp_tool"` to fetch identity card via `mcp__our-product-mcp__get-identity` once per session

---

## Open questions → candidate PoC spikes

1. **Slash command merging**: Are `/command` and skill `/plugin:skill` now unified? (Docs suggest skills replaced commands post-v2.1.) → Spike: test if commands/ still work or require skills/ migration.
2. **Nested CLAUDE.md in subdirs + monorepo exclusions**: Does `claudeMdExcludes` glob pattern matching work with `@`-imports, or does it only filter loaded files? → Spike: test monorepo setup with team CLAUDE.md + exclusion.
3. **Hook `SessionStart` context injection size limit**: Docs don't state token budget for `additionalContext` field. → Spike: measure in real session; confirm no silent truncation of identity card.
4. **MCP prompt elicitation in hooks**: Can `Elicitation` hook integrate with prompt-based hook decisions? → Spike: prototype hook that uses MCP server's prompt resources as condition checks.
5. **Agent Skills distribution packaging**: If we want to distribute our skills via agentskills.io registry, do only standard fields export? → Spike: validate plugin publish flow with partial YAML export.

---

## Confidence & gaps

**High confidence** (v2.1.239+ docs, tested recently):
- CLAUDE.md load order, import syntax, nested rules
- Skills frontmatter, AgentSkills spec alignment
- Hook events, JSON schema, exit code blocking behavior
- Plugin.json structure, distribution flow
- MCP token limits, env-var expansion

**Unverified** (docs incomplete or no explicit mention):
- Exact token budget for SessionStart `additionalContext` injection (implied ≤4MiB file but not stated)
- Whether `disableAllHooks` blocks managed policy hooks (docs say "cannot disable" managed hooks "from non-managed settings" but unclear if in managed settings themselves)
- AgentSkills registry integration (no official endpoint; infer from claude.ai submit form)
- Codex/OpenAI Codex compatibility with Claude Code CLAUDE.md/@-imports (out of scope for this research, but raised in planning context)

**Recommended first spike**: Create test AGENTS.md → CLAUDE.md import in a real project; verify all three load-order layers (managed, user, project) read correctly; confirm `/context` shows all three.

---

## Planning-agent annotations (2026-09-18)

- The layout sketch under *Implications* copies generic ML-project rules (`experiment-reproducibility.md`,
  `experiment-validator.md`) that do **not** apply to this repository. The actual harness layout is
  still awaiting a dedicated ADR; no harness-layout ADR existed at takeover time.
- Claims to re-verify in spike S2 before relying on them: (1) `SessionStart` hook handler `type: "mcp_tool"`
  can call our MCP server to fetch the L0 card; (2) size limit of `additionalContext`; (3) per-tool
  `_meta["anthropic/maxResultSizeChars"]` override. Until verified, the Claude Code adapter must not depend on them.
- "Local" vs "user" MCP scope wording above is ambiguous; consult `code.claude.com/docs/en/mcp` when implementing the adapter.

### Verified by planning agent (WebFetch of code.claude.com/docs/en/hooks, 2026-09-18)

- Five hook handler types exist: `command`, `http`, `mcp_tool`, `prompt`, `agent`.
- **Correction:** `mcp_tool` hooks are *skipped* for `SessionStart` at launch — the docs state SessionStart
  "fires before the servers are available" and Claude Code "skips the event's `mcp_tool` hooks".
  ⇒ The end-user Claude Code adapter must inject the L0 identity card with a **`command` hook** whose
  plain-text stdout becomes context (stdout is added as context for `SessionStart`, `UserPromptSubmit`,
  `UserPromptExpansion`, `PostModelSwitch`). Cheapest implementation: print a pre-rendered card file.
- SessionStart matchers: `startup`, `resume`, `clear`, `compact`, `fork`.
- No documented size limit for SessionStart-injected context and no documented Stop-block cap
  (the "max 8 blocks" claim above is unverified) — keep the L0 card small by design (budget in ADR-0009).

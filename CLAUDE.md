@AGENTS.md

# Claude Code specifics

- Treat `AGENTS.md` as the canonical repository contract. It takes precedence over user-level global
  defaults (for example automatic Research Memory initialization or Obsidian project-memory
  bootstrap); those need explicit maintainer confirmation in this repository.
- Keep host-specific automation thin. Reusable task workflows belong in skills after their
  contracts stabilize.
- A product L0 identity card must be printed by a bounded command hook from a pre-rendered file;
  do not call MCP at `SessionStart`, when MCP servers are not yet available.
- Never place private source content in hook logs or hook configuration.

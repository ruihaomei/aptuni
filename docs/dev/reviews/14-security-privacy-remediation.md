# Security and Privacy Notes Remediation (post-approval)

- **Responds to:** `14-security-privacy-sixth-rereview.md`
- **Date:** 2026-09-18
- **Status:** non-blocking notes addressed before S04; no re-review required by the verdict

| Note | Remediation |
|---|---|
| H6-1 Codex escalation | Reviewer option 3, chosen for lightness: the Codex profile keeps the user's escalation policy, reports reason code `host_escalation_available`, and ADR-0013 items 2/8 plus THREAT_MODEL non-claims state that approving an escalation request for this CLI runs an agent-composed command unconfined. Users may choose `approval_policy=never`. Claude Code profile disables unsandboxed retry. Verification case added. |
| H6-2 unsandboxed core processes | ADR-0013 item 1: approve/commit service reachable only from the CLI approve entry point; MCP, hook and worker processes never call it; no non-CLI input schema carries action-selection/token/nonce fields; workers run only committed intents. Import-graph, schema-enumeration and S04 cases added. |
| M6-1 | THREAT_MODEL authorization table now says "terminal-only CLI confirmation". |
| M6-2 | Abuse case 2 reworded: never claims confinement; `not_in_effect` only on core-observed evidence, `unverified` otherwise. |
| M6-3 | "Terminal-only" defined as the CLI subcommand in a process not denied by host confinement; core cannot identify the terminal. CLI output run from an agent shell moved into THREAT_MODEL non-claims; plan 02 preview discloses it. |
| M6-4 | Project-scope host config files (Claude Code `.claude/settings*.json`, `.mcp.json`, hook scripts; Codex project config) are protected paths; non-bundled hook/MCP entries are a `not_in_effect` reason code; S04 case added. |
| L6-1 | Session key: host session ID where available, else MCP process lifetime; recorded per host version. |
| L6-2 | Drift wording aligned: observable drift → `profile: drifted`; `not_in_effect` only with evidence; unknown version → `unverified` (ADR-0013 Consequences, KI-014). |
| L6-3 | Action IDs resolve by exact match only. |
| L6-4 | Setup states the profile covers only newly launched sessions and asks for a relaunch. |

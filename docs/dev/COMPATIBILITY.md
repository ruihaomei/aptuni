# MVP Compatibility and Locale Matrix

**Status:** Draft; S03 fixed the SQLite baseline. S04 is in progress and S12/the first scaffold still
fill release versions before acceptance.

Gate 0/S01 proof baseline on 2026-09-18: macOS 26.2 (build 25C56), local APFS **data** volume
(`/System/Volumes/Data`, where user files live; the root volume is sealed/read-only), CPython 3.13.3
at `/opt/homebrew/bin/python3.13` with its SQLite 3.53.2. Installed Claude Code 2.1.87
(`~/.local/bin/claude`) and Codex CLI 0.153.4 (ChatGPT desktop bundle) are local S04 evidence hosts,
not the release matrix. On 2026-09-19 the upstream stable targets were Claude Code 2.1.267 plus
2.1.266 and Codex 0.155.0 plus 0.154.0. Codex read paths pass; Claude's two journeys remain blocked
before inference by the account usage limit. Gate 0 accepts the Vault
write protocol only on this baseline; unknown, network,
or synchronized filesystems fail closed until separately admitted.

## Supported production matrix

| Surface | Milestone 1 support |
|---|---|
| Python | CPython 3.11, 3.12, 3.13 |
| OS/filesystem | Gate 0: macOS 26.2/APFS. M1.1 adds an exact Ubuntu LTS/ext4 CI runner before claiming Linux support. |
| SQLite | bundled Python SQLite with FTS5; minimum exact version established by S03 |
| Hosts | Claude Code and Codex versions proven by S04/S12. S04 records the current and the preceding stable version per host before any host journey runs; both must pass. A missing preceding version is release-blocking unless a `KNOWN_ISSUES.md` waiver records the attempted source, reason, and reviewer approval |
| Locale | `en` and `zh-CN`; deterministic English fallback for unknown locale |
| Approval | ADR-0013 terminal-only confirmation; confinement reported only as `not_in_effect` / `unverified` |
| Cursor / Claude Desktop | protocol-compatibility notes only in M1, not first-class adapter support |

Every release records exact CI and host versions. A host/SQLite/Python version outside the matrix is
an explicit diagnostic gap, not a silent pass. Upgrades rerun capability, telemetry/egress, schema,
L0, and daily-task probes; downgrade reads older supported schemas or fails with migration guidance.

## Required locale/host scenarios

Run the same fresh-install, guided setup, source sync, query, observe/review, permission change,
purge, doctor, and handoff scenario in:

```text
Claude Code × en
Claude Code × zh-CN
Codex       × en
Codex       × zh-CN
```

Also test mixed Chinese/English queries, Unicode normalization, two-character Chinese terms, Chinese
filenames/Vault paths, byte/response-unit truncation, locale fallback, and snapshots that fail on any
untranslated user-facing key. Hosted scenarios use synthetic data; strict local-only scenarios use a
fake proven-local host and verify remote/unknown host denial.

## Host confinement required keys (ADR-0013 item 3, normative)

S04 fills each row with exact key names, required values, and the core-observable evidence source
(merged settings, host argv, or hook-reported permission mode) for the pinned host version before any
host journey. Only a complete effective-settings snapshot can yield `installed`, `missing` or
`drifted`; an unreadable, incomplete or ambiguously merged snapshot yields profile `unverified`.
Core reports confinement `not_in_effect` when positive observable evidence shows a required state is
missing, overridden or appended; otherwise confinement is `unverified`. Core never reports
confinement as proven.

| Host (version) | Surface | Required state | Verified by S04 |
|---|---|---|---|
| Claude Code 2.1.267 + 2.1.266 | Bash OS sandbox | `sandbox.enabled=true`; `failIfUnavailable=true`; `allowUnsandboxedCommands=false`; `filesystem.disabled=false`; protected paths denied; no `excludedCommands` entry reaches them | keys confirmed by current official docs; real probes blocked by account limit |
| Claude Code 2.1.267 + 2.1.266 | Edit/Write/Read tools | permission deny rules for protected paths (rule-based, reason code `edit_tool_rule_based`) | pending real probe; these tools do not use the Bash OS sandbox |
| Claude Code 2.1.267 + 2.1.266 | Escape settings | `allowAppleEvents=false`; Unix sockets cannot reach core; `additionalDirectories`, permission modes and setting-source selection do not expose protected paths | exact merged values and real probes pending |
| Claude Code 2.1.267 + 2.1.266 | Hooks/MCP/plugin files | user-scope files outside every writable root; project-scope `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`, hook scripts write-denied; non-bundled hook/MCP entries → `not_in_effect` | pending |
| Codex 0.155.0 + 0.154.0 | Sandbox | `sandbox_mode=workspace-write`; protected paths outside `sandbox_workspace_write.writable_roots`; `network_access=false`; `exclude_tmpdir_env_var=true`; `exclude_slash_tmp=true` | partial: real protected write denied in both versions; remaining keys/probes pending |
| Codex 0.155.0 + 0.154.0 | Approval/escalation | record effective `approval_policy`; `on-request` or granular sandbox approval → reason `host_escalation_available`; `never` removes the prompt | partial: `never` used in read/write journeys; effective-value observability pending |
| Codex 0.155.0 + 0.154.0 | Config/profiles | no profile/`-c`/project override weakens the above; `~/.codex` and bundled adapter path outside writable roots | pending; project-scoped `.codex` layers are skipped only for untrusted projects |
| Any | Install path | installed package outside every writable root (never a project `.venv`) | pending |

## S04 interim host evidence (not acceptance)

| Host/session | Measured result | Remaining gap |
|---|---|---|
| Codex 0.155.0 and 0.154.0, `read-only`, `approval_policy=never` | Current and preceding stable both returned `HOST_OK 61` from the bounded annotated L0 tool. | Required read path passes; protected-path/status/session probes pending. |
| Codex 0.153.4, same session profile | Without `readOnlyHint` the host denied the call as approval-required; after annotation it returned `HOST_OK 61`. A non-destructive idempotent candidate write was allowed, and core kept it quarantined/non-exposable. | Older installed observation only. |
| Claude Code 2.1.267 and 2.1.266 | Authentication and both binaries pass startup; both then fail before inference/MCP with HTTP 429 and zero API tokens/tool calls because the account usage/session limit is exhausted. | Rerun after the limit resets or is raised. |
| Claude Code 2.1.87, `dontAsk`, strict synthetic MCP config | No MCP call occurred; repeated host API HTTP 400, zero API duration/tokens/cost, bounded termination after 131.6 seconds. | External/account/API blocker; version is behind stable. |

Official current Codex configuration accepts `approval_policy = "on-request" | "never"` (plus a
granular table); `untrusted` is removed and `on-failure` deprecated. `workspace-write` command
network defaults off, but that control explicitly does not cover MCP, model/auth, apps, browser, or
other client traffic. Claude's current sandbox supports `sandbox.enabled`,
`allowUnsandboxedCommands=false`, `failIfUnavailable`, `filesystem.disabled=false`,
`filesystem.denyRead`/`denyWrite`, `allowAppleEvents=false`, an empty `allowUnixSockets`, and read/
edit permission rules. Built-in Read/Edit/Write use permission rules rather than the Bash OS sandbox,
and `excludedCommands` can be appended across settings scopes, so those surfaces require separate
real-host probes. Several controls postdate installed 2.1.87; the release profile targets
2.1.267/2.1.266 and cannot infer support from the older binary.

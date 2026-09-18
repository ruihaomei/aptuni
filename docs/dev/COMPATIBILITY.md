# MVP Compatibility and Locale Matrix

**Status:** Draft; S03 fixed the SQLite baseline. S04 is in progress and S12/the first scaffold still
fill release versions before acceptance.

Gate 0/S01 proof baseline on 2026-09-18: macOS 26.2 (build 25C56), local APFS **data** volume
(`/System/Volumes/Data`, where user files live; the root volume is sealed/read-only), CPython 3.13.3
at `/opt/homebrew/bin/python3.13` with its SQLite 3.53.2. Installed Claude Code 2.1.87
(`~/.local/bin/claude`) and Codex CLI 0.153.4 (ChatGPT desktop bundle) are local S04 evidence hosts,
not the release matrix. On 2026-09-19 the upstream stable targets were Claude Code 2.1.267 plus
2.1.266 and Codex 0.155.0 plus 0.154.0; those four journeys remain pending. Gate 0 accepts the Vault
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
host journey. Core reports `not_in_effect` when observable evidence shows a required state is missing,
overridden, or appended; otherwise `unverified`. Core never reports confinement as proven.

| Host (version) | Surface | Required state | Verified by S04 |
|---|---|---|---|
| Claude Code 2.1.87 | Bash OS sandbox | enabled; protected paths denied for writes and, where supported, reads; no unsandboxed retry or excluded command (approval is terminal-only) | pending |
| Claude Code 2.1.87 | Edit/Write/Read tools | deny rules for protected paths (rule-based, reason code `edit_tool_rule_based`) | pending |
| Claude Code 2.1.87 | Escape settings | Apple Events, Unix sockets to core, extra directories and bypass/auto permission modes do not reach protected paths | pending |
| Claude Code 2.1.87 | Hooks/MCP/plugin files | user-scope files outside every writable root; project-scope `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`, hook scripts write-denied; non-bundled hook/MCP entries → `not_in_effect` | pending |
| Codex 0.153.4 + preceding | Sandbox | workspace-write; protected paths outside writable roots; network off unless granted | pending |
| Codex 0.153.4 + preceding | Approval/escalation | record the effective approval policy; escalation-capable → reason `host_escalation_available` (user's control is declining; `never` removes it); record read-deny support and project-config handling | pending |
| Codex 0.153.4 + preceding | Config/profiles | no profile/`-c` override weakens the above; `~/.codex` not writable | pending |
| Any | Install path | installed package outside every writable root (never a project `.venv`) | pending |

## S04 interim host evidence (not acceptance)

| Host/session | Measured result | Remaining gap |
|---|---|---|
| Codex 0.153.4, `read-only`, `approval_policy=never` | Standard `readOnlyHint` allowed the bounded synthetic L0 call; without it the host denied the call as approval-required. A non-destructive idempotent candidate write was allowed, and core kept it quarantined/non-exposable. | Version is behind current stable; protected-path/status/session probes pending. |
| Claude Code 2.1.87, `dontAsk`, strict synthetic MCP config | No MCP call occurred; repeated host API HTTP 400, zero API duration/tokens/cost, bounded termination after 131.6 seconds. | External/account/API blocker; version is behind stable. |

Official current Codex configuration accepts `approval_policy = "on-request" | "never"` (plus a
granular table); `untrusted` is removed and `on-failure` deprecated. `workspace-write` command
network defaults off, but that control explicitly does not cover MCP, model/auth, apps, browser, or
other client traffic. Claude's current sandbox supports `sandbox.enabled`,
`allowUnsandboxedCommands=false`, `failIfUnavailable`, `filesystem.denyRead`/`denyWrite`, and read/
edit permission rules, but several controls postdate installed 2.1.87. S04 must verify them on the
target versions rather than copying current docs into an old profile.

# MVP Compatibility and Locale Matrix

**Status:** Draft; S03 fixed the SQLite baseline and hosted run 35520369299 closed the Ubuntu
24.04/ext4 gate. S12 still fills the real-host rows before host acceptance.

Gate 0/S01 proof baseline on 2026-09-18: macOS 26.2 (build 25C56), local APFS **data** volume
(`/System/Volumes/Data`, where user files live; the root volume is sealed/read-only), CPython 3.13.3
at `/opt/homebrew/bin/python3.13` with its SQLite 3.53.2. Installed Claude Code 2.1.87
(`~/.local/bin/claude`) and Codex CLI 0.153.4 (ChatGPT desktop bundle) are local S04 evidence hosts,
not the release matrix. On 2026-09-19 the upstream stable targets were Claude Code 2.1.267 plus
2.1.266 and Codex 0.155.0 plus 0.154.0. All four required MCP read journeys and host-confinement A/B
journeys completed. Gate 0 accepts the Vault write protocol only on this baseline; unknown, network,
or synchronized filesystems fail closed until separately admitted.

## Supported production matrix

| Surface | Milestone 1 support |
|---|---|
| Python | CPython 3.11, 3.12, 3.13 |
| OS/filesystem | macOS 26.2/APFS plus Ubuntu 24.04/ext4; hosted run 35520369299 passed the real filesystem admission and durability gate at `c86e861`. Other filesystems remain unadmitted. |
| SQLite | bundled Python SQLite with FTS5; minimum exact version established by S03 |
| Hosts | Claude Code and Codex versions proven by S04/S12. S04 records the current and the preceding stable version per host before any host journey runs; both must pass. A missing preceding version is release-blocking unless a `KNOWN_ISSUES.md` waiver records the attempted source, reason, and reviewer approval |
| Locale | `en` and `zh-CN`; deterministic English fallback for unknown locale |
| Approval | ADR-0013 terminal-only confirmation; confinement reported only as `not_in_effect` / `unverified` |
| Cursor / Claude Desktop | protocol-compatibility notes only in M1, not first-class adapter support |

Every release records exact CI and host versions. A host/SQLite/Python version outside the matrix is
an explicit diagnostic gap, not a silent pass. Upgrades rerun capability, telemetry/egress, schema,
L0, and daily-task probes; downgrade reads older supported schemas or fails with migration guidance.

## Hosted filesystem evidence

GitHub Actions run 35520369299 at `c86e861` completed successfully on 2026-09-20. Its Ubuntu 24.04
job passed the full 459-test/47-subtest suite, ruff, strict mypy, relay and 34 developer checks. The
separate ext4 durability step passed 91 tests plus 11 subtests across filesystem admission,
concurrency, Vault and backup behavior. The real-baseline admission test resolves the runner's
temporary path through `/proc/self/mountinfo`, requires `fstypename == "ext4"` and `is_local`, and
then exercises `check_vault_filesystem`; it is not inferred from the runner label.

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
| Claude Code 2.1.267 + 2.1.266 | Bash OS sandbox | `sandbox.enabled=true`; `autoAllowBashIfSandboxed=true`; `failIfUnavailable=true`; `allowUnsandboxedCommands=false`; `filesystem.disabled=false`; exact protected paths in `denyRead`/`denyWrite`; `allowWrite=[]`; `excludedCommands=[]` | Both versions: CLI `--settings` baseline blocked protected write. Project source injected an environment marker and attempted scalar/list weakening, but no escape was observed. The cause is not attributed (CLI precedence, `excludedCommands` matching or permission mode), so blocked results stay `unverified`. Complete managed+CLI+project provenance is not exposed, so baseline profile remains `unverified`; core can positively scan non-bundled project entries. |
| Claude Code 2.1.267 + 2.1.266 | Edit/Write/Read tools | exact absolute `Read(//path)` and `Edit(//path)` denies for protected paths (rule-based, reason code `edit_tool_rule_based`); path-scoped `Write(path)` is not consulted by these versions | Focused non-persistent runs loaded the exact policy and session hook. Claude emitted no Read/Write call, so neither a tool denial nor confinement is claimed. The outer marker stayed unchanged and the random read token was absent in both versions. |
| Claude Code 2.1.267 + 2.1.266 | Escape settings | `allowAppleEvents=false`; `allowUnixSockets=[]`; `network.allowedDomains=[]`; no `additionalDirectories`; CLI `--permission-mode dontAsk`, `--permission-prompts none`, and explicit `--setting-sources` | Both versions blocked live TCP and AF_UNIX connections, confirmed by independent outer listeners. Focused runs recorded the exact `osascript` attempt before permission handling and no Apple Event effect; no native approval prompt appeared. No launch used `--add-dir`. CLI launch values are known to the launcher, but complete effective settings remain unobservable. |
| Claude Code 2.1.267 + 2.1.266 | Hooks/MCP/plugin files | user-scope files outside every writable root; project-scope `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`, hook scripts write-denied; non-bundled hook/MCP entries → `not_in_effect` | Project settings were loaded in both versions, proven by an outer-observed project `SessionStart` hook marker that is absent in baseline (`--setting-sources ''`). The fixture itself is positive `unbundled_entry_visible` evidence even though CLI precedence blocked escape. The focused Write leg emitted no call, so no built-in Write denial is claimed. |
| Codex 0.155.0 + 0.154.0 | Sandbox | CLI `sandbox_mode=workspace-write`; protected paths outside writable roots; `sandbox_workspace_write.network_access=false`; `exclude_tmpdir_env_var=true`; `exclude_slash_tmp=true` | Both versions blocked protected write, TCP and AF_UNIX under explicit CLI overrides; outer observations matched. Legacy `workspace-write` permits reads outside the workspace, so it cannot claim protected-read denial. Complete effective-setting provenance is not exposed; baseline stays `unverified`. |
| Codex 0.155.0 + 0.154.0 | Approval/escalation | record effective `approval_policy`; `on-request` or granular sandbox approval → reason `host_escalation_available`; `never` removes the prompt | Both read and canary journeys used CLI `never`. The launcher knows its flag; the MCP process cannot prove every launch layer, so an absent positive escape remains `unverified`. |
| Codex 0.155.0 + 0.154.0 | Config/profiles | no profile/`-c`/trusted-project override weakens the above; `~/.codex` and bundled adapter path outside writable roots | Isolated A/B (temporary `CODEX_HOME` with one trust entry, identical in every mode): a trusted control with no `.codex/` blocked write/TCP/AF_UNIX, while the project `.codex/config.toml` alone selected `danger-full-access` and made all three succeed. Outer observers confirmed each effect in both versions. Core project-file scanning yields `escape_setting_visible` for the visible `sandbox_mode`, and the successful effects add write/socket reasons. |
| Any | Install path | installed package outside every writable root (never a project `.venv`) | The S12 runner resolved the generated bundle's interpreter, imported `aptuni` under `-I`, and recorded only content-free classification booleans: interpreter and package both outside the project, built wheel importable, project `.venv` unused. The frozen matrix records `private_temporary_runtime_outside_project`. |

The S12 daily-task matrix passes on all four frozen versions from an Aptuni wheel installed in a
private temporary runtime outside the project. Each non-persistent host session called the bounded
identity tool, observed the synthetic handoff marker, called context for an ungranted module and
received `mcp_module_denied`. The focused Claude matrix also completes the exact-path file-tool and
Apple Event observations with sanitized evidence. File-tool calls were not emitted, while Apple
Event attempts were; absence of unsafe effects remains `unverified`, never a confinement claim.

Session evidence uses the Claude `SessionStart` hook session ID when the packaged hook is present;
the MCP process lifetime is the fallback and the Codex key. Real Claude 2.1.267/2.1.266
project hooks received a non-empty `session_id` (sanitized to a boolean), so the capture path exists;
the S04 fixture still binds evidence to one runner process and never carries it forward.

## S04 interim host evidence (not acceptance)

| Host/session | Measured result | Remaining gap |
|---|---|---|
| Codex 0.155.0 and 0.154.0, `read-only`, `approval_policy=never` | Current and preceding stable both returned `HOST_OK 61` from the bounded annotated L0 tool. | Required read path passes. |
| Codex 0.153.4, same session profile | Without `readOnlyHint` the host denied the call as approval-required; after annotation it returned `HOST_OK 61`. A non-destructive idempotent candidate write was allowed, and core kept it quarantined/non-exposable. | Older installed observation only. |
| Claude Code 2.1.267 and 2.1.266, `dontAsk`, strict MCP config | Both returned `HOST_OK 61`. Baseline write/TCP/AF_UNIX canaries were blocked; the outer-observed project hook loaded without escaping the CLI profile and carried a session id. Focused runs emitted the Apple Event attempt with no effect; file-tool attempts were not emitted and remain an explicit non-claim. | Required S12 observations complete; status remains `unverified`. |
| Codex 0.155.0 and 0.154.0, baseline / trusted control / trusted project | Baseline and control blocked write/TCP/AF_UNIX. The project layer alone made all three succeed; inner and outer observations agreed. | Closes project-injection detection, not protected-read support. |
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

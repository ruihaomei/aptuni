# ADR-0013: Treat shell-capable hosts as inside the user's trust boundary and require host confinement

- **Status:** Proposed — maintainer accepted the residual risk on 2026-09-18 (see Decision)
- **Date:** 2026-09-18
- **Deciders:** maintainer (chose this option explicitly) · planning agent · security reviewer
- **PRD refs:** §2 (technical/psychological lightness), §6, §17, §23, §27, §52
- **Research refs:** `docs/dev/research/05-claude-code-instructions.md`, `06-codex-instructions.md`
- **Supersedes in part:** the OS/FIDO2 **ApprovalBroker** paragraphs of ADR-0005, ADR-0010 (purge
  confirmation), ADR-0011 (candidate acceptance) and ADR-0012 (broker port). All other content of those
  ADRs stands.
- **Review lineage:** responds to `reviews/09-security-privacy-third-rereview.md` (B2-R3, H-A, H-B,
  N3–N5) and `reviews/12-security-privacy-fourth-rereview.md` (B4-1, H4-1–H4-3, M4-1–M4-6, L4-1–L4-5), and
  `reviews/13-security-privacy-fifth-rereview.md` (B5-1, B5-2, H5-1–H5-3, M5-1–M5-3, L5-1–L5-3), and
  `reviews/14-security-privacy-sixth-rereview.md` notes (H6-1, H6-2, M6-1–M6-4, L6-1–L6-4).

## Context

Claude Code and Codex, the mandatory MVP hosts, run shell commands and write files as the user. The
Vault is plaintext and must stay editable in Obsidian (PRD §21), and the product is an ordinary
user-installed Python package. A process that has the user's shell can therefore:

- edit review, grant and policy state directly,
- replace any enrolled credential,
- patch installed verifier code.

Four review rounds showed that every in-product approval mechanism (typed phrase, TTY, and then an
OS/FIDO2 broker) is bypassable from that position, unless the product also ships OS-level
confinement, a code-signed native helper and a signed-state trust base. That is weeks of native macOS
work, and it conflicts with PRD §2 technical lightness.

## Options considered

### Option A — Honest boundary plus host confinement (chosen)
Core enforcement covers only mutations made through application services (MCP, CLI, SDK). A host
agent with unconfined same-user shell access is trusted like the user. The actual protection against
an injected agent is the host's own OS sandbox and permission rules, which the adapters configure
and `doctor` checks for evidence of misconfiguration (it never certifies them).
- **+** Truthful, small and testable. It removes the authenticator enrollment problem and the
  test-authenticator isolation problem.
- **−** The guarantee depends on host configuration. When confinement is missing, it is reported as
  "not in effect" rather than enforced.

### Option B — Hardware-backed broker
A signed native helper holds a Secure Enclave key. The option also needs an enrollment ceremony and
signed-state verification on load.
- **+** Strongest guarantee.
- **−** Weeks of native work, code-signing certificates and an enrollment UX. It delays first use.
  **Deferred** to a later milestone, which needs a new ADR.

## Decision

Option A, chosen by the maintainer on 2026-09-18 with the residual risk explicitly accepted. Amended
the same day for reviews 12 and 13 (terminal-only approval; core never claims `confined`).

1. **Enforcement boundary (normative).** Core policy, confirmation, nonce and journal rules authorize
   mutations only through application services. Direct writes by a same-user process to the Vault,
   config/grant/state or installed package are *outside core enforcement*. The only *supported*
   approval surface is the CLI subcommand. An in-process caller of the SDK approve service is stopped
   only by OS confinement: a sandboxed process cannot commit the nonce or Vault write, so it fails
   closed. No document may claim that core confirmation stops an unconfined shell-capable host.
   The approve/commit service is reachable **only** from the CLI approve entry point: MCP handlers,
   hook handlers, journal workers and every other long-lived core process never call it, and no
   non-CLI input schema carries an action-selection, token or nonce field. Workers execute only
   intents that are already committed.
2. **Confirmation contract (terminal-only).** This is an accidental-action guard and an
   MCP-cannot-self-approve guard. It is not proof of human presence.
   - MCP tools and agents may *create* a pending action and point the user to it; they never approve.
   - Approval happens only through the `review` / `purge confirm` CLI subcommand, in a process that
     host confinement does not deny. "Terminal-only" names this surface; core does not and cannot
     tell the user's terminal from an agent shell. The CLI shows the full core-rendered preview:
     - action type, scope identity and count, egress provider/destination/data class, and
       irreversibility;
     - untrusted names, delimited and with confusables flagged.

     The user then selects the action. The command line carries only core-generated action IDs, in
     the charset `[a-z0-9-]`, never source-derived text, so there is nothing to shell-inject.
   - The token binds the **full** action digest, principal, policy epoch, scope, expiry and a
     single-use nonce. IDs resolve by exact match only (no prefix or fuzzy match); an unknown ID is
     rejected.
   - The entry point runs an isolated interpreter (`-I`: no `PYTHON*` env, no cwd on `sys.path`)
     from the install path.
   - Core provides no host-prompt routing. In a confined session without sandbox escalation, an
     agent-invoked approval cannot commit (the sandbox denies the Vault/nonce write), so it fails
     closed with a content-free reason code. Host escalation (e.g. a Codex on-request/untrusted/
     on-failure approval policy, or a Claude Code unsandboxed retry) runs the escalated command
     unconfined. If the user approves an escalation request for this CLI, the approval commits. The
     bundled Claude Code profile disables unsandboxed retry. The Codex profile keeps the user's
     escalation policy for usability, reports it as reason code `host_escalation_available`, and
     documents that declining escalation requests naming this CLI is the user's control; users may
     choose `approval_policy=never` instead. Unconfined sessions are the accepted residual risk
     (item 8).
3. **Host confinement profile.** For each adapter and pinned host version:
   - **Written by the core CLI** from package-bundled content, never authored by the agent. Changing
     global host settings is a consequential SetupPlan action with a preview.
   - **Protected paths:** agent writes (and, where the host supports it, reads) are denied to the Vault, the config/grant/state directories,
     the installed package (which must live outside every writable root, e.g. a `uv tool` location,
     never a project `.venv`), and host hook/MCP/plugin/adapter files, **including project-scope files
     inside writable roots** (Claude Code `.claude/settings.json`, `.claude/settings.local.json`,
     `.mcp.json`, project hook scripts; Codex project config if S04 finds it honored). Any hook or
     MCP-server entry in merged settings that is not in the bundled profile is a `not_in_effect`
     reason code.
   - **Required keys:** `COMPATIBILITY.md` holds the normative required-key list per host version,
     filled in by S04. It covers:
     - Claude Code: `sandbox.enabled`, `allowUnsandboxedCommands`, `excludedCommands` (merged across
       scopes), `allowAppleEvents`, `allowUnixSockets`, `filesystem`/`allowWrite`,
       `additionalDirectories`, permission mode, and Edit/Write deny rules;
     - Codex: `sandbox_mode`, `approval_policy`, writable roots, network access and profile
       overrides.

     A missing, overridden or appended required key lowers the status (item 4).
   - **Path identity and copies:** Core compares protected filesystem objects by canonical real path
     and `(st_dev, st_ino)`. Symlinks, hardlinks and renames that resolve to the same object are alias
     violations. Ordinary copies and APFS clones are distinct objects; core MUST NOT infer clone
     ancestry from `realpath`, `stat`, inode, timestamps or content equality. On an APFS volume
     advertising `VOL_CAP_FMT_CLONE_MAPPING`, an optional macOS-native scan may treat matching
     `ATTR_CMNEXT_CLONEID` together with full-clone evidence as positive
     `protected_full_clone_visible` evidence inside an enumerated writable root. Missing capability,
     incomplete scans, permission failure, deleted clones, and partial or diverged clones remain
     `unverified`. Absence of a detected clone never proves confinement.
   - **No approval-capable IPC:** the core exposes none, and core sockets must not be reachable
     through `allowUnixSockets`.
4. **Status derivation (normative).** Core can prove a setup is *unsafe*, never that it is safe, so
   it never reports `confined`. The status fields are:
   - `profile`: `installed` / `missing` / `drifted` / `unverified`. The first three require a
     complete, core-observed effective-settings snapshot covering every normative source and
     precedence layer. Confirmed absence yields `missing`; unreadable, incomplete, unsupported or
     ambiguously merged settings yield `profile: unverified`, `confinement: unverified`, reason
     `effective_settings_unobservable`. `installed` means only that the required security-relevant
     projection matches; it is never a confinement claim;
   - `confinement`: `not_in_effect` or `unverified`.

   `not_in_effect` requires positive, core-observed evidence. Examples:
   - a core-issued nonce canary write, socket connect or Apple Event that *succeeded*;
   - an escape key or launch flag visible in a core-observable source (merged settings, host argv or
     the permission mode reported to hooks, as S04 records per host version);
   - an install or Vault path inside a writable root.

   Everything else is `unverified`, including skipped, misdirected or agent-reported-only probe legs
   and launch-time settings that core cannot observe.

   Rules:
   - Evidence is bound to a session key: the host session ID delivered to the SessionStart hook
     where available, otherwise the MCP server process lifetime (which cannot observe compact or
     resume). `COMPATIBILITY.md` records which key each host version uses. Resume, fork or compact
     starts a new session. Evidence is never carried across sessions.
   - Labels, env vars, adapter fields and config keys cannot change the status.
   - Status sent to a host, and written to `views/Status.md` (which host tools can read), is an enum
     plus fixed reason codes only. Full detail is printed by the CLI, which an agent shell can also
     run where read-deny is unsupported (THREAT_MODEL non-claims).
   - Status detects misconfiguration of a cooperating session. It cannot attest confinement against an
     agent that is already unconfined.
   - Where hosts support it, the profile also denies host-tool *reads* of the Vault and state paths.
     Where they don't, the preview says so (THREAT_MODEL non-claims).
   - A newly installed profile covers only newly launched host sessions; setup tells the user to
     relaunch.
5. **Out-of-band edits are detected, not trusted.** Detection is a stat/hash gate against the
   hash-chained change log. It runs before every policy decision and in each journal-worker recheck,
   not only on load.
   - A purely narrowing edit is honored immediately.
   - These edits are quarantined as a whole until item-2 confirmation:
     - any edit that widens exposure or accepts a candidate;
     - a mixed narrow+widen edit;
     - a record moved or retagged into an exposed module.
   - A content edit to an already-exposed record is re-reviewed before its next remote egress.
   - Restore, migration and import re-verify against the current log and route widening through
     confirmation. They never re-baseline the log.
   - Detection catches uninformed edits only and is not a security boundary.
6. **Deferred effects recheck policy.** Approval expiry bounds effect *start*. Before each disclosing
   network/provider effect a worker rechecks the grant and epoch.
   - A revoked or narrowed grant ends the intent in `cancelled_policy`.
   - An unrelated epoch bump re-evaluates the effect instead of cancelling it.
   - Purge always continues.
   - Exactly one durable intent; effects run at least once through idempotent adapters or dedupe keys.
7. **No overrides; test doubles are isolated.**
   - A test enumerates every CLI flag, env-var prefix and config key and asserts that none changes the
     approval verdict, the approver or the status.
   - Fake proven-local hosts and confinement probes live only under `tests/` (never a separate package). They are excluded from
     the sdist explicitly, and Slice 1 asserts they are absent from the wheel and from any installed
     import path.
8. **Accepted residual risk.**
   - A same-user host running unconfined can change the local profile and policy without product
     approval.
   - A user can approve an action whose terminal preview they did not read.
   - A user who approves a host escalation request for this CLI lets an agent-composed command commit
     unconfined (item 2).
   - Hardware-backed approval is a future ADR.

## Consequences

- **Positive:**
  - Removes the ApprovalBroker, enrollment and test-authenticator surfaces from the MVP.
  - Every security claim becomes testable on macOS 26.2 with the real hosts.
- **Negative / risks:**
  - Protection depends on the host sandbox, and host setting keys can change between versions. S04
    and S12 re-probe per host version. Observable drift yields `profile: drifted`, and `not_in_effect`
    only with positive evidence; an unrecognized host version yields `unverified`.
- **Follow-ups:**
  - Update THREAT_MODEL, ADR indexes, SPIKES S04, plans 00/01/02, COMPATIBILITY and ROADMAP to
    reference this ADR.
  - Write a hardware-backed approval ADR before any release that markets stronger approval.

## Verification

S04 (per host) and Foundation Slice 7 run these tests, each with a binary pass criterion:

- **Terminal-only approval.**
  - MCP/model text cannot approve.
  - An agent-invoked approval inside a confined session fails closed with a content-free code, and so
    does an SDK-level approve from inside the sandbox.
  - A source or module name containing `$(…)`, a backtick, `'`, `\`, `;` or a newline appears only
    as delimited data in the terminal preview and never on a command line.
  - An unknown or prefix-only action ID is rejected (exact match only).
  - An import/call-graph test proves MCP, hook and worker entry points cannot reach the approve
    service; enumeration of MCP tool and hook input schemas finds no token, nonce or approval field;
    a confined agent that has read pending-action and nonce state cannot commit through any MCP tool,
    hook payload or worker trigger.
  - Under the Codex profile, an escalation request for an approve command is either not offered or
    the status carries `host_escalation_available`.
  - An agent write of a hook/MCP entry to project settings is denied, or the next session reports
    `not_in_effect`.
  - A changed digest, a replayed nonce, a stale epoch or a widened scope is denied.
  - `PYTHONPATH`/`PYTHONSTARTUP` or a workspace shadow module does not alter the approver.
- **Status never reports `confined`.**
  - Any core-observed successful canary (write, socket, Apple Event) or observable escape key or flag
    yields `not_in_effect`.
  - A skipped or misdirected probe leg, or an escape set only by an unobservable launch flag, yields
    `unverified`.
  - An unreadable, incomplete, unsupported or ambiguously merged effective-settings snapshot yields
    `profile: unverified` and confinement `unverified`; only confirmed absence in a complete snapshot
    yields `profile: missing` and `not_in_effect`.
  - Symlink/hardlink/rename aliases are detected by canonical path plus device/inode. Portable clone
    checks and incomplete native scans remain `unverified`; a detected full clone may only add the
    positive reason `protected_full_clone_visible`.
  - A forged label or env var changes nothing.
  - Evidence from session N is absent in session N+1.
- **Leaks.**
  - A marker path never appears in host-bound status or in `views/Status.md`.
  - A marker read through host file tools is denied where the host supports read-deny, or disclosed
    in the preview otherwise.
- **Out-of-band edits.**
  - Narrowing is honored.
  - Widening, mixed and retag edits quarantine.
  - A content edit to an exposed record is re-reviewed before its next remote egress.
  - Restore, migration and import never re-baseline the change log.
- **Deferred effects.** Revoking egress after journal commit leaves no network effect and ends in
  `cancelled_policy`. An unrelated epoch bump re-evaluates the effect.
- **Overrides and packaging.**
  - The flag/env/config enumeration test shows no override.
  - Test doubles are absent from the wheel and the sdist.
- **Regression.** Crash and concurrency cases from ADR-0005 and ADR-0010 still pass.

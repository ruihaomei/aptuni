# Security and Privacy Fourth Re-review (focused)

- **Date:** 2026-09-18
- **Reviewer:** independent security/privacy reviewer (no prior context; repository is the only source)
- **Responds to:** `09-security-privacy-remediation.md` and `DECISIONS/ADR-0013-honest-host-trust-boundary.md`
- **Supersedes:** `09-security-privacy-third-rereview.md`

## Scope

This review checks the contract the maintainer chose in ADR-0013: an honest enforcement boundary plus
control (a), host confinement, with the host-shell residual risk accepted. The scope choice is **not**
re-litigated. A hardware broker would be stronger, but that is not a finding here. The review asks
four questions:

1. Is the contract stated honestly and consistently?
2. Can it be implemented on macOS 26.2 with Claude Code 2.1.87 and the Codex CLI?
3. Is it covered by binary tests?
4. Does it have gaps *inside* its declared scope?

Documents read in full or in the relevant sections:

- ADR-0013, ADR-0005, ADR-0010, ADR-0011 and ADR-0012
- `THREAT_MODEL.md` and `SPIKES.md` (S04, S12)
- plans 00, 01 and 02
- `COMPATIBILITY.md`, `KNOWN_ISSUES.md`, `ROADMAP.md`, `MVP_DEPENDENCY_GRAPH.md`, `STATE.md` and `HANDOFF.md`
- remediation 09, review 09, and PRD §16

Host behaviour was checked against the current Claude Code sandboxing documentation
(`code.claude.com/docs/en/sandboxing`, fetched 2026-09-18). Those docs describe versions newer than
2.1.87 in places, so every host claim below is framed as an S04 verification item, not a settled fact.

## Commands run

```text
grep -rniE "ApprovalBroker|FIDO|WebAuthn|authenticator|out-of-band/scoped|interactive flow|strong confirmation|exactly-once|human presence" docs AGENTS.md CLAUDE.md | grep -v docs/dev/reviews/
grep -rniE "cannot approve|host shell|user presence|..." docs/dev docs/product AGENTS.md CLAUDE.md   (overclaim sweep)
grep -rn -iE "per-session|drift" docs/dev                                               (N4 drift definition)
claude --version        → 2.1.87 (Claude Code)
which codex             → not found (KI-015 confirmed)
sw_vers                 → macOS 26.2 (25C56)
python3.13 tools/check_relay.py               → "relay check passed" (before this report was added)
python3.13 -m unittest tests/dev/test_check_relay.py → Ran 19 tests, OK
```

The leftover-term grep returns only the following, all of which are acceptable:

- history and status lines: `STATE.md:22`, `KNOWN_ISSUES.md:14` (KI-011), `HANDOFF.md:26`;
- ADR-0013's own supersession, context and options text;
- `THREAT_MODEL.md:69` ("not proof of human presence"), which is a correct disclaimer.

The broader overclaim sweep found two normative leftovers. They are reported under H4-1.

**Note for the caller.** After this report is added, `check_relay.py` will fail with "review report is
absent from lineage manifest" until `reviews/STATUS.json` is updated:

- security `current` → `12-security-privacy-fourth-rereview.md`;
- add `09-security-privacy-third-rereview.md` to `supersedes`;
- verdict `BLOCK`.

The STATE/HANDOFF summary line stays `security=BLOCK`. This reviewer was not permitted to edit those files.

## Disposition of prior findings

| ID | Prior severity | Disposition | Evidence / residual |
|---|---|---|---|
| B2-R3 | Blocking | **Closed as a boundary statement; the control is not yet testable (see B4-1)** | The enforcement boundary is stated exactly and consistently: ADR-0013:51-54, `THREAT_MODEL.md:67-78`, ADR-0005:46-50, ADR-0012:36-38, residual risk at `THREAT_MODEL.md:181-182`. Control (a) is named for both hosts (ADR-0013:65-72). Two leftover overclaims remain (H4-1). The `doctor` status that the honesty of the whole contract depends on has no defined derivation and no false-positive test (B4-1). |
| H-A | High | **Closed at planning level** (Low note L4-1) | No authenticator exists. Doubles are under `tests/` or a test-only package, with a wheel/sdist assertion (ADR-0013:95-97, plan 01:126-128, `THREAT_MODEL.md:168-170`). "No env/flag disables the guard" is stated as a rule but is not a binary test (M4-4). The assertion is cited as "Slice 1" but is not listed in Slice 1's steps or Done line (plan 01:37-51). |
| H-B | High | **Moot as written; recurs in a new form (H4-2)** | With no broker, the authenticator display problem is gone. However, the human now decides at the *host's* approval prompt. That prompt shows the command line (for example a digest prefix) plus the agent's own chat text. The human never sees the core-rendered preview before deciding. |
| N3 | Medium | **Closed** (Low note L4-3) | Grant and epoch are rechecked before each disclosing effect, ending in `cancelled_policy`, and purge continues: `THREAT_MODEL.md:85-87`, ADR-0013:88-93, abuse case 9 (`THREAT_MODEL.md:171-172`), plan 00:71-73. Missing: the S04 acceptance text (SPIKES:71-84) omits the test, "approval expiry bounds effect start" was not adopted, and the treatment of an unrelated epoch bump is unspecified. |
| N4 | Medium | **Closed for MVP** (Low note L4-2) | Test-only placement plus the artifact assertion. Remediation 09 says the per-session adapter/runtime hash recheck "remains the drift definition", but no normative doc contains it: `THREAT_MODEL.md:139` and ADR-0005:77 say only "drift revokes admission". Impact is low because MVP denies `proven_local` for the real hosts. |
| N5 | Low | **Closed** | "exactly one durable intent; effects at least once …" appears at `THREAT_MODEL.md:84-85` and ADR-0013:93. The generic confirmation terms are replaced by ADR-0013 references (`THREAT_MODEL.md:48,58,92,150`, ADR-0010:49, ADR-0011:42). KI-011 is updated. Plan 00:72 still says "idempotent exactly-one durable intent", which is acceptable. |

## New findings

### B4-1 — Blocking: the confinement status can overstate protection, and nothing tests that it doesn't

The contract works only if the user is told truthfully when protection is not in effect. ADR-0013:74-80
promises that "wording never overstates the protection". It defines `confined` as "OS-enforced sandbox
verified" and lists "bypass-permissions or full-access mode" as `not_in_effect`. No document defines
*how* `doctor` derives the status, and the derivation matters.

**1. Per-session runtime state is invisible to a config-file check.** Both hosts accept launch flags
that override the settings files:

- Claude Code: `--dangerously-skip-permissions`, `--permission-mode`, `--settings '{…}'`;
- Codex: `--dangerously-bypass-approvals-and-sandbox`, `-s danger-full-access`, `-c key=value`.

A `doctor` that reads `~/.claude/settings.json` or `~/.codex/config.toml` will report `confined` for
a session launched with bypass flags. So will a status computed during onboarding and then cached
(plan 02:20-22, 56-57).

ADR-0013:109-110 re-probes only "per host version", not per session. The "drift degrades to
`not_in_effect`" rule presupposes a detector that is never specified.

**2. Labels could elevate the status.** For `proven_local` the plan says "user/host/config labels
cannot elevate the class" (`THREAT_MODEL.md:136-139`). There is no equivalent rule for the
confinement status. Nothing forbids a config key, env var or adapter-declared field such as
`confinement: confined`, and ADR-0013:64 forbids only env/flag keys that *disable the guard*.

**3. Claude Code's OS sandbox covers only part of the host.** It applies to Bash, PowerShell and
Monitor commands and their children. It does **not** cover the Edit/Write tools, which are governed
by permission rules evaluated by the host rather than by the OS.

"Sandbox + permission rules" (ADR-0013:70) is therefore partly OS-enforced at best, and
`confined: OS-enforced sandbox verified` would overstate the Edit-tool path. The escape hatches also
change the answer:

- `allowUnsandboxedCommands` (retry outside the sandbox, auto-approved in auto mode);
- `excludedCommands` (appendable from any settings scope);
- `allowAppleEvents`;
- `allowUnixSockets`;
- `--add-dir` / `additionalDirectories` covering the Vault.

**4. The binary test lacks the false-positive direction.** S04 (SPIKES:75-76, plan 00:66-69) and
ADR-0013:122-123 accept "blocked … **or** `doctor` reports `not_in_effect`". Nothing requires that
`doctor` **never reports `confined`** when a write actually succeeds.

**Actions (required before APPROVE):**

- **Define the derivation normatively in ADR-0013 item 4.** The status is the minimum of two results:
  - the effective merged host settings, including every protected key listed in H4-3;
  - a **live in-session probe** run through the host's own shell tool and its file-edit tool. The
    probe attempts a canary write under the Vault, config/grant/state and install paths. Any success
    means `not_in_effect`.
- **Never cache a status across sessions.** Record the probe time and the host version.
- **State what core cannot observe.** For example: a later relaunch with bypass flags, or a user's
  `!` shell. Word the status as "verified for the probed session at <time>", never as a standing
  guarantee.
- **Add the rule "labels, env vars and config keys cannot raise the status"**, mirroring the
  `proven_local` rule.
- **Define `confined` per host.** For Claude Code, the Bash sandbox plus Edit/Write deny rules must
  both be verified by the live probe. If the Edit path is rule-only, name that in the status reason.
- **Add S04/Slice 7 negative tests with binary pass criteria.** For each host, launch with each
  bypass/full-access flag, with `allowUnsandboxedCommands` true in auto mode, with the Vault inside a
  writable root or `--add-dir`, and with a forged status label or env var. For each case, assert that
  `doctor` does not report `confined` and that the next status notice says `not_in_effect`.

### H4-1 — High: two normative leftovers still overclaim

Each of the following contradicts ADR-0013:51-56 and must be corrected before APPROVE.

- **ADR-0005:92-93: "prove MCP/CLI/host shell cannot approve".** Under ADR-0013 the CLI *is* the
  approval path. An unconfined host shell *can* approve, which is the accepted residual risk. Replace
  this with: "prove MCP/model text cannot approve; a confined host agent cannot complete approval
  without the host's human prompt; an unconfined host is out of scope (ADR-0013 item 8)."
- **`ROADMAP.md:98-99`: "MVP deliberately requires verified user presence".** ADR-0013:55-56 and
  `THREAT_MODEL.md:68-69` say the opposite ("not proof of human presence"). Replace this with "MVP
  requires the ADR-0013 confirmation".
- **Consequence for PRD §16.** PRD §16 ("NOT held back awaiting approval") is already overridden by
  ADR-0011:42 and the roadmap. No change is needed beyond keeping that override explicit.

### H4-2 — High: the human does not see the core-rendered preview when deciding at the host prompt

ADR-0013:57-63 and `THREAT_MODEL.md:69-71` require that "the core renders the preview … never
requester-supplied text" and that the host prompt gates approval. In the flow as specified, the agent
invokes `review approve <digest-prefix>`, and the host prompt shows that command string. The only
human-readable description available at decision time is the agent's own chat message. The core's
rendering appears only in the CLI's output, *after* approval.

An instruction-injected agent can therefore describe digest `ab12…` as benign and obtain approval for
a harmful action. This is the H-B attack in a new form. The ADR claims to guard against "MCP-injection",
which overstates what it provides. The requirement "core-rendered preview" is testable only as "the
CLI prints it", not as "the human saw it before approving".

**Actions (pick one and state it):**

- **(a) Bind the rendering into the command.** The approval command must carry the core's canonical
  one-line summary, for example `review approve --digest ab12… --expect "<canonical summary>"`. The
  CLI rejects the command unless `--expect` byte-equals the core's rendering of the digest, so the text
  shown in the host prompt is core-verified.
  - Cap and normalize the summary: no control characters and no bidirectional or zero-width Unicode.
  - Test with a mismatched `--expect` string, a truncated string and a homoglyph string.
- **(b) Downgrade the claim.** THREAT_MODEL and ADR-0013 would state that a deceived user can approve
  any pending action at the host prompt. In that case, drop "MCP-injection guard" and keep only
  "MCP cannot self-approve; accidental-action guard".

### H4-3 — High: the confinement profile has no complete required-key list or escape-surface tests

ADR-0013:65-72 names only "workspace-write + on-request" (Codex) and "sandbox filesystem restrictions
+ permission rules" (Claude Code). KI-014 correctly defers the exact keys to S04. However, the
acceptance criteria (SPIKES:75-78, plan 00:66-69) test only a direct write to the Vault/config paths.
The following in-scope escape surfaces are neither required nor tested.

**Surface 1: host escape settings.**

- Claude Code: `sandbox.enabled`, `allowUnsandboxedCommands`, `excludedCommands` (merged from all
  scopes), `allowAppleEvents`, `allowUnixSockets`, `filesystem.disabled`, `allowWrite` and
  `additionalDirectories` covering protected paths, and permission mode (auto/bypass).
- Codex: `sandbox_mode`, `approval_policy`, `sandbox_workspace_write.writable_roots`, network access,
  and profile overrides.

**Surface 2: host config that runs code outside the sandbox.** This covers hooks, MCP server
definitions and plugin/adapter files. The Claude Code adapter itself relies on a SessionStart
`command` hook (research 05:229-231), and hooks run outside the sandbox.

The current Claude Code docs say that project `.claude` settings, hooks and `.mcp.json` are
write-protected inside the sandbox. However:

- user-scope `~/.claude/…` and installed plugin/adapter files are protected only if they lie outside
  every writable root;
- Codex's protection of `.codex`/`.git` must be verified for the pinned versions.

**Surface 3: the install path.** A project-local `.venv`, as created by `uv`, sits inside the
workspace writable root. There the agent can patch the policy code. ADR-0013:77-78 names only "Vault
inside a writable root".

**Surface 4: path indirection.** This includes symlinks and **hardlinks** created from a writable root
to Vault/state files, rename or move of a protected directory, and APFS clones. Seatbelt rules are
path-based, so a hardlink inside a writable root to a Vault file inode needs an explicit test.

**Surface 5: local IPC.** A sandboxed agent could reach an unsandboxed core process (the MCP server,
or any future lock or daemon socket) through a Unix socket. The core must expose no approval-capable
IPC, and `allowUnixSockets` must not cover core sockets.

**Actions:**

- Make the required-key list normative, filled in by S04 per host version, in `COMPATIBILITY.md`.
- Treat any required key found missing, overridden or appended as `not_in_effect`, or as
  `partially_confined` with a named reason.
- Add S04 adversarial cases with binary pass criteria for each surface above. The pass criterion is
  that the write or escalation is blocked or prompted, and that `doctor` does not report `confined`
  when it is not.
- Add "installed package path inside a writable root" to the `not_in_effect` conditions.

### M4-1 — Medium: `partially_confined` semantics are not honest enough

Permission-rule "ask" prompts match command strings. They can be bypassed with `python -m …`,
`sh -c`, aliases, or by importing the in-process SDK directly (plan 01:134). ADR-0013:62 says approval
is "available only as a core CLI subcommand", but at code level the SDK's approve service is callable
by any same-user Python process. The only real stop is the OS sandbox's write denial.

**Action:** Define `partially_confined` as "accidental-action friction only; provides no protection
against an injected agent". Restate ADR-0013:61-62 as "the only *supported* approval surface is the
CLI subcommand; in-process callers are stopped only by OS confinement". Add a test showing that an
SDK-level approve call from inside the confined sandbox fails closed because it cannot commit.

### M4-2 — Medium: the approval path is undefined when the host cannot or will not prompt

Several configurations have no way to reach the host prompt:

- Codex with `approval_policy=never`;
- Claude Code in strict mode (`allowUnsandboxedCommands: false`) without an `excludedCommands` entry;
- plan 02 case D ("no supported host");
- MCP-only hosts.

In each of these, an agent-invoked approval cannot commit. A sandboxed command cannot write the
nonce store or the Vault, which is the correct fail-closed behaviour, but no documented path remains.

**Action:** Name "user runs the approval subcommand in their own terminal" as the canonical fallback
in ADR-0013 item 2 and plan 02. Test that a sandboxed invocation fails closed with a content-free
reason code.

### M4-3 — Medium: out-of-band edit detection has gaps in timing, classification and restore

ADR-0013:81-87 says detection runs "on load" and that narrowing is "honored immediately".

**1. Long-running processes.** A long-running MCP server would not observe edits between loads.
Narrowing would not be immediate, and a process that re-reads grant files without verification would
honor a widening edit.

**Action:** Run detection before every policy decision (stat or hash gate) and in the journal worker
recheck (item 6).

**2. Classification.** The following cases need explicit rules:

- **Mixed edits.** An edit that narrows one field and widens another must be quarantined as a whole.
- **Module membership and location.** Moving or retagging a record into an exposed module widens
  exposure, but it is not "review, grant or policy state" as listed.
- **Content edits to already-approved exposed records.** An Obsidian edit to such a record changes
  what is disclosed. Define whether it is widening, and route it at least through re-review before
  its next *remote* egress.

**3. Other application-service paths.** Restore from backup, migration and import must re-verify
against the current change log and send any widening through confirmation. They must not re-baseline
the log.

**Action:** Add Slice 7 and ADR-0010 restore tests for these cases.

### M4-4 — Medium: several binary tests are missing from the S04 and Foundation criteria

Required item (c) of this review is only partly covered:

- **S04 acceptance text (SPIKES:71-84) omits three tests.** It lacks narrowing-honored,
  revoked-egress → `cancelled_policy`, and the no-env/flag test. Plan 00 step 5 has the
  revoked-egress test, but the acceptance text should match the plan.
- **"No env/flag/config disables the guard" is a statement, not a test** (ADR-0013:64, plan 01:127).
  Add a test that enumerates every CLI flag, env var prefix and config key, and asserts that none
  changes the approval verdict, the approver or the status. It must also cover status overrides
  (B4-1).
- **The wheel/sdist assertion is attributed to Slice 1 but absent from Slice 1** (plan 01:37-51).
  Add it to Slice 1's steps and Done line.

### M4-5 — Medium: the status and notice can leak personal data to the host model

`doctor`, onboarding and the "rate-limited notice" (ADR-0013:74) are delivered through the agent
(Bash output or MCP results). That delivery is `host_model_egress` to a remote or unknown host.
Reasons such as "Vault inside writable root /Users/<name>/…" would disclose local paths and
identities. The diagnostic boundary (`THREAT_MODEL.md:124-125`) redacts only "before persistence".

**Action:** Status output to a host is an enum plus fixed reason codes, with no paths, usernames,
Vault names or source names. Full detail is shown only on the user's local TTY. Add a marker-path
test to the status output under strict local-only mode.

### M4-6 — Medium: onboarding ordering and profile installation

Plan 02:20-22 correctly reports the status before it creates grants. Two problems remain:

- **The reported status comes too early.** The profile is installed *during* a host session. For
  Codex and for launch-flag cases, that session's sandbox was fixed at launch. A status reported
  immediately after installation cannot be `confined` for the current session (B4-1).
- **The profile source is unspecified.** If a host agent drives onboarding and writes the profile
  itself, it can install a weakened one.

**Actions:**

- The core CLI writes the profile from package-bundled content, and `doctor` diffs the effective
  settings against it.
- The status stays `not_in_effect` until a new host session passes the live probe.
- The SetupPlan preview lists the host settings files that will be modified; changing a user's global
  host settings is a consequential action.

### Low

- **L4-1.** An sdist conventionally includes `tests/`. Either exclude test-double modules from the
  sdist explicitly or restate the assertion as "absent from the wheel and from any installed import
  path". The same applies to a test-only package published separately.
- **L4-2.** Put the N4 per-session adapter/runtime hash recheck (the drift definition) into
  `THREAT_MODEL.md:136-139`, or drop the claim from remediation 09.
- **L4-3.** For N3, state that the approval expiry bounds *effect start*. Also define that an unrelated
  epoch bump re-evaluates the effect rather than cancelling it.
- **L4-4.** The Codex CLI is absent on the Gate 0 host (KI-015). ADR-0013's Codex mechanism
  (workspace-write + on-request; approval via a sandbox-denial → escalation prompt) is plausible but
  unverified. Keep KI-014/KI-015 as S04 blockers, and record whether a Codex rules/execpolicy
  "prompt" rule is available for the pinned version.
- **L4-5.** The "one rate-limited notice" must reach the human, not only the model. Specify the
  surface: the host UI or the user TTY.

## Implementability summary (macOS 26.2, Claude Code 2.1.87, Codex)

| Requirement | Claude Code | Codex | Verdict |
|---|---|---|---|
| Deny agent writes to Vault/config/install | Bash: Seatbelt `sandbox.filesystem.denyWrite`/cwd-only writes. Edit/Write: permission deny rules only | workspace-write with paths outside writable roots | Feasible. Claude Code is partly rule-based (B4-1, H4-3) |
| Approval only through a human prompt | Sandbox-denied commit → unsandboxed retry or `excludedCommands` + ask rule → prompt | Sandbox-denied → escalation request under on-request | Feasible, but the prompt shows command text only (H4-2) |
| MCP cannot approve | No approve tool; static import test | Same | Feasible and testable |
| Live status | In-session canary probe through Bash and Edit | In-session probe through the shell tool | Feasible, but not specified (B4-1) |
| Quarantine of widening edits | Core-only | Core-only | Feasible, with gaps (M4-3) |
| Revoked egress → `cancelled_policy` | Core-only | Core-only | Feasible and specified |

## Re-review gate checklist

- [x] The enforcement boundary is stated exactly, and the residual risk is accepted by the maintainer
      and recorded (ADR-0013, THREAT_MODEL).
- [x] No broker/FIDO2/authenticator/enrollment requirement remains in normative docs.
- [ ] No normative claim that core stops an unconfined host shell or verifies user presence remains
      (H4-1: ADR-0005:92-93, ROADMAP:98-99).
- [ ] The confinement status derivation is defined (effective settings + live in-session probe), is
      not elevatable by labels, is never cached across sessions, and has false-positive tests for
      bypass/full-access flags (B4-1).
- [ ] The required host-setting keys and escape surfaces (escape hatch, excluded commands, hooks/MCP
      config, install path, symlink/hardlink, Unix sockets) have binary S04 tests (H4-3).
- [ ] The human sees a core-verified rendering before approving, or the claim is downgraded (H4-2).
- [x] MCP cannot approve (binary S04/Slice 7 test).
- [ ] Narrowing-honored, widening-quarantined, revoked-egress, no-env/flag and wheel/sdist tests
      appear in the S04 acceptance text and in Slice 1/Slice 7 Done criteria (M4-4).
- [x] Deferred effects recheck grant and epoch; `cancelled_policy` is terminal; purge continues (N3).
- [x] Test doubles live under `tests/` or a test-only package with no runtime selector (H-A, N4).
- [x] Wording "exactly one durable intent; effects at least once" is used (N5).

**Final judgment:** The maintainer's chosen contract is sound in shape and mostly stated honestly. The
ApprovalBroker, FIDO2 and authenticator surfaces are gone, and N3–N5 are closed. The contract's
remaining security promise is that the user is told truthfully when confinement is not in effect.
That promise is currently neither defined nor falsifiable: runtime bypass flags and label-derived
status could yield `confined` with no protection, and no test forbids it (B4-1).

Fixing B4-1 and H4-1 needs small documentation and test-criteria edits. H4-2 and H4-3 should land in
the same pass, because B4-1's probe depends on H4-3's key list.

**Verdict:** **BLOCK**

# Security and Privacy Fifth Re-review (focused)

- **Date:** 2026-09-18
- **Reviewer:** independent security/privacy reviewer (no prior context; repository is the only source)
- **Responds to:** `12-security-privacy-remediation.md` and the amended
  `DECISIONS/ADR-0013-honest-host-trust-boundary.md`
- **Supersedes:** `12-security-privacy-fourth-rereview.md`

## Scope

This is a focused re-review of the report-12 findings (B4-1, H4-1 to H4-3, M4-1 to M4-6, L4-1 to L4-5)
at **planning level**. The maintainer's honest-boundary scope is accepted and not re-litigated:
same-user unconfined hosts are inside the trust boundary, host confinement is the control, and no
hardware broker is requested. Exact host setting keys are deferred to S04. That deferral is accepted
because unfilled `COMPATIBILITY.md` rows cap status at `unverified` (fail-closed). Spikes not having
run is expected and is not a finding.

Files read: ADR-0013 (full), ADR-0005 (§Decision, §Verification), `THREAT_MODEL.md` (full),
`COMPATIBILITY.md` (full), `KNOWN_ISSUES.md`, `SPIKES.md` S04, `ROADMAP.md` M2, plans 00 (S04 steps),
01 (Slices 1, 7) and 02 (full), remediation 12, report 12, `reviews/STATUS.json`, and the STATE/HANDOFF
status lines.

## Commands run

```text
grep -rniE "ApprovalBroker|FIDO|WebAuthn|authenticator|MCP-injection guard|verified user presence|exactly-once" \
     docs AGENTS.md CLAUDE.md | grep -v docs/dev/reviews/
  → only ADR-0013:8, 25, 36-37, 149 (its own supersession/options/consequences text). Clean.
grep -rniE "denyRead|read access|agent read|can read" docs AGENTS.md CLAUDE.md      → no hits (see H5-3)
grep -rniE "session id|session_id|session identity|new session" docs               → no normative definition (see M5-1)
grep -rniE "prefix" docs/dev/DECISIONS docs/dev/THREAT_MODEL.md docs/dev/plans    → only ADR-0013:62 (see H5-1)
claude --version            → 2.1.87 (Claude Code)
which codex                 → not found (KI-015 still open)
sw_vers                     → macOS 26.2 (25C56)
python3.13 tools/check_relay.py   → "relay check passed" (before this report was added)
```

**Note for the caller.** After this report is added, `check_relay.py` fails with "review report is
absent from lineage manifest" until `reviews/STATUS.json` is updated:

- security `current` → `13-security-privacy-fifth-rereview.md`;
- add `12-security-privacy-fourth-rereview.md` to `supersedes`;
- set the verdict to match the final line of this report.

The reviewer was not permitted to edit those files.

## Disposition of report-12 findings

| ID | Sev. | Disposition | Evidence / residual |
|---|---|---|---|
| B4-1 | Blocking | **Partially closed; residual is blocking (B5-1)** | The derivation is now normative and consistent: minimum of the settings check and the live probe, never cached, `unverified` default, labels cannot raise it, and Claude Code carries `edit_tool_rule_based` (ADR-0013:93-115, `THREAT_MODEL.md:76-79`, `COMPATIBILITY.md:46-48`, plan 02:24-25, 59-62). False-positive tests exist (ADR-0013:170-174, SPIKES:75-77). However, the specified derivation can still yield a false `confined` (B5-1). |
| H4-1 | High | **Closed** | ADR-0005:92-94 now reads "prove MCP/model text cannot approve … an unconfined host is out of scope". `ROADMAP.md:98-99` now reads "requires the ADR-0013 confirmation, overriding PRD §16 for MVP". The leftover grep is clean. |
| H4-2 | High | **Closed in shape; the chosen mechanism introduces a new blocking defect (B5-2) and gaps (H5-1)** | Option (a) is adopted: ADR-0013:62-66, `THREAT_MODEL.md:69-72`, plan 02:20-22, and mismatch/truncation/homoglyph tests at ADR-0013:169. "MCP-injection guard" is dropped, and the deceived-user risk is accepted at ADR-0013:72-73 and 143. |
| H4-3 | High | **Closed at planning level** (with H5-2) | Key families per host: ADR-0013:80-88. Normative table: `COMPATIBILITY.md:44-59`. Fail-closed rule for unfilled rows: `COMPATIBILITY.md:47-48`. Install path outside writable roots: ADR-0013:77-79. Real-path/inode rule: ADR-0013:89-90. No approval-capable IPC: ADR-0013:91-92. Every surface has a Verification case (ADR-0013:170-174). The Claude Code approval-routing contradiction is raised as H5-2. |
| M4-1 | Medium | **Closed** | ADR-0013:55-58, 101-102 and 167. |
| M4-2 | Medium | **Closed** | ADR-0013:69-71, plan 02:21-22 and ADR-0013:166. |
| M4-3 | Medium | **Closed** (Low note L5-3) | ADR-0013:116-127 and plan 01:129-131. There is no Verification case for "content edit to an exposed record re-reviewed before remote egress" or for migration/import (L5-3). |
| M4-4 | Medium | **Mostly closed** (M5-2) | S04 acceptance references every Verification case (SPIKES:75-81). The enumeration test is at ADR-0013:135-136 and 181. The wheel/sdist check is in Slice 1 step 7 and its Done line (plan 01:49-53). Plan 00 step 4 and the Slice 7 Done line lag behind (M5-2). |
| M4-5 | Medium | **Closed for the MCP/stdout channel; undermined by host file reads (H5-3)** | ADR-0013:113-115, `THREAT_MODEL.md:128-129`, and the marker-path test at ADR-0013:180. |
| M4-6 | Medium | **Closed** | ADR-0013:75-76, 104-106 and plan 02:20-25. |
| L4-1 | Low | **Closed** (L5-2 wording) | ADR-0013:137-139 and plan 01:49-50. |
| L4-2 | Low | **Closed** | `THREAT_MODEL.md:144-145`. |
| L4-3 | Low | **Closed** | ADR-0013:128-131 and 178. |
| L4-4 | Low | **Open as intended (S04)** (L5-1) | KI-014/KI-015. The Codex rows in `COMPATIBILITY.md:56-58` are pending. |
| L4-5 | Low | **Closed** | ADR-0013:114-115. |

## New findings

### B5-1 — Blocking: the specified probe treats "no observed success" as a pass, so `confined` can still be false

ADR-0013:94-96 defines the probe as canary writes attempted "through the host's own shell tool **and**
its file-edit tool", and says "any success means `not_in_effect`". Two properties of that definition
contradict the promise that status never reports `confined` falsely (ADR-0013:170):

1. **The file-edit leg is agent-executed and absence-based.** Core cannot call the host's Edit/Write
   (Claude Code) or apply_patch (Codex) tool; the model must do it. If the model skips the step,
   targets the wrong path, or reports a failure it never produced, no canary appears. The rule as
   written then scores the leg as passed. This happens with an ordinary unreliable model, not only an
   injected one. No Verification case covers it: every case in ADR-0013:170-174 varies the *host
   configuration*, never the *probe execution*.
2. **Launch-time configuration that is not a file-write surface is invisible to both legs.** The
   settings check reads merged settings files. For example, Claude Code `--settings '{…}'` can set
   `allowUnsandboxedCommands`, `excludedCommands` or `allowUnixSockets`; Codex `-c`/`--profile` can do
   the same. Launch-time settings like these are not in any file. The probe tries only direct canary
   writes, and the sandboxed doctor process correctly gets EPERM. So both legs pass, yet in auto or
   bypass mode the agent can escape through an auto-approved unsandboxed retry, an excluded command, a
   core socket or Apple Events. S04 would expose this, because its
   "`allowUnsandboxedCommands` in auto mode" case will fail. But the normative derivation gives
   S04 no mechanism that could pass it.

**Required actions (planning text only):**

- ADR-0013 item 4: **a leg passes only on positive, core-observed, nonce-bound denial evidence.**
  - Shell leg: the core process itself observes EPERM or the sandbox denial on a fresh-nonce canary.
  - Edit leg: a host-originated record of the denied tool call for that nonce, for example a
    PreToolUse/PostToolUse hook entry written outside the sandbox, or Codex's own denial event.
  - A missing, unmatched or agent-reported-only result yields `unverified`, never a pass.
- **Anything core cannot observe caps status at `unverified`.** This covers inline `--settings`,
  `-c`/`--profile`, `--add-dir`, and unknown or unparsed host launch flags. Take the evidence from a
  core-observable source, such as the host process argv and the permission mode reported to hooks.
  S04 decides which source is reliable per host version and records it in `COMPATIBILITY.md`.
- **The probe covers every escape class in the required-key table, not only direct writes.**
  - An unsandboxed-retry request must be denied or prompted.
  - A connect attempt to a core-owned canary socket must fail.
  - An Apple Event canary must fail.
- **Add Verification/S04 cases with binary criteria:**
  - "edit leg not executed or misdirected → not `confined`";
  - "escape key set only via a launch flag → not `confined`".

### B5-2 — Blocking: the prescribed `--expect "<summary>"` form lets source-derived text run as shell code

ADR-0013:62 prescribes `--expect "<summary>"` in **double quotes**. The summary is only NFC-normalized
and stripped of control, bidi and zero-width characters (ADR-0013:65-66). No charset restriction or
shell-quoting rule exists. Summaries of candidate approvals and purges will include user- or
source-derived text: titles, filenames, module and source names.

A name containing `$(…)` or a backtick expression causes the command substitution to run in the host
shell when the command runs. That happens *before* the CLI can compare bytes. On Claude Code and Codex
the approved command is the one that runs outside the sandbox (via the unsandboxed retry, the excluded
command or the escalation). So an attacker who controls a source filename gets code execution outside
the sandbox as soon as the human approves what looks like a "core-verified summary".

This makes the claim "the command text shown at the host's approval prompt is core-verified"
(ADR-0013:63-64, `THREAT_MODEL.md:70-72`) false, and it creates a new path from source injection to
escape.

**Required actions:**

- The canonical summary uses a shell-inert charset. Either no `$ \` " ' \ ; & | < > ( ) { } * ? ! ~ #`,
  or untrusted fields are rendered as core IDs or short hashes rather than raw text.
- The adapter always emits the summary single-quoted, and the CLI rejects any `--expect` that differs.
- Tests: source and module names containing `$(…)`, backticks, `'`, `\`, `;` and newline. The approval
  command must execute nothing extra and must be rejected or produce an inert summary.

### H5-1 — High: the summary binding does not cover the security-relevant action fields, and prefix resolution is unspecified

- **Coverage and collisions.** ADR-0013:62-66 does not say what the summary must contain. The 160-char
  cap plus truncation lets two different actions share one summary. For example, a narrow and a wide
  purge whose scope names differ after character 160, or an egress grant whose destination is cut off.
  The human then approves a truthful but incomplete string.
  - **Action:** the summary must include, in core-controlled fixed-order fields, the action type, the
    scope cardinality and scope identity, egress provider/destination/data class (if any),
    irreversibility, and a digest prefix.
  - The summary must be injective over those fields. When a field cannot fit, host-prompt approval is
    refused and routed to the user's terminal with the full preview.
  - Untrusted fields are delimited and placed last. Confusable characters (UTS #39 skeleton) are
    flagged or rendered as IDs, because stripping bidi and zero-width characters does not stop
    homoglyph names inside the summary.
- **Digest prefix.** The minimum length and the ambiguity behaviour are undefined, and MCP can mint
  pending actions to grind a colliding prefix.
  - **Action:** require at least 64 bits of prefix, resolution to exactly one pending action, and
    rejection on ambiguity. The token binds the full digest (already at ADR-0013:67).
  - Test with two pending actions that share a short prefix.

### H5-2 — High: the Claude Code approval route conflicts with the required-key table, and the approving process can be hijacked

- **Routing conflict.** `COMPATIBILITY.md:52` requires "no unsandboxed retry or excluded command
  covering core CLI writes". But the approve CLI must write the nonce store and the Vault, which are
  protected paths. With neither escape available, an agent-invoked approval can never commit in
  Claude Code. That contradicts "the adapter profile routes the subcommand to the host's human prompt"
  (ADR-0013:68) and plan 00:68-69 ("must raise the host approval prompt").
  - **Action:** pick one and state it.
    - (a) Claude Code approval is terminal-only (the fallback at ADR-0013:69-71 becomes primary).
    - (b) An exact-match `excludedCommands` entry plus an `ask` rule for only the approve/confirm
      subcommand, with no other unsandboxed route. Record it as the single allowed exception in the
      required-key table.
- **Hijack of the unsandboxed approver.** Under (b), or under the Codex escalation, the approving
  process runs unsandboxed. An agent can prefix `PYTHONPATH=…`, `PYTHONSTARTUP`, a different `cwd`, or
  chain `; …` so that the process that runs is not the one the summary describes.
  - **Action:** the approval entry point runs an isolated interpreter (`-I`, or equivalent: ignore
    `PYTHON*`, no cwd or workspace on `sys.path`) from the install path outside writable roots. It
    refuses unexpected env or argv.
  - The exception pattern must not match prefixed or chained commands.
  - Add S04 tests for the env prefix, chaining and a workspace shadow module.

### H5-3 — High: host file tools can read the Vault and `views/Status.md`, so the privacy claims hold only for the MCP channel

The confinement profile denies only **writes** to protected paths (ADR-0013:77-79,
`COMPATIBILITY.md:52-58`). Nothing denies or discloses host-agent **reads** of the Vault or the
config/state files through Read, cat or apply_patch context.

Two claims are affected:

- Strict local-only mode "denies L0 and personal MCP results to a remote/unknown host"
  (`THREAT_MODEL.md:135-137`, plan 02 case B).
- "Full detail appears only on the user's own terminal and in the local Vault view `views/Status.md`"
  (ADR-0013:113-115).

Both are true only for the MCP/stdout channel. A confined agent can still read `Status.md` (which
holds paths and names) and every Vault record, and send them to the remote model. This is not an
overclaim in the literal wording, but users will read "strict local-only" as covering it.

**Action:** either

- add read-deny for the Vault and state paths to the profile where the host supports it (Claude Code
  sandbox read-deny plus Read deny rules; Codex per S04), with required-key rows and a marker-read
  S04 test, **or**
- state explicitly in `THREAT_MODEL.md` non-claims, the onboarding privacy preview and the
  strict-local wording that host file tools can read the Vault, and that strict local-only governs
  only core-mediated delivery.

Also move full status detail out of the Vault, or state that it is agent-readable.

### M5-1 — Medium: "session" is undefined, so "never cached across sessions" is not testable

ADR-0013:104-110 and plan 02:24 depend on detecting a new host session, but no document defines
session identity.

**Action:** bind status to a core-observable session key. For example, the MCP server process
lifetime, or the host `session_id` delivered to the SessionStart hook for Claude Code and its
equivalent for Codex. Resume, fork or compact is a new session. Test that a status from session N is
reported as `unverified` in session N+1 before probing.

### M5-2 — Medium: two plan texts still carry the old criterion

- **Plan 00 step 4 (plan 00:67-69).** It still reads "must be blocked (else `doctor` reports
  `not_in_effect`)". That is the pre-B4-1 either/or wording, with no false-positive direction, no
  reference to the ADR-0013 Verification list and no instruction to record keys in the
  `COMPATIBILITY.md` table.
  - **Action:** align it with SPIKES:75-81.
- **Slice 7 Done line (plan 01:140-141).** It does not mention the ADR-0013 Verification cases, which
  appear only in step 2.
  - **Action:** add "all ADR-0013 Verification cases pass" to Done.

### M5-3 — Medium: the status is a cooperative self-check, not an attestation, and the docs should say so

Within the accepted scope, an already-unconfined injected agent can forge the probe. For example, it
can wrap doctor in its own stricter `sandbox-exec` profile, fake the output, or write `Status.md`.

ADR-0013:110-111 lists only relaunch and the user's `!` shell as non-covered.

**Action:** add one non-claim: "status detects misconfiguration of a cooperating session; it cannot
attest confinement against an agent that is already unconfined". This is honesty wording only; the
scope is not reopened.

### Low

- **L5-1.** `COMPATIBILITY.md:7` names "Codex CLI 0.153.4" as the S04 planning snapshot. KI-015 and
  `COMPATIBILITY.md:56-58` say the Codex version is unrecorded. Reconcile them, and mark 0.153.4 as
  unverified if it came from documentation.
- **L5-2.** ADR-0013:137 says the doubles live "only under `tests/`", but `THREAT_MODEL.md:175` says
  "test-only package". Use one wording.
- **L5-3.** ADR-0013 Verification (175-176) lacks cases for:
  - a content edit to an already-exposed record being re-reviewed before remote egress (item 5);
  - migration and import never re-baselining the change log.
- **L5-4.** KI-011 (`KNOWN_ISSUES.md:14`) and the STATE/HANDOFF lines must be updated to cite this
  report once `STATUS.json` is registered.

## Implementability note (Claude Code 2.1.87, Codex, macOS 26.2)

| Element | Feasible? | Condition |
|---|---|---|
| Settings leg from merged files | Yes | Launch flags need a separate core-observable source (B5-1) |
| Shell-leg canary (core observes EPERM) | Yes | Robust; add socket and Apple Event canaries |
| Edit-leg canary | Yes, only with host-originated evidence | Hooks (Claude Code) or the Codex denial event; S04 must confirm per version |
| `--expect` binding | Yes | Shell-inert charset plus single quoting (B5-2); field coverage (H5-1) |
| Human prompt for approval | Codex: via escalation. Claude Code: needs the (a)/(b) decision | H5-2 |

## Gate checklist

- [x] The enforcement boundary is stated exactly, and the residual risk is accepted and recorded.
- [x] No broker, FIDO, authenticator, "MCP-injection guard", "verified user presence" or "exactly-once"
      text remains in normative docs.
- [x] H4-1 overclaims are removed (ADR-0005, ROADMAP).
- [x] The status derivation is defined, never cached, not raisable by labels, `unverified` by default,
      and unfilled key rows fail closed.
- [ ] The status derivation cannot yield a false `confined`: positive-evidence legs, launch-time
      configuration capped, escape classes probed (B5-1).
- [ ] The core-verified prompt text cannot execute source-derived shell code (B5-2).
- [ ] The summary covers type, scope, egress and irreversibility, and prefix resolution is unambiguous
      (H5-1).
- [ ] The Claude Code approval route is consistent with the required-key table, and the approver
      cannot be hijacked (H5-2).
- [x] Required-key table and escape-surface Verification cases exist (H4-3).
- [x] MCP cannot approve; sandboxed and SDK approval fail closed; a terminal fallback exists.
- [x] Out-of-band detection runs before every decision, with mixed and retag quarantine and no
      re-baseline.
- [x] Deferred effects recheck policy; expiry bounds effect start; `cancelled_policy` is terminal.
- [x] Test doubles are excluded from the wheel and the sdist (Slice 1 step and Done line).
- [ ] Privacy claims account for host file-tool reads (H5-3).

**Final judgment:** Remediation 12 closes most findings of report 12 cleanly and consistently. H4-1,
M4-1, M4-2, M4-6 and the Lows are closed, and H4-3 is closed at planning level with a fail-closed rule
for pending rows. Two defects remain that make stated security claims false within the chosen scope:

- **B5-1.** The probe scores "no observed success" as a pass, so a skipped edit leg or a launch-time
  escape setting yields a false `confined`.
- **B5-2.** The prescribed double-quoted `--expect` turns source-derived summary text into shell code
  that runs outside the sandbox.

Both need only a few sentences of normative text plus test cases, in ADR-0013 items 2 and 4, the
Verification list and SPIKES S04. H5-1 to H5-3 should land in the same pass.

**Verdict:** **BLOCK**

# Security and Privacy Sixth Re-review (focused)

- **Date:** 2026-09-18
- **Reviewer:** independent security/privacy reviewer (no prior context; repository is the only source)
- **Responds to:** `13-security-privacy-remediation.md` and the simplified
  `DECISIONS/ADR-0013-honest-host-trust-boundary.md`
- **Supersedes:** `13-security-privacy-fifth-rereview.md`

## Scope

This is a focused, planning-level re-review of the report-13 findings (B5-1, B5-2, H5-1 to H5-3,
M5-1 to M5-3, L5-1 to L5-4) and of the simplified contract that remediation 13 introduced:

- approval is terminal-only on every host;
- `--expect` is removed;
- core never claims confinement. Status is `profile` (`installed`/`missing`/`drifted`) plus
  `confinement` (`not_in_effect` on core-observed evidence, otherwise `unverified`).

The maintainer's honest-boundary scope is accepted and is not re-litigated. Unconfined same-user
hosts are inside the trust boundary. No hardware broker or positive attestation is requested.
Deferring empirical host facts to S04 is accepted where the rule for unknowns is fail-closed. Spikes
not having run is expected and is not a finding.

Files read:

- ADR-0013 (full).
- ADR-0005 §Decision and §Verification; ADR-0012 §Decision; ADR-0008:43.
- `THREAT_MODEL.md` (full); `COMPATIBILITY.md` (full); `KNOWN_ISSUES.md`.
- `SPIKES.md` S04; plans 00 (S04), 01 (Slices 1 and 7) and 02 (full).
- Remediation 13, report 13, `reviews/STATUS.json`, and the STATE/HANDOFF status lines.

## Commands run

```text
grep -rn -- "--expect\|partially_confined\|human prompt\|approval prompt\|ApprovalBroker\|FIDO\|WebAuthn" \
     docs AGENTS.md CLAUDE.md | grep -v docs/dev/reviews/
  → ADR-0013:8, 26, 156 (its own supersession/context/consequence text) and KNOWN_ISSUES:14 (KI-011
    history text quoting the report-13 finding). No normative leftover.
grep -rniE "host approval|host prompt|escalat|confined|verified confinement|in effect|unverified|not_in_effect" \
     docs AGENTS.md CLAUDE.md | grep -v docs/dev/reviews/
  → leftovers at THREAT_MODEL:58 and THREAT_MODEL:165-167 (M6-1, M6-2); COMPATIBILITY:59 (H6-1)
grep -rniE "hook|worker|daemon" docs/dev/DECISIONS docs/dev/plans docs/dev/THREAT_MODEL.md docs/dev/SPIKES.md
  → hooks (ADR-0008:43, ADR-0013:106/114, THREAT_MODEL:189) and journal workers are core code that
    runs outside the host sandbox; ADR-0013 does not bind them (H6-2)
grep -rn "own terminal" docs | grep -v reviews/
  → ADR-0013:63, 118; plan 02:21, 61 (M6-3)
python3.13 tools/check_relay.py   → "relay check passed" (before this report was added)
claude --version                  → 2.1.87 (Claude Code)
which codex                       → not found (KI-015 still open, as documented)
```

**Note for the caller.** After this report is added, `check_relay.py` will fail until
`reviews/STATUS.json` is updated:

- security `current` → `14-security-privacy-sixth-rereview.md`;
- add `13-security-privacy-fifth-rereview.md` to `supersedes`;
- set the verdict from the final line of this report.

KI-011, STATE and HANDOFF should then cite this report. The reviewer was not permitted to edit those
files.

## Disposition of report-13 findings

| ID | Sev. | Disposition | Evidence / residual |
|---|---|---|---|
| B5-1 | Blocking | **Closed** | The design no longer has a `confined` value (ADR-0013:97-101; COMPATIBILITY:50; ADR-0005:47-49). `not_in_effect` needs positive core-observed evidence, and skipped, misdirected or agent-reported legs, as well as unobservable launch flags, yield `unverified` (ADR-0013:103-110). Absence-based scoring can therefore no longer produce a protection claim. Binary tests: ADR-0013:179-185 and SPIKES:77-79. Evidence sources are deferred to S04 with a fail-closed rule (COMPATIBILITY:47-50). |
| B5-2 | Blocking | **Closed** | `--expect` is gone (the grep is clean). The command line carries only core-generated IDs in `[a-z0-9-]` (ADR-0013:69-70; THREAT_MODEL:71-72). Hostile-name test: ADR-0013:174-175 and SPIKES:77. |
| H5-1 | High | **Closed** | There is no summary on the command line. The terminal preview fields are at ADR-0013:64-67. The token binds the full digest, and ambiguous or unknown IDs are rejected (ADR-0013:71-72, test :176). Low note L6-3 applies. |
| H5-2 | High | **Closed for Claude Code; residual on Codex (H6-1)** | The route is terminal-only for all hosts (ADR-0013:75), and the key table forbids unsandboxed retry and excluded commands without conflict (COMPATIBILITY:54). The isolated `-I` entry point is at ADR-0013:73-74, with its test at :178. The Codex escalation path is still a de facto host-prompt route (H6-1). |
| H5-3 | High | **Closed** | Read-deny is added where supported (ADR-0013:81, 121-122; COMPATIBILITY:54-55, 59). The non-claim is at THREAT_MODEL:188-190, the onboarding disclosure at plan 02:22-23, and the test at ADR-0013:188-189. `views/Status.md` holds only an enum and reason codes (ADR-0013:117-118). CLI-output residual: M6-3. |
| M5-1 | Medium | **Closed at planning level** (L6-1) | The session key is at ADR-0013:113-115 and the test at :185. Because status is now negative-only, key ambiguity affects only freshness, not safety. |
| M5-2 | Medium | **Closed** | Plan 00:67-70 and plan 01:127-133 and 141-143 reference every ADR-0013 Verification case. |
| M5-3 | Medium | **Closed** | ADR-0013:119-120 and THREAT_MODEL:80-81. |
| L5-1 | Low | **Closed** | COMPATIBILITY:7-8 and KI-015. |
| L5-2 | Low | **Closed** | ADR-0013:144 and THREAT_MODEL:176 use the same wording. |
| L5-3 | Low | **Closed** | ADR-0013:131-133 and 193-194. |
| L5-4 | Low | **Closed for this round** | KI-011, STATE:22-25 and HANDOFF:25-28 are updated. They must be refreshed again for this report (see the note above). |

## Probe of the simplified contract

| Question | Answer |
|---|---|
| Can a confined agent get an approval committed through a core process running outside the sandbox? | **Not by design, but only partly bound.** The MCP server hosts the in-process SDK, including the approve service (ADR-0012:40). It runs outside the Bash sandbox. MCP is barred from approving (ADR-0013:62), and core exposes no approval IPC (ADR-0013:95-96). Hook handlers and journal workers also run unsandboxed on agent-influenced input, but they are not bound, and no structural test exists → **H6-2**. |
| Is "terminal-only" enforceable? | **Only via the sandbox's write denial, and only for the host's own shell.** In an unconfined session it is conventional; this is honestly stated (ADR-0013:75-77, 147-150). Codex escalation reopens a host-prompt route (**H6-1**). "The user's own terminal" is not something the CLI can distinguish (**M6-3**). |
| Does onboarding depend on a removed mechanism? | **No.** Plan 02:20-25 uses terminal confirmation of the SetupPlan digest. A minor disclosure gap about the current session is noted in L6-4. |
| Does `not_in_effect` / `unverified` wording anywhere imply protection? | **Two leftovers:** THREAT_MODEL:58 ("under host approval") and THREAT_MODEL:165-167 ("verified confinement profile … without it, doctor reports `not_in_effect`") → **M6-1** and **M6-2**. ADR-0013:160 and KI-014 also have a minor drift-wording mismatch (L6-2). |
| Are the session keys and evidence sources testable? | **Yes, with deferral.** Evidence sources are recorded per host in S04 under a fail-closed rule. The session key has an either/or choice (L6-1). |

## New findings

### H6-1 — High: Codex sandbox escalation is a host-prompt approval route that the plan says does not exist

- **Evidence.**
  - ADR-0013:75 says "No host-prompt routing exists", and ADR-0013:75-76 says a confined agent's
    approval "cannot commit".
  - COMPATIBILITY:59 sets the Codex required state to "escalation cannot reach Vault/state writes".
  - The approval-policy key family is listed at ADR-0013:89-90.
- **Why it matters.** Under an escalation-capable Codex approval policy (on-request, untrusted,
  on-failure or an equivalent), the agent can ask to run `review` / `purge confirm <id>` without the
  sandbox. The command text is composed by the agent and may be chained or env-prefixed. If the user
  approves the Codex prompt, the command runs unsandboxed and commits.
  - This is exactly the host-prompt route that remediation 13 removed. It returns through the host,
    not through core.
  - An escalated command runs with the user's full privileges. So "escalation cannot reach
    Vault/state writes" is probably not satisfiable per path. It is satisfiable only by making
    escalation unavailable.
  - The row is still pending, so nothing is claimed yet. But the plan gives S04 no satisfiable target,
    and it states the ADR-0013:75-76 claim for Codex without qualification.
- **Actions.**
  1. Set the Codex required state to "sandbox escalation unavailable". Use `approval_policy` `never`
     or an equivalent granular rejection of sandbox escalation, whichever S04 confirms.
  2. Make an escalation-capable policy that is visible in the effective config or argv a
     `not_in_effect` reason code.
  3. If the maintainer prefers to keep escalation for usability, state instead in ADR-0013 item 8 and
     in the THREAT_MODEL non-claims that approving any Codex escalation prompt runs that command
     unconfined. That includes a core approval. The "cannot commit" claim would then be limited to
     hosts or profiles without escalation.
  4. Add a Verification/S04 case with a binary result: "agent requests escalation of an approve
     command under the Codex profile → the request is not offered, or status is `not_in_effect`".

### H6-2 — High: unsandboxed core processes are not bound by the "confined approval fails closed" argument

- **Evidence.**
  - The fail-closed argument rests on the sandbox denying the Vault/nonce write (ADR-0013:57-58,
    75-76; THREAT_MODEL:72-73).
  - The MCP server hosts the in-process SDK and its approve service (ADR-0012:40, "CLI and MCP are
    thin adapters"). It runs outside the host's Bash sandbox.
  - Claude Code command hooks run core code outside the sandbox with host-supplied JSON. They are used
    for SessionStart, the session key and L0 (ADR-0008:43, ADR-0013:106, 114, THREAT_MODEL:189).
  - Journal workers are core processes that write state (ADR-0013:124, 136).
  - ADR-0013 binds only MCP ("never approve", :62) and IPC (:95-96).
- **Why it matters.** Any code path in these processes that reaches the approve or commit service on
  agent-influenced input commits with full write access. The sandbox never sees it, so the headline
  claim would be false. Where read-deny is unsupported, a confined agent can also read pending-action
  and nonce state. That makes any accidental "confirm by ID/nonce" parameter a usable bypass.
- **Actions.**
  1. Add to ADR-0013 item 1 or 2: the approve/commit service is reachable only from the CLI approve
     entry point. MCP handlers, hook handlers, journal workers and any other long-lived core process
     never call it. No non-CLI input schema carries an action-selection, token or nonce field.
     Workers execute only intents that were already committed.
  2. Add structural Verification cases:
     - an import/call-graph test proves that the MCP, hook and worker entry points cannot reach the
       approve service;
     - an enumeration of MCP tool and hook input schemas finds no token, nonce or approval field;
     - an S04 case: "a confined agent that has read the pending-action and nonce state cannot commit
       through any MCP tool, hook payload or worker trigger".

### M6-1 — Medium: `THREAT_MODEL.md:58` still prescribes "CLI confirmation under host approval"

The authorization table's destructive/permission row reads "core-rendered preview + ADR-0013 CLI
confirmation under host approval". That is the removed host-prompt route. It contradicts
ADR-0013:75 and THREAT_MODEL:70-72.

**Action:** replace it with "core-rendered preview + ADR-0013 terminal-only CLI confirmation".

### M6-2 — Medium: abuse case 2 implies verified confinement and a deterministic `not_in_effect`

THREAT_MODEL:165-167 reads: "Under a verified confinement profile, a host agent's write … is blocked
by the host; without it, `doctor` reports `not_in_effect`." That wording has two problems:

- it implies that a verified profile state exists, although ADR-0013:97-98 says core can never
  verify confinement;
- it promises `not_in_effect` whenever the profile is absent, although ADR-0013:103-110 says a
  missing profile is `profile: missing` and `unverified` unless there is positive evidence.

A test written from this abuse case would contradict ADR-0013 Verification.

**Action:** reword it along these lines. "With the adapter profile applied (S04 fixture), a host
agent's write … is denied by the host. `doctor` never reports confinement as in effect. It reports
`not_in_effect` only on core-observed evidence and `unverified` otherwise."

### M6-3 — Medium: "the user's own terminal" is not a distinction the CLI can make

The following texts treat the user's terminal as a distinct channel:

- ADR-0013:63 ("in their own terminal");
- ADR-0013:118 ("Full detail appears only on the user's own terminal");
- THREAT_MODEL:70-71 and 189 (strict local-only governs "CLI output");
- plan 02:21 and 61.

The CLI cannot tell the user's terminal from a host-agent shell. The only enforcement is the host
sandbox:

- write-deny for commits;
- read-deny for the state that the CLI would print.

On hosts without read-deny (Codex, per COMPATIBILITY:59), a confined agent can run
`doctor`/`review` in its shell and get full status detail and preview content. Strict local-only
cannot govern that CLI output.

**Actions:**

- Define "terminal-only" normatively as "the CLI subcommand, in a process not denied by host
  confinement; core does not and cannot identify the terminal".
- Move "CLI output invoked from a host shell" into the THREAT_MODEL:188-190 non-claim next to host
  file tools.
- Make the plan 02 per-host preview say so.

### M6-4 — Medium: project-scope host configuration inside writable roots is not explicitly protected

- **Evidence.** ADR-0013:83 protects "host hook/MCP/plugin/adapter files", and COMPATIBILITY:57
  requires them to be "outside every writable root or write-protected". But the plan does not list the
  project-scope files that live *inside* the workspace writable root and can add unsandboxed
  execution at the next launch:
  - Claude Code: `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json` and project hook
    scripts;
  - Codex: project-level config, if S04 finds that it is honored.

  The ADR-0013:86-88 key list also does not treat a non-bundled hook or MCP-server entry in merged
  settings as observable escape evidence.
- **Why it matters.** A confined agent can plant a hook or MCP server there. It then runs unsandboxed
  in the next session, and that session's status would not show it as an escape.
- **Actions.**
  - Enumerate the project-scope config files per host in the COMPATIBILITY rows, and require
    write-deny for every writable root. S04 confirms whether the host already denies these writes.
  - Make any hook or MCP-server entry not in the bundled profile a `not_in_effect` reason code.
  - Add an S04 case: "agent writes a hook to project settings → the write is denied, or the next
    session reports `not_in_effect`".

### Low

- **L6-1.** The session key is "the MCP server process lifetime, **or** the host session ID"
  (ADR-0013:113-114). The MCP process lifetime cannot observe a compact or a resume. Record in
  `COMPATIBILITY.md` which key each host version uses. Status is now negative-only, so this affects
  freshness, not safety.
- **L6-2.** ADR-0013:160 and KI-014 say that drift "degrades the status to `not_in_effect`". Under
  item 4, drift that core can observe yields `profile: drifted`, and it yields `not_in_effect` only
  when positive evidence exists. An unrecognized host version yields `unverified`. Align the wording.
- **L6-3.** State that action IDs resolve by exact match only, with no prefix or fuzzy resolution.
  The "ambiguous ID" rejection at ADR-0013:72 then covers a defined case.
- **L6-4.** A profile installed by setup takes effect only in newly launched host sessions. Plan
  02:24-26 and 59-62 should tell the user that the current session is not covered and must be
  relaunched.

## Gate checklist

- [x] Enforcement boundary stated exactly; residual risk accepted and recorded (ADR-0013 item 8,
      THREAT_MODEL:191-192).
- [x] No `--expect`, `partially_confined`, host approval prompt, broker, FIDO or WebAuthn text in
      normative docs (grep clean apart from history and supersession text). Note the two wording
      leftovers M6-1 and M6-2.
- [x] Status can never report `confined`. `not_in_effect` needs positive core-observed evidence, and
      everything else is `unverified`, with binary tests (B5-1).
- [x] No source-derived text reaches a command line, with a test (B5-2).
- [x] The terminal preview covers type, scope, egress and irreversibility; the full digest is bound;
      ambiguous or unknown IDs are rejected (H5-1).
- [x] Claude Code approval route consistent with the required-key table; approver isolated with `-I`
      (H5-2).
- [ ] The Codex escalation route is closed or honestly scoped (H6-1).
- [ ] Unsandboxed core processes (MCP, hooks, workers) cannot reach the approve service, with a
      structural test (H6-2).
- [x] Host file-tool reads disclosed; read-deny where supported; `Status.md` enum only (H5-3).
- [x] Session binding and evidence sources defined or deferred with fail-closed rules (M5-1).
- [x] Plans 00 and 01 reference every ADR-0013 Verification case (M5-2).
- [x] Cooperative self-check non-claim present (M5-3).
- [x] Test doubles excluded from the wheel and the sdist; out-of-band detection and deferred-effect
      cases present.

**Final judgment:** Remediation 13 closes every report-13 finding. Simplifying ADR-0013 to
terminal-only approval and a negative-only status removes both blocking defects rather than patching
them. No remaining defect makes a security claim false within the chosen scope as written, because
every host row is still pending and the ADR-level claims are conditional on the profile.

Two High gaps should land before S04 runs, because S04 cannot pass them honestly without them:

- **H6-1.** The Codex escalation needs a satisfiable required state.
- **H6-2.** The unsandboxed MCP, hook and worker processes need an explicit "cannot reach approve"
  rule and a structural test.

The Medium findings are wording and coverage fixes.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

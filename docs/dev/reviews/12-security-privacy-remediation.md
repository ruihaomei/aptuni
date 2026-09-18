# Fifth Security and Privacy Remediation

- **Responds to:** `12-security-privacy-fourth-rereview.md`
- **Date:** 2026-09-18
- **Status:** ADR-0013 amended; focused re-review pending

| Finding | Remediation |
|---|---|
| B4-1 status can overstate | ADR-0013 item 4: status = min(effective merged-settings check over the required keys, live in-session canary probe through the host shell tool **and** file-edit tool); any successful canary → `not_in_effect`; new `unverified` status for no-probe sessions; never cached across sessions; worded per session/time/host version; labels/env/config cannot raise it; Claude Code `confined` always carries `edit_tool_rule_based`. Negative tests for every bypass flag, escape setting, writable-root Vault/install, hook/MCP/plugin write, indirection, socket, and forged label/env in ADR-0013 Verification and S04 acceptance. |
| H4-1 leftover overclaims | ADR-0005 Verification and ROADMAP M2 rewritten per the reviewer's wording; PRD §16 override stated explicitly in ROADMAP. |
| H4-2 host prompt shows agent text | Option (a): `--expect "<summary>"` must byte-equal the core's canonical ≤160-char NFC summary with control/bidi/zero-width stripped; mismatch/truncation/homoglyph tests. THREAT_MODEL now says "MCP-cannot-self-approve" instead of "MCP-injection guard"; a deceived user approving a truthful summary is accepted residual risk. |
| H4-3 required keys / escape surfaces | ADR-0013 item 3 lists required key families per host; `COMPATIBILITY.md` gains a normative required-key table (pending S04; unfilled rows cap status at `unverified`); install path must be outside writable roots; real-path/inode comparison for symlink/hardlink/rename/clone; no approval-capable IPC. |
| M4-1 `partially_confined` | Defined as accidental-action friction only, no protection against an injected agent; CLI is the only *supported* approval surface; SDK approve from a sandbox fails closed (tested). |
| M4-2 no host prompt | Canonical fallback: user runs the subcommand in their own terminal; sandboxed invocation fails closed with a content-free reason code (ADR-0013 item 2, plan 02). |
| M4-3 detection gaps | Detection before every policy decision and in worker rechecks; mixed and module-retag edits quarantine as a whole; content edits to exposed records re-reviewed before next remote egress; restore/migration/import never re-baseline (ADR-0013 item 5, plan 01 Slice 7). |
| M4-4 missing binary tests | S04 acceptance now references every ADR-0013 Verification case; enumeration test for flags/env/config; wheel/sdist assertion added to Slice 1 steps and Done. |
| M4-5 status leakage | Host-bound status is enum + reason codes only; full detail only on the user's terminal and `views/Status.md`; diagnostic redaction extended to host-bound output; marker-path test. |
| M4-6 onboarding order | Core CLI writes the profile from bundled content; preview lists modified host settings files; status stays `unverified` until a new session passes the probe (plan 02). |
| L4-1 | Test doubles excluded from sdist explicitly and absent from wheel/import path. |
| L4-2 | Drift = per-session adapter/runtime hash recheck before any L0/personal release (THREAT_MODEL). |
| L4-3 | Approval expiry bounds effect start; unrelated epoch bump re-evaluates (ADR-0013 item 6). |
| L4-4 | KI-014/KI-015 remain S04 blockers; Codex prompt-rule availability recorded in the required-key table. |
| L4-5 | Human-visible surfaces are the user's terminal and `views/Status.md`; agent-relayed notices are best-effort. |

# Sixth Security and Privacy Remediation

- **Responds to:** `13-security-privacy-fifth-rereview.md`
- **Date:** 2026-09-18
- **Status:** ADR-0013 simplified within the maintainer-chosen scope; focused re-review pending

Design change: instead of patching the host-prompt route and the positive confinement claim again,
remediation 13 removes both (the reviewer's H5-2 option (a), applied to every host). Approval is
terminal-only; core never claims confinement is in effect.

| Finding | Remediation |
|---|---|
| B5-1 absence-based `confined` | Core never reports `confined`. Status = `profile` (`installed`/`missing`/`drifted`) + `confinement` (`not_in_effect` on positive core-observed evidence: successful nonce canary write/socket/Apple Event, observable escape key or launch flag, writable-root Vault/install path; otherwise `unverified`). Skipped/misdirected legs and unobservable launch flags yield `unverified`. Verification and S04 cases added (ADR-0013 item 4). |
| B5-2 shell injection via `--expect` | `--expect` removed. Approval runs in the user's terminal with the full preview; the command line carries only core-generated IDs in `[a-z0-9-]`. Test: `$(…)`, backtick, quote, backslash, `;`, newline in names never reach a command line. |
| H5-1 summary coverage / prefix | No summary-on-command-line; the terminal preview shows action type, scope identity/count, egress provider/destination/data class, irreversibility, delimited untrusted names with confusables flagged; token binds the **full** digest; ambiguous/unknown IDs rejected. |
| H5-2 Claude Code routing / approver hijack | No host-prompt routing exists (terminal-only for all hosts), so the required-key table forbids unsandboxed retry/excluded commands without conflict. The entry point runs `-I` from the install path; env/shadow-module tests added. |
| H5-3 host reads | Profile adds read-deny where supported (required-key rows); THREAT_MODEL non-claim and onboarding preview state that host file tools may read the Vault and that strict local-only governs core-mediated delivery only; `views/Status.md` holds only enum/reason codes. |
| M5-1 session undefined | Evidence is bound to the MCP server process lifetime or the host session ID from the SessionStart hook; resume/fork/compact is a new session; test that session N evidence is absent in N+1. |
| M5-2 stale plan text | Plan 00 step 4 and plan 01 Slice 7 (step and Done) now reference every ADR-0013 Verification case. |
| M5-3 cooperative self-check | Non-claim added to ADR-0013 item 4 and THREAT_MODEL. |
| L5-1 Codex version | `COMPATIBILITY.md` states 0.153.4 came from the ChatGPT desktop bundle (research 06) and is not on PATH; KI-015 reconciled. |
| L5-2 double placement | "under `tests/` only (never a separate package)" in both ADR-0013 and THREAT_MODEL. |
| L5-3 missing cases | Content-edit re-review before remote egress and migration/import non-re-baseline added to ADR-0013 Verification. |
| L5-4 state lines | KI-011, STATE, HANDOFF and STATUS.json updated. |

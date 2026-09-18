# Known Issues and Open Risks

| ID | Severity | Issue | Disposition |
|---|---|---|---|
| KI-002 | Release blocker | Public license is not confirmed. | Maintainer decides ADR-0009 before release/contributions. |
| KI-003 | Blocking | Bilingual FTS design is evidence-informed but unmeasured on project corpus. | Run S03. |
| KI-004 | Blocking per source | MarginNote export identity is not publicly guaranteed stable. | Run Gate 0 S05A then MarginNote S05B on real sanitized exports. |
| KI-005 | Blocking | Proposed MCP API has not been exercised across required hosts. | Run S04; Claude/Codex required. |
| KI-007 | High | Plugin discovery/failure isolation and locked-closure approval are not proven in an installed fixture. | Run S02; no malicious-code sandbox claim. |
| KI-008 | Deferred | Mem0 local privacy/retention/export behavior needs isolation testing. | S10 before Milestone 2 adapter. |
| KI-009 | Deferred | Graphiti projection loses canonical semantics and needs a ledger. | S11 before Milestone 3 adapter. |
| KI-010 | Process | Project Research Memory has not been initialized. | Await maintainer answer; not an implementation blocker. |
| KI-014 | High | Host confinement setting keys (Claude Code sandbox/permissions, Codex sandbox/writable roots) are unverified for the pinned host versions. | S04 verifies and records them plus the session key per host; observable drift yields `profile: drifted`, unknown versions `unverified`. |
| KI-016 | High | S01 findings F1–F3: whole-Vault revalidation per commit, integrity mismatch blocks all reads, purge needs startup `recover()`. | Mandatory M1.1 Slice 3 requirements (incremental validation + compaction; out-of-band edits → quarantine; recover before serving); fold into ADR-0001/0010 on acceptance. |
| KI-015 | Low | Codex 0.153.4 was observed only in the ChatGPT desktop bundle (not on PATH); its preceding version is unrecorded. | Record exact and preceding versions during S04 before any host journey. |

Resolved issues move to an appended history section; do not silently delete them.

## Resolved history

- **KI-001 (2026-09-18):** S00 selected temporary development distribution
  `personal-context-core` / import `personal_context_core`; public naming remains a release workstream.
- **KI-012 (2026-09-18):** Execution review stream reached APPROVE WITH NON-BLOCKING NOTES (report 10);
  its notes NF1–NF8 are addressed in remediation 10.
- **KI-013 (2026-09-18):** Cold Claude Code relay drill passed (report 11); defects fixed in
  remediation 11.
- **KI-011 (2026-09-18):** Security stream reached APPROVE WITH NON-BLOCKING NOTES (report 14) after the
  maintainer chose the honest host trust boundary (ADR-0013); notes addressed in remediation 14.
- **KI-006 (2026-09-18):** S01 proved the Vault write protocol on the Gate 0 baseline (46 tests; crash at
  four boundaries, 8-process concurrency, lock-holder SIGKILL, purge/restore). Power-loss durability
  remains an assumption (`spikes/S01-vault.md` F4).

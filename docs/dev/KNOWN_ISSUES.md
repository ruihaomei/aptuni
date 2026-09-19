# Known Issues and Open Risks

| ID | Severity | Issue | Disposition |
|---|---|---|---|
| KI-002 | Release blocker | Public license is not confirmed. | Maintainer decides ADR-0009 before release/contributions. |
| KI-004 | Blocking per source | MarginNote export identity is not publicly guaranteed stable. | Run Gate 0 S05A then MarginNote S05B on real sanitized exports. |
| KI-005 | Blocking | S04 local protocol/policy layer and Codex 0.155.0/0.154.0 read/protected-write paths pass. Claude authentication is restored, but 2.1.267/2.1.266 both stop before inference/MCP with HTTP 429 because the account usage/session limit is exhausted. | Rerun both Claude journeys after the limit resets or is raised, then finish ADR-0013 host probes. |
| KI-008 | Deferred | Mem0 local privacy/retention/export behavior needs isolation testing. | S10 before Milestone 2 adapter. |
| KI-009 | Deferred | Graphiti projection loses canonical semantics and needs a ledger. | S11 before Milestone 3 adapter. |
| KI-010 | Process | Project Research Memory has not been initialized. | Await maintainer answer; not an implementation blocker. |
| KI-014 | High | Host confinement setting keys (Claude Code sandbox/permissions, Codex sandbox/writable roots) are unverified for the pinned host versions. | S04 verifies and records them plus the session key per host; observable drift yields `profile: drifted`, unknown versions `unverified`. |
| KI-016 | High | S01 findings F1–F3: whole-Vault revalidation per commit, integrity mismatch blocks all reads, purge needs startup `recover()`. | Mandatory M1.1 Slice 3 requirements (incremental validation + compaction; out-of-band edits → quarantine; recover before serving); fold into ADR-0001/0010 on acceptance. |
| KI-017 | High | S02 F1: pip RECORD does not hash `.pyc`; a forged bytecode file passes closure verification and executes. | M1.1 sets `sys.pycache_prefix` to a core-owned directory before importing plugins (proven in S02) and adds F2/F3 (manifest placement; lockfile artifact hashes). |
| KI-018 | High | S03 used a templated synthetic corpus; broad two-character queries admitted top-5 distractors even though aggregate gates passed. | M1 adds dogfood judgments and per-result context-noise tests; retain size telemetry and score/reranking seam before user-facing quality claims. |
| KI-019 | High | Portable `realpath`/`stat` cannot identify APFS clone ancestry. S04 found a promising Foundation content identifier, while independent review identified native full-clone mapping attributes but warned that arbitrary historical, partial or diverged ancestry remains unprovable. | ADR-0013 was narrowed. Add a pinned native full-clone bridge plus adversarial false-positive/false-negative and incomplete-scan tests; portable or failed native probes remain `unverified`, and absence never proves confinement. |

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
- **KI-007 (2026-09-18):** S02 proved entry-point discovery without execution, isolation of duplicate,
  broken and incompatible plugins, approval bound to the installed closure, and drift denial
  (12 tests). Undeclared-network checks are detection only.
- **KI-003 (2026-09-19):** S03 measured all three extension-free FTS5 strategies on frozen bilingual
  evidence. Deterministic 2–4-character CJK lexemes passed development, 25k-scale, and untouched
  holdout gates (23 tests); generalization and broad-query noise continue as KI-018.
- **KI-015 (2026-09-19):** S04 ran the required Codex current/preceding stable pair (0.155.0 and
  0.154.0); both returned `HOST_OK 61` on the bounded annotated read path. Installed 0.153.4 remains
  an additional observation, not the release target.

# Cold Claude Code Relay Drill

- **Date:** 2026-09-18
- **Method:** cold reconstruction from repository files only; no prior conversation context. Entry
  followed the Claude Code path: auto-loaded `CLAUDE.md` → `@AGENTS.md` → `STATE.md` →
  `HANDOFF.md` → `reviews/STATUS.json` and current review reports → ADR index/ADR-0008 →
  `ROADMAP.md`, `SPIKES.md`, `KNOWN_ISSUES.md`, `COMPATIBILITY.md` → `git status` → baseline checks.
- **Host:** Claude Code 2.1.87 on macOS 26.2 (25C56); `python3` on the Claude shell PATH is
  Anaconda CPython 3.12.4; `python3.13` is Homebrew CPython 3.13.3.
- **Scope:** relay readiness and planning state only; no production code; no file edited except this
  report. Concurrently written reports 09/10 were out of scope and not treated as defects.
- **Cold-relay verdict:** **PASS** for safe continuation of Gate 0 planning, review, and spike work;
  production implementation remains **BLOCK**.

## 1. Current gate and production-code state

The project is in **Gate 0 — planning and proof** (`STATE.md:4`). Production code has not started and
may not start: `AGENTS.md:30` blocks it until Gate 0 in `ROADMAP.md` passes, and `STATE.md:5`,
`HANDOFF.md:20-21`, and `ROADMAP.md:11-15` agree. Two of four review streams are `BLOCK`
(`reviews/STATUS.json`), no S01–S05A results exist (`docs/dev/spikes/` holds only S00), and all
twelve ADRs are `Proposed`. The repository has no commits; every file is untracked.

## 2. Completed work

- PRD v2.1 and depersonalized rationale; eight research notes; research synthesis; twelve proposed
  ADRs; MVP dependency graph; threat model; roadmap; spike catalog; evaluation and compatibility
  plans; three execution plans.
- S00 temporary namespace `personal-context-core` / `personal_context_core` (KI-001 resolved).
- Review lineage: architecture `APPROVE_WITH_NON_BLOCKING_NOTES` (07); security `BLOCK` (06 second
  re-review) with third remediation `06-security-privacy-remediation.md` written; execution `BLOCK`
  (08 re-review) with second remediation `08-execution-test-remediation.md` written; relay `PASS`
  (05, Codex only).
- Relay tooling: `tools/check_relay.py` with `STATUS.json` lineage parsing and untracked-aware
  whitespace scanning; five unit tests pass in this session under both 3.12.4 and 3.13.3.
- Gate 0 S01 baseline fixed to macOS 26.2/APFS/CPython 3.13.3 (`COMPATIBILITY.md:5-8`); this host
  matches it.

Remediations 06 and 08 are author claims, not closure; each states its focused re-review is pending.

## 3. Real blocking items

1. **Security stream `BLOCK`.** B2-R2 (TTY/PTY is not human presence), H1 (external-effect
   atomicity), M3 (proven-local admission authority) are remediated on paper via the OS/FIDO2
   ApprovalBroker; a third focused security re-review has not been run (KI-011).
2. **Execution stream `BLOCK`.** N1 (review-lineage checker) and N2 (S01 matrix loop) are remediated
   on paper; N3/N4 High and N5 Medium also claimed; a second focused execution re-review has not
   been run (KI-012). Several N1 requirements appear unmet (see defect D4).
3. **Decision-changing spikes absent.** S01, S02, S03, S04, S05A have no result files (KI-003..007).
4. **ADRs not accepted.** All twelve remain `Proposed`; ADR-0008 acceptance additionally needs this
   Claude drill registered (KI-013).
5. **Maintainer decisions pending (not Gate 0 blockers):** Research Memory initialization (KI-010),
   public brand/package migration, and Apache-2.0 confirmation (KI-002) remain release gates.

## 4. Next highest-priority action

Register this drill (see D1), then commission the two independent focused re-reviews: security
against `06-security-privacy-remediation.md` and execution against
`08-execution-test-remediation.md`. The execution re-reviewer should verify N1 against the full
required-test list, not just the one added test. Only after both clear: run S01–S04 and S05A on the
fixed baseline, record results, and accept or revise ADRs. No production scaffold before then.

## 5. Harness defects and contradictions found

| ID | Severity | Location | Finding |
|---|---|---|---|
| D1 | Medium | `tools/check_relay.py:138-140`; `reviews/STATUS.json:18-22` | Writing any non-remediation review report (including this one) makes `check_relay.py` fail until `STATUS.json` and the STATE summary line are updated together. A drill restricted to writing its report cannot leave the checker green, and parallel reviewers (09/10) collide on the same two files. The `relay` stream also models one drill, so `relay=PASS` (`STATE.md:7`) reads as complete while only Codex has run. Needs separate `relay-codex`/`relay-claude` streams or a required-drill list. |
| D2 | Low | `STATE.md:40` vs `HANDOFF.md:34`, `08-execution-test-remediation.md:12` | STATE records "3 passed"; there are five tests and HANDOFF says five. |
| D3 | Medium | `STATE.md:41-43`; `HANDOFF.md:33-34` | `git diff --check: passed` is still recorded without the no-commit/untracked caveat that 08 N3 required. The link count "50 files" is stale (52 under `docs/`, 56 repo-wide). HANDOFF says to rerun "after the pending review agents write their reports", which is time-relative and unresolvable without chat history. |
| D4 | Medium | `tests/dev/test_check_relay.py:54-83`; `tools/check_relay.py:134-149` | 08 N1 required tests for latest BLOCK, missing/multiple verdicts, verdict words in unrelated prose, and missing Codex/Claude drill evidence; only historical-BLOCK→APPROVE is tested. Verdict parity is still a substring search of the whole report, and the BLOCK acknowledgement is still a `"BLOCK"`/`"re-review"` substring test over STATE+HANDOFF. |
| D5 | Low | `08-execution-test-remediation.md:9-14` vs `08-execution-test-rereview.md:137-205` | Remediation cites B1/H5, B2, H7, H8, H9, M6; the re-review raised N1–N5. Traceability requires the reader to map IDs by hand. |
| D6 | Low | `HANDOFF.md:10-13`; `AGENTS.md:8` | Neither read-order lists `reviews/STATUS.json` or `KNOWN_ISSUES.md`, though they hold the authoritative verdicts and blocker list. STATE's one-line summary partly compensates. |
| D7 | Low (Claude-specific) | `AGENTS.md:37-38`; `COMPATIBILITY.md:6` | Commands say `python3`; in this Claude shell that is Anaconda 3.12.4, not the declared 3.13.3 baseline. Harmless for relay checks, material for S01/S03 evidence. Pin the interpreter (e.g. `python3.13`) for spike commands. |
| D8 | Low (Claude-specific) | `.gitignore` | `.claude/` is not ignored; a Claude runtime file `.claude/scheduled_tasks.lock` now exists and would be swept into the first commit by `git add .`. |
| D9 | Low (Claude-specific) | `CLAUDE.md:1-11` | `@AGENTS.md` import is correct and both files are concise (456 B / 1957 B). However, this user's global Claude config loads rules that default to Research Memory/Obsidian bootstrap, `/plan` directories, and proactive agent spawning. CLAUDE.md does not say that the repository contract overrides user-level defaults; a cold Claude session must infer that from `AGENTS.md:9-10` and KI-010. One line in CLAUDE.md would remove the ambiguity. Its L0-hook bullets are product guidance, not dev-harness behavior, and could be moved to an ADR reference. |

No fact needed for safe continuation was resolvable only through chat history. No `.claude/skills`,
hooks, or settings exist, which matches `CLAUDE.md:5-6` and ADR-0008; compared with the Codex drill
there is no Claude-only skill or hook gap at Gate 0.

Items the Codex drill flagged that are now fixed: STATE no longer says "finish the three remediation
passes"; historical BLOCK handling uses `STATUS.json`; untracked whitespace is scanned.

## 6. Safe continuation judgment

**PASS**, with the same scope boundary as the Codex drill. A fresh Claude Code session recovered the
gate, invariants, lineage, open blockers, and next action from repository files alone, and would not
be misled into starting production code, accepting ADRs, or initializing Research Memory. The
defects above are accuracy and ergonomics issues; none would cause unsafe continuation. Production
implementation remains blocked by security/execution `BLOCK` verdicts and missing S01–S05A evidence.

## Commands run

Before creating this report:

```text
git status
On branch main; No commits yet; untracked: .gitignore AGENTS.md CLAUDE.md docs/ tests/ tools/

python3 -m unittest tests/dev/test_check_relay.py        (CPython 3.12.4)
Ran 5 tests — OK

python3 tools/check_relay.py
relay check passed

python3.13 -B -m unittest tests/dev/test_check_relay.py  (CPython 3.13.3)
Ran 5 tests — OK

python3.13 -B tools/check_relay.py
relay check passed

git diff --check
exit 0; no output (no commits: covers no untracked content)

sw_vers; claude --version
macOS 26.2 (25C56); Claude Code 2.1.87
```

`PROJECT_KNOWLEDGE.md` is absent, so no Research Memory status command was run. After creating this
report, `python3 tools/check_relay.py` is expected to fail with "review report is absent from lineage
manifest: 11-cold-claude-relay-drill.md" until the maintainer or next agent registers it (D1).

**Verdict:** **PASS**

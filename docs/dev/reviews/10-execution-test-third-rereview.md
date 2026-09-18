# Third Focused Execution and Test Re-review

- **Date:** 2026-09-18
- **Re-reviews:** `08-execution-test-rereview.md` (N1–N5)
- **Remediation under review:** `08-execution-test-remediation.md` and the artifacts it cites
  (`reviews/STATUS.json`, `tools/check_relay.py`, `tests/dev/test_check_relay.py`,
  `COMPATIBILITY.md`, `SPIKES.md`, `plans/00-phase-0-spikes.md`, `EVALUATION_PLAN.md`, `STATE.md`,
  `HANDOFF.md`, `ROADMAP.md`)
- **Evidence rule:** a revised plan can close a planning defect; it is not execution proof. S01–S05A
  and the cold Claude Code relay have not run, which is expected at this point and is not by itself a
  reason to block the plan.

## Commands run and results

```text
python3 -m unittest tests/dev/test_check_relay.py -v     (python3 = 3.12.4, /opt/anaconda3)
Ran 5 tests — OK

python3 tools/check_relay.py
relay check passed (exit 0; run before this report was written)

git diff --check
exit 0 — but `git ls-files` = 0: no file is tracked, so this checks nothing

sw_vers                        macOS 26.2, build 25C56          (matches COMPATIBILITY.md:5)
mount                          /System/Volumes/Data: apfs, local, journaled, "root data"
/opt/homebrew/bin/python3.13   CPython 3.13.3, sqlite3 3.53.2    (matches COMPATIBILITY.md:6)
claude --version               2.1.87                           (matches COMPATIBILITY.md:6)
codex --version                not on PATH here; 0.153.4 could not be checked in this session
```

The relay checker was probed with nine throwaway copies of the repository under
`/private/tmp/relay-probe-10` (deleted after the run). None of the probes touched the repository:

| Probe | Mutation | Checker result |
|---|---|---|
| E0 | Adds a file named `10-execution-test-third-rereview.md` | **FAIL** (the file is not in the manifest). This is correct and expected. |
| E1 | `execution.verdict = PASS` while current report 08 ends in `**BLOCK**` | **pass** — `PASS` appears in the prose of 08 |
| E2 | `architecture.verdict = BLOCK` while report 07 approves | **pass** — the word `NON-BLOCKING` contains `BLOCK` |
| E3 | `architecture.verdict = APPROVE` for report 07 (APPROVE WITH NON-BLOCKING NOTES) | **pass** — substring match |
| E4 | New APPROVE report 10 listed only under `supersedes`; `current` stays 08 | **pass** — the checker never checks which report is newest |
| E5 | New `10-execution-remediation-review.md` with a BLOCK verdict | **pass** — any file whose name contains `remediation` is skipped |
| E6 | Every stream made non-blocking; HANDOFF still says "Execution remains `BLOCK`" | **pass** — the stale HANDOFF is not detected |
| E7 | Codex drill report and `relay` stream deleted | **pass** — nothing requires drill evidence |
| E8 | Report with no verdict line, only the prose "might BLOCK or APPROVE" | **pass** |
| E9 | A second, contradictory `Review status manifest:` line appended to STATE | **pass** |

## Disposition of 08 findings

| ID | 08 severity | Disposition | Basis |
|---|---|---|---|
| N1 relay verdict resolution | Blocking | **PARTIALLY CLOSED → residual High (NF1, NF2, NF3)** | The central fault is fixed. `STATUS.json` now carries current/verdict/supersedes for each lineage, so a historical BLOCK no longer blocks for ever (`check_relay.py:106-137`, test `test_check_relay.py:54-83`). PASS/FAIL are accepted as values. Every non-remediation report must belong to a lineage (`:138-140`), and the STATE summary must match exactly (`:141-144`). Four parts of the required fix are still missing: (a) parsing exactly one final verdict per report, (b) checking that `current` is the newest report, (c) checking HANDOFF freshness, and (d) checking drill evidence. The four tests 08 asked for were not added (latest BLOCK, missing/multiple verdicts, unrelated prose, missing drill). Probes E1–E9 show the gaps. Humans can still decide the gate from the explicit `**Verdict:**` lines, so this no longer blocks the plan. |
| N2 S01 matrix circularity | Blocking | **CLOSED at planning level; residual Medium (NF5)** | One exact Gate 0 baseline is predeclared: macOS 26.2 (25C56), local APFS, CPython 3.13.3, SQLite 3.53.2 (`COMPATIBILITY.md:5-8,15`). `SPIKES.md:27-31` and `plans/00-phase-0-spikes.md:30-33` use the same baseline. Unknown, network and synced filesystems fail closed, and Linux/ext4 is deferred to a later admission. The plan no longer depends on CI that is built after Gate 0. I checked the baseline facts on this host. |
| N3 `git diff --check` coverage | High | **PARTIALLY CLOSED → residual Medium (NF4)** | `check_workspace_text` (`check_relay.py:162-185`) scans all text files whether or not Git tracks them, and it has a test (`test_check_relay.py:85-93`). However, `STATE.md:40-43` still records "3 passed" and "`git diff --check`: passed" with no caveat, plus a stale count of 50 Markdown files (56 exist). `HANDOFF.md:34` says five tests. `check_state` requires the literal text `git diff --check` in STATE (`check_relay.py:31,80-84`), so the checker enforces the misleading line. |
| N4 evaluation loopholes | High | **PARTIALLY CLOSED → residual High (NF6)** | Setup success and safe refusal are now separate, both at 100%, and a refusal never counts as success (`EVALUATION_PLAN.md:23`). This closes the all-refusal loophole. Context noise now uses ADR-0005 byte-based units (`EVALUATION_PLAN.md:20`, `ADR-0005:80-82`). Still undefined: how a response is split into judged segments, what happens with empty output (0/0), how judge ties are broken, the fixed overhead constant, and a versioned annotation example. The rows of `plans/02-onboarding-advisor.md:31-38` are not labelled as success or refusal cases. |
| N5 prior host minor | Medium | **PARTIALLY CLOSED → residual Low (NF7)** | `COMPATIBILITY.md:17` removes the silent skip: the current and preceding versions must pass, or the gap must be recorded. It still does not predeclare the preceding version for each host. It also offers "release-blocking/documented unsupported" as an either/or with no owner or waiver artifact. |

## New and residual findings

### NF1 — High: the manifest-to-report verdict check is a substring test and does not tie verdict type to stream

**Evidence:** `tools/check_relay.py:129-135` accepts a report when the display verdict appears anywhere
in its text. `REVIEW_VERDICTS` (`:33`) is shared by all streams, so a review stream can be marked
`PASS` and a drill can be marked `APPROVE`. Probes E1, E2, E3 and E8 all pass even though the manifest
contradicts the report's final verdict. E1 is the dangerous case: `execution=PASS` passes against the
current BLOCK report 08. The only lineage test (`tests/dev/test_check_relay.py:54-83`) covers only
the case where the answer is already correct.

**Action:**

1. Parse exactly one anchored final verdict per report, for example
   `^(\- )?\*\*(Verdict|Cold-relay verdict):\*\* \*\*(…)\*\*$`. Reports with zero or several matches
   fail.
2. Require the manifest verdict to equal the parsed verdict.
3. Restrict review streams to APPROVE, APPROVE_WITH_NON_BLOCKING_NOTES and BLOCK, and drill streams
   to PASS and FAIL.
4. Add tests for latest BLOCK, manifest/report mismatch, missing verdict, multiple verdicts, prose
   that contains verdict words, and `NON-BLOCKING` versus `BLOCK`.

Fix this before the checker is cited as Gate 0 relay evidence (`ROADMAP.md:15`).

### NF2 — High: cold-drill evidence is not modelled, so the missing Claude Code drill cannot be detected

**Evidence:** `STATUS.json` has a single `relay` stream whose current report is the Codex drill
report 05. `STATE.md:7` therefore prints `relay=PASS` even though the Claude Code drill has not run
(`KNOWN_ISSUES.md:16`, `ROADMAP.md:15`). Probe E7 deletes the Codex drill entirely and the checker
still passes. 08 required tests for "missing Codex/Claude drill evidence"; none exist.

**Action:**

1. Split the relay lineage into `relay-codex` and `relay-claude-code`, or declare
   `required_drills` in the manifest.
2. Allow a pending drill state that counts as open, and make the STATE summary show it
   (for example `relay-claude-code=PENDING`).
3. Fail the checker whenever a declared drill has no report.
4. Add a test for each of these cases.

### NF3 — Medium: lineage ordering, the remediation-name exemption and HANDOFF freshness are unchecked

**Evidence:**

- `check_relay.py:116-128` never checks that `current` is the newest report in its lineage (probe
  E4).
- `:139` exempts every filename containing `remediation`, including a mislabelled verdict report
  (probe E5).
- HANDOFF is read only when something is blocking, and only for the substrings `BLOCK` and
  `re-review` (`:145-149`). A stale BLOCK narrative therefore survives when all streams are clear
  (probe E6).
- A contradictory second summary line in STATE is not detected (probe E9).

**Action:**

1. Require `current` to have the highest numeric prefix among the lineage's current and
   superseded reports.
2. Require remediation files to declare `Responds to:` naming a report in the manifest, and to
   contain no verdict line.
3. Require exactly one `Review status manifest:` line in STATE and a matching structured line in
   HANDOFF.
4. Add tests for each of these checks.

### NF4 — Medium: recorded validation state is stale, and the checker forces the misleading line

**Evidence:** `STATE.md:40-43` says "3 passed", "`git diff --check`: passed" and "50 files". The
actual figures are 5 tests, zero tracked files and 56 Markdown files. `HANDOFF.md:34` says five
tests. `check_relay.py:31` requires the literal `git diff --check` to appear in STATE.

**Action:**

1. Change the STATE entry to "`git diff --check`: exit 0, no tracked files (no coverage);
   untracked-aware whitespace is enforced by `tools/check_relay.py`".
2. Or make `VALIDATION_MARKERS` name the checker's workspace-text check instead of `git diff --check`.
3. Update the test and file counts.

### NF5 — Medium: S01 baseline details that still allow divergent runs

**Evidence and action:**

1. **Interpreter.** On this host, bare `python3` resolves to Anaconda CPython 3.12.4 with SQLite
   3.45.3, not to the 3.13.3/3.53.2 baseline. `plans/00-phase-0-spikes.md:30-35` should require
   the S01 command to call the pinned interpreter explicitly. The S01 result should record
   `sys.executable`, `sys.version`, `sqlite3.sqlite_version`, `sw_vers` and `mount`, and fail when
   any of them differs from the baseline.
2. **Volume.** "Local APFS root volume" (`COMPATIBILITY.md:5`) is imprecise. The root is the sealed,
   read-only system volume; user files live on the APFS data volume (`/System/Volumes/Data`). Name
   the data volume.
3. **Fail-closed test.** "Unknown/network/synced filesystems fail closed" has no detection method
   and no negative probe. Specify detection, for example `statfs` `f_fstypename` plus the local
   flag and a denylist of known sync-provider roots. Add S01 negative cases, such as an injected
   non-APFS or non-local `statfs` result and a synced-root path, that must refuse.
4. **Linux owner.** The M1.1 Linux/ext4 admission (`COMPATIBILITY.md:15`, `SPIKES.md:30-31`) has
   no owner in `ROADMAP.md:23-39` or in Slice 3 of `plans/01-foundation-tdd.md`. Add it as an
   explicit M1.1 exit item that reruns the S01 concurrency/crash suite on the exact ext4 runner.
   The remediation note says ROADMAP was changed, but ROADMAP contains no baseline or ext4 text.

### NF6 — High (not a Gate 0 blocker; must close before M1.3 thresholds freeze): remaining ambiguity in the context-noise and setup metrics

**Evidence:** `EVALUATION_PLAN.md:20` does not define:

- the judged segment granularity (whole record, field or byte span);
- the result for empty output, where 0/0 is undefined;
- how disagreements between judges are resolved;
- the "fixed per-record/metadata overhead" constant (ADR-0005:80-82 leaves it unnamed);
- a versioned annotation example.

`EVALUATION_PLAN.md:23` refers to eligible success cases and expected refusal cases, but
`plans/02-onboarding-advisor.md:31-38` does not assign rows A–G to either class. Row B is mixed:
content-free setup succeeds while personal release is refused. Rows F (cancellation) and G (crash)
fit neither class.

**Action:**

1. Specify record-level (or span-level) judgement.
2. Define empty output: a correct empty answer scores 0% noise and is counted separately; an empty
   answer where relevant items existed fails recall.
3. Use two independent judges, with adjudication by a third or by the maintainer, and treat ties
   as irrelevant (the conservative choice).
4. Pin the overhead constant and add a checksummed worked example.
5. Tag each onboarding row with its assertions: success, refusal, or both for B. Classify F and G
   separately and require at least one case per class.

### NF7 — Low: prior-version compatibility still has no predeclared version or waiver owner

**Action:** before S04/S12, record the preceding stable version for Claude Code and Codex. Replace
"release-blocking/documented unsupported" with a single rule: the gap is release-blocking unless a
waiver in `KNOWN_ISSUES.md` records the attempted source, the reason and reviewer approval.
Separately, confirm Codex CLI 0.153.4; this session could not.

### NF8 — Low (procedural): the checker will fail until this report is registered

Probe E0 shows that adding this file makes `tools/check_relay.py` fail with "absent from lineage
manifest". This is correct behaviour. The authors should set `execution.current` to this file, add
08 to `supersedes`, set the verdict below, and update the `STATE.md:7` summary line. Separately,
the claim that "a failing unit test was added first" cannot be verified, because there is no Git
history.

## Execution evidence versus planned evidence

- **Actually executed in this review:** the 5 relay unit tests, the relay checker, `git diff --check`
  (which checks nothing because no files are tracked), the host-baseline facts above, and nine
  checker probes under `/private/tmp`.
- **Still planned:** S01–S05A, all M1 checks, the four host×locale journeys, onboarding E2E, and
  the evaluation suite.
- **Still missing:** the cold Claude Code relay drill. The roadmap records it honestly, but the
  checker cannot detect that it is missing (NF2).

## Verdict

The blocking parts of N1 and N2 are resolved at the planning level. Historical verdicts no longer
block for ever, the lineage is recorded in a machine-readable manifest, and the Gate 0 S01 matrix is
exact and does not depend on later CI. No remaining defect makes the plan unexecutable or its gates
undecidable, because each report carries an explicit final verdict line that a reviewer can resolve.

Two conditions apply:

1. NF1 and NF2 must be fixed and tested before `tools/check_relay.py` counts as Gate 0 relay evidence
   or as ADR-0008 acceptance evidence.
2. NF6 must be fixed before the M1.3 evaluation thresholds are frozen.

NF3–NF5 should be fixed before S01 runs.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

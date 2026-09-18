# Focused Execution and Test Re-review

- **Date:** 2026-09-18
- **Re-reviews:** `03-execution-test-review.md`
- **Remediation under review:** `03-execution-test-remediation.md` and the artifacts it cites
- **Evidence rule:** a revised plan can close a planning defect, but it is not execution proof. Only
  commands/results recorded from an actual run count as execution evidence.

## Validation performed

The following commands were run in this re-review before and after inspecting the artifacts:

```text
python3 -m unittest tests/dev/test_check_relay.py
Ran 3 tests — OK

python3 tools/check_relay.py
relay check passed

git diff --check
exit 0
```

The `git diff --check` result has the untracked-tree limitation described in N3 below. No S01–S05A
result exists, so this report does not claim those spikes passed. The cold Codex report is evidence
for one relay journey only; the cold Claude Code journey remains pending and the roadmap correctly
keeps that Gate 0 checkbox open.

## Original blocking findings

### B1 — S04 egress boundary: CLOSED at planning level

`SPIKES.md:58-74` and `plans/00-phase-0-spikes.md:54-67` now separate denied
server/dependency socket activity from expected bounded STDIO disclosure. Hosted probes are
synthetic, the host/vendor boundary is recorded separately, and unexpected destinations fail. The
criterion is now binary enough to execute. It remains unproven until S04 produces a result artifact.

### B2 — S01 concurrency: PARTIALLY CLOSED; see blocking N2

`SPIKES.md:19-31` and `plans/00-phase-0-spikes.md:21-34` now include simultaneous append/supersede,
stale writers, lock crash/recovery, reader-during-commit, directory durability, lost updates, and a
single valid serial outcome. The missing exact Gate 0 OS/filesystem matrix still prevents an
unambiguous pass; N2 keeps this finding open.

### B3 — S05 ordering: CLOSED at planning level

`SPIKES.md:76-92`, `plans/00-phase-0-spikes.md:69-78`, `MVP_DEPENDENCY_GRAPH.md:8-16`, and
`ROADMAP.md:14` consistently split S05A before v1 freeze from provider-specific S05B before each
provider ships. The graph has no remaining contradictory edge.

### B4 — Plugin Advisor/install flow: CLOSED at planning level

`ROADMAP.md:63-76` owns the MVP deliverable and `plans/02-onboarding-advisor.md` supplies a bounded
state machine, the fifteen required steps, bilingual cases, cancellation at every point, one final
confirmation, crash resume/rollback, doctor/smoke, and Vault-location output. Successful and refusal
cases are distinct. Security properties of the confirmation issuer remain governed by the separate
security review.

## Original high-priority findings

### H1 — Build/install verification: CLOSED at planning level

`plans/01-foundation-tdd.md:37-51` now requires sdist and wheel builds, non-editable clean installs,
schema/translation/entry-point smoke tests, CI parity, wheelhouse installation with sockets denied,
and a separate offline-runtime test. `COMPATIBILITY.md` carries the planned Python/OS/host/locale
matrix. These checks have not run because the production scaffold is still gated.

### H2 — Migration/backup recovery: CLOSED at planning level

`plans/01-foundation-tdd.md:67-86` adds transaction/version markers, per-step fault injection,
idempotent resume, unknown-newer-version refusal, last-known-good restore, corrupted-generation
fallback, backup verification before rotation, and pre-purge restore without resurrection. These
are now M1.1 requirements rather than an M1.5-only drill.

### H3 — Product evaluation: PARTIALLY CLOSED; see high N4

`EVALUATION_PLAN.md` assigns automated gates, thresholds, fixture/checksum discipline, holdouts,
machine-readable run manifests, and human/dogfood scorecards. This is substantial closure. The setup
success metric still admits an all-refusal pass, and `response unit` is not yet defined; N4 must be
resolved before accepting the M1.3 evaluation plan.

### H4 — Bilingual/cross-host matrix: CLOSED at planning level with one medium follow-up

`COMPATIBILITY.md` covers Python/OS/SQLite/host/locale dimensions, four Claude/Codex × en/zh-CN
journeys, CJK paths, mixed queries, normalization, fallback, untranslated-key failure, and upgrade
behavior. Exact host/SQLite versions are explicitly outputs of S03/S04/S12, so their current absence
is not falsely presented as proof. The optional prior-minor wording remains non-binary; see N5.

### H5 — Relay checks and cold relay: OPEN; see blocking N1

The checker and its three tests are real and passed. `05-cold-codex-relay-drill.md` is useful partial
evidence and explicitly states that production remains blocked. The cold Claude Code drill is still
missing, which is honestly recorded in `ROADMAP.md:15` and the Codex drill. However, the checker does
not actually determine current review verdicts or stale handoff state; N1 is a functional blocker,
not merely missing evidence.

### H6 — Policy completion boundary: CLOSED at planning level

`plans/01-foundation-tdd.md:88-99` narrows M1.1 completion to the policy contract and mandatory
application-port shape, then requires each later persistence/exposure slice to enumerate entry
points and test epoch propagation and final exposure recheck.

## Original medium-priority findings

### M1 — Plan-acceptance gate: CLOSED

`ROADMAP.md:107-113` prohibits starting a milestone/slice without an accepted TDD plan naming
ownership, fixtures, failure cases, exact commands, and exit evidence, while deferring detailed
planning until upstream contracts stabilize.

### M2 — S03 threshold precommit: CLOSED

`SPIKES.md:46-56` and `plans/00-phase-0-spikes.md:46-52` freeze/checksum corpus, judgments, metric
code, numeric thresholds, and an untouched holdout before comparison; the runner must exit non-zero
on any missed threshold.

### M3 — Binary verification language: CLOSED

`plans/01-foundation-tdd.md:134-145` names mandatory temporal, memory, authority, policy, and purge
properties; surviving critical mutants require a recorded test or reviewed exception; documentation
examples are executable. `ROADMAP.md:107-113` makes recorded binary evidence a completion rule.

### M4 — Skills/repository artifacts: CLOSED at planning level

`ROADMAP.md:78-90` assigns `CITATION.cff`, `CODEOWNERS`, `THIRD_PARTY_NOTICES.md`, and four
post-contract skills to M1.5, each with a fixture smoke test. Deferring them until contracts exist
avoids premature scaffolding.

### M5 — Package placeholder: CLOSED

`plans/01-foundation-tdd.md:3-6` and its file tree use `personal-context-core`,
`personal_context_core`, and `personal-context`, and preserve a separate public-rename migration
gate.

## New findings

### N1 — Blocking: relay verdict detection cannot distinguish current from historical review state

**Locations:** `tools/check_relay.py:32`, `tools/check_relay.py:86-105`,
`tests/dev/test_check_relay.py:17-55`, `05-cold-codex-relay-drill.md:81-85`

`check_review_state` searches every non-remediation report for any occurrence of `BLOCK`, not a
single declared final verdict or a supersession chain. Historical blocking reports must remain in
the repository, so `blocking` stays true after a focused re-review approves them. Conversely, the
check passes as long as STATE/HANDOFF contain the substrings `BLOCK` and `re-review`, even if those
files describe an obsolete blocker. A cold-drill report with a `PASS` verdict is accepted only by
accident because its prose also contains `BLOCK`; `PASS` is not in the verdict regex. None of the
three unit tests exercises review-state parsing.

This prevents the promised stale-handoff detector from deciding when Gate 0 is actually clear and
can force agents either to retain stale BLOCK text or bypass the checker.

**Required fix:** define machine-readable review identity/scope/final-verdict/supersedes fields;
parse exactly one final verdict per report; resolve the latest verdict per review lineage; support
cold-drill `PASS`/`FAIL` separately; compare the resolved open blockers and required drill artifacts
with structured STATE/HANDOFF fields. Add tests for historical BLOCK → approved re-review, latest
BLOCK, missing/multiple verdicts, unrelated prose containing verdict words, and missing Codex/Claude
drill evidence.

### N2 — Blocking: S01's Gate 0 platform/filesystem matrix is circular and still undefined

**Locations:** `SPIKES.md:26-31`, `plans/00-phase-0-spikes.md:30-34`,
`COMPATIBILITY.md:3-16`, `ROADMAP.md:14-19`

S01 must pass on the "supported OS/filesystem matrix" before Gate 0 exits, but
`COMPATIBILITY.md` names only "current supported macOS and Ubuntu LTS runners" and says exact OS
versions are pinned later in CI. CI is created in M1.1 Slice 1, which cannot start until Gate 0 has
already passed. The filesystem types and local/CI environments are not listed at all. Therefore two
agents can run different matrices and both claim S01 acceptance.

**Required fix:** predeclare an exact Gate 0 S01 proof matrix now, including OS version, filesystem,
local/VM/runner mechanism, Python version, and unsupported/network-filesystem policy. Make every
required row produce the same concurrency/crash evidence or explicitly scope MVP support more
narrowly. The later production CI matrix may expand it, but it cannot retroactively define a Gate 0
acceptance input.

### N3 — High: the recorded `git diff --check` evidence does not cover this repository

**Locations:** `STATE.md:33-40`, `HANDOFF.md:31-35`,
`05-cold-codex-relay-drill.md:78-80`, `05-cold-codex-relay-drill.md:97-113`

The working tree has no initial commit and all current files are untracked. Plain
`git diff --check` therefore checks none of their contents, yet STATE/HANDOFF record it as a passed
validation without the caveat. The Codex drill correctly identifies this limitation, so the current
summary overstates the evidence.

**Action:** add an untracked-aware whitespace validation command (or create the reviewed initial
checkpoint when authorized), test it, and record the exact command/result. Until then, describe
plain `git diff --check` only as exit 0 with no tracked-diff coverage.

### N4 — High: two evaluation gates still have pass-by-ambiguity loopholes

**Locations:** `EVALUATION_PLAN.md` automated-gate table and corpus discipline,
`plans/02-onboarding-advisor.md:25-44`

`Setup success` counts journeys "completing or safely refusing" at 100%, so an implementation that
safely refuses every supported journey can pass. `Context noise` divides irrelevant response units
by total response units without defining a response unit or how judges segment/count it, so separate
runners can produce different scores from the same output.

**Action:** split supported-success cases from predeclared safe-refusal cases and require every
supported case to complete. Define response-unit segmentation, empty-output handling, judge tie
resolution, and a versioned annotation example before freezing thresholds.

### N5 — Medium: the prior-host-minor compatibility promise is non-binary

**Location:** `COMPATIBILITY.md:15`

"One prior compatible minor tested where installable" has no owner or waiver artifact and allows a
silent skip.

**Action:** predeclare the prior version for each host before S04/S12, or require a recorded
unavailable-version waiver with attempted source, reason, and reviewer approval; otherwise remove
the compatibility promise from M1 support.

## Execution evidence versus planned evidence

- **Actually executed:** three relay-checker unit tests, the current relay checker, one cold Codex
  reconstruction, and the commands listed at the top of this report.
- **Still planned:** S01–S05A, all M1 production checks, four host×locale journeys, onboarding E2E,
  migration/restore matrix, evaluation suite, and built-artifact/CI installation.
- **Still missing:** cold Claude Code relay drill. Its absence is explicitly gated and is not papered
  over by the remediation.

## Verdict

**BLOCK**

B1, B3, B4, H1, H2, H4, H6, and M1–M5 are adequately remediated at the planning level. B2/H5 remain
open through N2/N1. Gate 0 cannot rely on a concurrency spike whose required platform/filesystem
matrix is defined only after the gate, or on a relay checker that cannot resolve current verdicts
from historical reports. N3 and N4 must be fixed before their affected evidence is accepted; N5 is
non-blocking if it is converted into an explicit compatibility gap. Independently, S01–S05A and the
cold Claude Code drill still need real execution before Gate 0 can close.

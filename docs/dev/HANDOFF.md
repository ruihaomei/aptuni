# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; beta-agent-led-setup=APPROVE_WITH_NON_BLOCKING_NOTES; beta-attach-consent=APPROVE_WITH_NON_BLOCKING_NOTES; beta-b9-autosave-diversify=APPROVE_WITH_NON_BLOCKING_NOTES; beta-concept-queries=APPROVE_WITH_NON_BLOCKING_NOTES; beta-credential-guard=APPROVE_WITH_NON_BLOCKING_NOTES; beta-day0-fixes=APPROVE_WITH_NON_BLOCKING_NOTES; beta-day1-activation-fixes=APPROVE_WITH_NON_BLOCKING_NOTES; beta-e2e-research-harness=APPROVE_WITH_NON_BLOCKING_NOTES; beta-evidence-profile=APPROVE_WITH_NON_BLOCKING_NOTES; beta-knowledge-model=APPROVE_WITH_NON_BLOCKING_NOTES; beta-orchestration-guidance=APPROVE_WITH_NON_BLOCKING_NOTES; beta-stable-readiness-gate=APPROVE_WITH_NON_BLOCKING_NOTES; beta-top-down-flagship=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-ci-supply-chain=APPROVE_WITH_NON_BLOCKING_NOTES; m1-evaluation-harness=APPROVE; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-owner-backup-restore=APPROVE; m1-post-contract-skills=APPROVE; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-real-host-s12=APPROVE; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; m2-automatic-promotion=APPROVE_WITH_NON_BLOCKING_NOTES; m2-github-deep=APPROVE_WITH_NON_BLOCKING_NOTES; m2-hybrid-retrieval=APPROVE_WITH_NON_BLOCKING_NOTES; m2-longitudinal-dogfooding=APPROVE; m2-mem0-admission=APPROVE_WITH_NON_BLOCKING_NOTES; m2-mem0-projection-adapter=APPROVE_WITH_NON_BLOCKING_NOTES; m2-notion-source=APPROVE_WITH_NON_BLOCKING_NOTES; m2-obsidian-interface=APPROVE; m2-obsidian-source=APPROVE_WITH_NON_BLOCKING_NOTES; m2-profile-promotion=APPROVE_WITH_NON_BLOCKING_NOTES; m3-beta-agent-activation=APPROVE; m3-beta-plugin-context=APPROVE; m3-beta-top-down-agent-plugin=APPROVE; m3-context-evidence-rank=APPROVE_WITH_NON_BLOCKING_NOTES; m3-notion-activation-delta=APPROVE_WITH_NON_BLOCKING_NOTES; m3-notion-credential-hardening=APPROVE_WITH_NON_BLOCKING_NOTES; m3-notion-token-expiry=APPROVE_WITH_NON_BLOCKING_NOTES; m3-owner-labelled-evaluation=APPROVE_WITH_NON_BLOCKING_NOTES; m3-public-api-plugin-platform=APPROVE; m3-real-activation=APPROVE; relay-claude-code=PASS; relay-codex=PASS; release=APPROVE_WITH_NON_BLOCKING_NOTES; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Mode: 14-day real-user dogfooding (from 2026-10-01)

Dogfooding, not feature-chasing. The owner uses Aptuni in ordinary Agent sessions; agents use it
naturally, never turn routine work into testing, and record meaningful friction quietly (content-free)
in `docs/dev/BETA_DOGFOODING.md` → "Observations inbox". Surface an issue during the owner's task only
if it is P0/P1, risky, or needs a decision. P0/P1: fix with a regression test and a new Beta under the
release policy; everything smaller is batched (next setup/onboarding slice: the bundled
"one-conversation setup" item in BACKLOG). Beta/Stable gates stay open: ≥14 days with a clean final
7, ≥30 owner-scored real trials, automated Stable gate, and the owner's explicit UX Gate decision.
Development sessions triage the inbox into the defect table / daily log / BACKLOG and commit.

## Current position

**2026-10-03 current b10 research checkpoint (preceding local commit `1908b97`).**
Explicit owner activation is settled; no automatic OFF→Full. Full-session ordinary
prompts autonomously decide relevance. Both actual runners recovered without grant,
credential or network changes; global Codex model line now uses a verified available
GPT-6 Astra route. Both installed skills are generator-identical.

Frozen seven unchanged, all completed, independent strict E2E: Sonnet 4.6 **2/7**,
Codex Astra xhigh **6/7**; relevance inside Full **7/7 each**. The old 1/10 is only
pre-consolidation. No b10 release. Current results and per-task content-free token,
call and latency tables: `b10-continuation/frozen-unseen-results.md`.

Concrete next slice: **synthetic bounded discovery falsifier**. Two blind task-based
project-goal lists yield no project evidence; an independently planned oracle anchor
recovers an eligible tentative candidate, never counted as product success. Current
Context omits repository provenance from search/discovery. Manager froze two invented
worlds with identical labels/task but owner work versus study-only Evidence. Run that
small contrast before production discovery or B/C/D orchestration. Research runner
`tools/agent_e2e_run.py` and accounting `tools/agent_e2e.py` are runnable, Review 98
approved for validated environment (14 focused tests; full suite: 1,263 passed, 3 skips, 62 subtests; 70 developer checks; Ruff, mypy and relay green). Original confinement limitation
and reconstructed legacy manifests are disclosed; corrected runner checks effective
capabilities, exact MCP catalog, clean Full setup, snapshots and failed-run accounting.

Private restart directory: `/private/tmp/aptuni-b10-continuation/`. Original seven
hash ends `…784c3a`; independently curated six-task hash ends `…df16e26` remains
sealed, unread by candidate planners. Never tune against it before freezing a finalist.
Local raw research traces must be deleted after this phase's grading/review; preserve
preexisting inputs/evidence and both owner backups. No production behavior changed.
Do not repeat completed credential research; external copies/rotation stay unverified,
old pre-b9 backup retained. Follow current report, not historical pending-policy or
quota blockers below. No owner decision currently blocks these reversible experiments.

Historical checkpoints follow.

**Post-purge b10 checkpoint (2026-10-02; `b8ba178`, local, NOT released).** Owner
confirmed `act-dbba0c2dfd65f28e`; receipt is `complete_managed_external_action_needed`.
Live commit 62: 110,194 records, doctor healthy, credential inventory zero, both incident
ids absent, all 125 unrelated exposable Evidence records in the affected source retained.
Claude/Codex active grants restored with original scopes under explicit owner chat
authorization; Claude plugin reinstalled, Codex MCP points to the guarded checkout and
four generated user skills installed. Real STDIO initialization confirms new descriptions
and OFF mode for both. The older superseded Claude grant and unrelated developer-plugin
grant remain revoked. Installed public CLI is still b9; these adapters use this checkout.

Original ten runs graded without rerun: **one pass with note, nine failures**, 19 retrieval
attempts (15 successful, four refused), five single-call tasks, four multi-call tasks and
one missed invocation. First-call concept median four / max five. General guidance fix:
relevance decision, one consolidated concept/module plan, one justified replacement-term
retry, precise programme/role/project anchors, correct task/session semantics and no
mastery/progress inference from mentions/titles. Review 97 approved with non-blocking
notes; host parity note applied. Full gate: 1263 passed, three optional skips, 62 subtests;
Ruff, strict mypy, relay, 56 developer checks, secret scan and frozen evaluations pass.

**Actual blockers:** fresh seven-task mini-holdout locked privately, not run. Claude
capacity canary is exhausted until its stated 20:40 Asia/Shanghai reset; local Codex CLI
rejects its configured model before producing a response. No model/auth/network defaults
changed to compensate. Maintainer was asked whether normal prompts apply inside explicit
session Full (preserve ADR-0025) or require automatic task activation (new privacy policy).
No answer yet; keep OFF-by-default and do not change that contract. Do not reuse original
tasks as proof or claim text tests establish Agent compliance. Next: resolve policy, use
an available real host for locked unseen validation, grade honestly; fresh set after any
further generalizable fix. Release b10 only on complete product pass.

Credential-clean post-purge backup created and independently verified; zero detector hits,
zero incident ids, two ledger digests. Comparison to the 2026-10-01 backup retains every
unrelated old canonical record; only the old incident id is absent. Old backup has one
credential hit and remains on disk. It can be retired for current-state recovery after
explicit deletion authorization, but that also abandons its pre-b9 downgrade checkpoint.
Rotation and copies outside managed storage are owner-only and unverified. Details and
all requested outcomes: `docs/dev/b10-continuation/report.md`.

**b10 continuation: exact owner boundary (2026-10-02).** Review 96 is committed at
`7fa5c6d`, APPROVE WITH NON-BLOCKING NOTES. Focused credential baseline: 104 passed.
Live `doctor`: commit 61, 110,196 records, healthy; exactly the two known incident
history records, neither current/exposable. Live targeted credential-history preview
selects exactly those two records and zero sources; 125 unrelated exposable Evidence
records remain in that source. No deletion/revocation performed. ADR-0013 item 2
requires owner CLI confirmation (agents never approve), even though scripted digest
confirmation exists. Run the preview/confirm using `.tools/bin/uv run aptuni` in
this checkout; previews expire in ten minutes. After confirmation: verify doctor,
zero credential records, unrelated source data and restore adapter grants; then grade
the preserved original ten `cg/runs/holdout` runs before any guidance change. See
`docs/dev/b10-continuation/` for plan, findings and checkpoint report. No b10 release,
new clean backup or old backup deletion.

**Credential P1 + concept guidance (2026-10-02, local, NOT released; b10 gate open).**
Checkpoints: `ff3e396`, `606e722`, `6660ae2` (credential guard: Review 93 B1–B3, Review 94 and 95
blockers closed; `aptuni privacy purge preview --credential-history` erases withdrawn credential
Evidence chains without a source-wide purge — rehearsed on a scratch Vault copy, NOT run on the real
Vault; it also revokes adapter grants), `a2978fd` (ADR-0030 amendment: "usually 1-4 specific
concepts"; dev eval median 8→3 concepts, nDCG@5 0.755→0.769, leakage 1/5→0/5). Review 96 (narrow
re-review of `6660ae2`) was dispatched; check `docs/dev/reviews/96-*` and STATUS.json, then commit it.
Held-out end-to-end run (10 tasks, scratch `cg/runs/holdout`, not yet graded) shows product failures:
h01 (long zh career plan) made ≥5 calls with broad concepts; h04 broad concepts; h10 (zh research)
never called Aptuni. Next: grade the held-out run honestly, decide whether a generalizable guidance
fix is needed (then a fresh mini-holdout), owner decides on running the credential-history purge
(typed PURGE) before a credential-clean backup; b10 only after all gates pass.

**Retrieval investigation → ADR-0030 (2026-10-02, local, not released).** Maintainer brief: own
retrieval quality. Local read-only experiments on User #1's Vault (62 queries, 1,282 graded
judgments; findings in `docs/research/findings/retrieval-experiments.md`) found that letting the host
name `concepts`, each matched whole, beats b9 decisively (nDCG@5 0.629→0.866, should-be-empty
leakage 67%→0%) with no dependency; IDF gates, jieba, dense (MiniLM) and a cross-encoder were
rejected or deferred. Implemented test-first: Context API/MCP/CLI `concepts`, concept-mode projection
search, skills and tool descriptions (checkpoints `3df9ad0`, `c50f6bf`, `e9b693a`; Review 92 APPROVE WITH NON-BLOCKING NOTES, notes
N1–N4 applied in the final checkpoint). A folder-source note with credentials is exposable to Agents —
owner decision pending (BETA_DOGFOODING). **Next:** the owner decides on a 0.2.0b10 release and on
the credential note.

**0.2.0b9 candidate (2026-10-01, local).** Two changes since b8, both maintainer-requested: (1) owner
opt-in to save Agent memory proposals without confirmation (ADR-0018 2026-10-01 amendment,
`aptuni memory review policy --host-proposals on`, ReviewPolicy schema 2); (2) Context concept
diversification (ADR-0005 2026-10-01 amendment) from local MVP retrieval experiments
(`docs/research/findings/retrieval-experiments.md`: dedupe-and-demote adopted; jieba and a small dense
model rejected). The Claude grant now includes `memory.propose` (grant-2176e4d82effbba1, plugin
reinstalled). Reviews 88 BLOCK → 89 APPROVE WITH NON-BLOCKING NOTES. **0.2.0b8 and 0.2.0b9 are public (2026-10-01;
records `docs/dev/releases/0.2.0b8.md`, `0.2.0b9.md`).** User #1 runs 0.2.0b9 with Agent auto-save on
(backup taken first). Next: keep dogfooding; triage the inbox; BACKLOG holds Review 88/89 notes.

**Day 1 dogfooding P1 fixes (2026-10-01, local, not released).** A real `/aptuni:full` task got no
usable context. Root causes (the Vault and server were correct): Agent keyword-list queries had no
task language, so one absent keyword emptied the lexical result; multi-module refusals and the
memory-proposal refusal were bare codes (the Claude grant also lacks `memory.propose`). Fixed
test-first under ADR-0004 and ADR-0025 2026-10-01 amendments: whole-keyword fallback for 2+
whitespace/punctuation-separated keywords (frozen S03 metrics unchanged), guided refusal messages
built only from module/scope names, `aptuni_activation_status` adds `granted_modules` and
`memory_proposals`, proposal checks scope before session, Full skill guidance. Review 86 BLOCK →
remediated → Review 87 APPROVE WITH NON-BLOCKING NOTES; checkpoint `8795336`. **0.2.0b8 is public (2026-10-01).** after upgrading, regenerate the Claude/Codex bundles to get the
new skill text, and re-plan the adapter with `--allow-memory-proposals` if Agents should save memories.

**General Knowledge Evidence Model (ADR-0029) is implemented, reviewed and public as Aptuni 0.2.0b7.** Authority is a ceiling (Vault invariant), MarginNote cards and GitHub concept items are
classified item by item, `source authorize` re-derives through the classifier (now also
`--grant knowledge.applied` for GitHub), `aptuni source reclassify SOURCE_ID` migrates ADR-0028
blanket labels after a typed APPLY, and a derived Knowledge State powers `aptuni knowledge [QUERY]`
and a compact `aptuni.profile`. Code: `src/aptuni/knowledge/` (concepts, code_usage, classify,
state), `sources/github_concepts.py`, `application/knowledge_commands.py`,
`application/source_authority.py`, `cli/knowledge_cli.py`. Review 85 APPROVE_WITH_NON_BLOCKING_NOTES;
remediation applied. Full pytest, Ruff, strict mypy and relay green. Real-Vault rehearsal (scratch
copy, deleted): 3,737 downgrades, 22,678 studied Facts remain, idempotent.

**Release:** 0.2.0b7 is public (maintainer chose "Publish 0.2.0b7" on 2026-09-30; PyPI + GitHub
pre-release from `638d5d0`, byte-identical artifacts; record `docs/dev/releases/0.2.0b7.md`).
**Next:** User #1 upgrades (`uv tool install aptuni==0.2.0b7`; the tool is exact-pinned, so `uv tool upgrade` stays on the old version), backs up and runs, themselves: `aptuni source reclassify <MarginNote source id>`, optionally
`aptuni source authorize <GitHub source id> --grant knowledge.applied` per repository after a sync,
then `aptuni knowledge` and a real `$aptuni-profile` / `/aptuni:profile` task. Do not tune the
classifier thresholds before owner-labelled evidence.

### Previous position (ADR-0028)

Evidence-derived cold-start Profile is implemented locally under accepted ADR-0028, but is not yet
checkpointed or release-ready. The gap was real: source sync admitted Evidence but nothing consumed
it into Profile. Strong, exact-authority Evidence now creates active deterministic Profile Facts;
Profile activation also retrieves permitted exposure Evidence. The source→Memory shortcut is
deliberately rejected because Memory is interaction-derived. CLI and Obsidian support retrospective
reject/edit without an approval queue, sync reports `profile_written`, no-op sync and `profile refresh` backfill eligible
older strong Evidence, source withdrawal hides derived Facts, and owner corrections remain in
control. Full pytest, Ruff and strict mypy are green; the live Vault was not changed.

Review 82 BLOCKED on five findings; all are remediated test-first (ADR-0028 items 4, 5, 7–10):
successor Facts follow the Evidence lineage and owner reject/edit is permanent across it, `accept`
is refused; the invariant enforces the whole derivation (allow-list, deterministic ids, digest,
exact time/confidence, lineage); setup binds MarginNote authority into the digest and states it in
en/zh, while older plans keep their exposure-only meaning; `aptuni source authorize SOURCE_ID
--grant knowledge.studied` is the owner-confirmed upgrade for an existing source (schema-v3 grant,
Evidence re-derived as corrections, Facts in one commit); derivation/validation are linear (27k:
sync ~5.6 s, grant ~4.3 s, doctor ~3 s). Review 83 blocked on a single-Fact purge freezing sync;
the writer now treats ledger-purged lineage ids as a permanent withdrawal. Review 84 is
APPROVE_WITH_NON_BLOCKING_NOTES; notes are in BACKLOG. Full pytest (1043), Ruff, strict mypy and relay
are green; checkpoint `e8d72a9`. **Aptuni 0.2.0b5 is public (2026-09-30, maintainer-authorized;
record `docs/dev/releases/0.2.0b5.md`)** with ADR-0028 and the empty-GitHub-repository fix (Day 0 P2).
**Aptuni 0.2.0b6 is public (2026-09-30; record `docs/dev/releases/0.2.0b6.md`)** and fixes the first real `source authorize`: 2 of 26,417
titles ('mastery', 'proficient') tripped the no-proficiency invariant and refused the whole batch;
such topics now stay Evidence (verified on a scratch copy of the real Vault: 26,415 facts). After it is installed, User #1 backs up
and runs `aptuni source authorize <MarginNote source id> --grant knowledge.studied` themselves; the
agent never runs it for them.

**Aptuni 0.2.0b4 is public (2026-09-29, maintainer-authorized; record `docs/dev/releases/0.2.0b4.md`).** Day 0 on public 0.2.0b3
stopped at setup's sync step before any grant; ten defects are fixed test-first in `41b27c2..`
(oversized GitHub files skipped; real GitHub error codes; unreadable sources reported instead of
stopping setup, with progress; token notice, 24 h plans, confirmed setups never expire; readable
CJK with confusables escaped; `status --lang`; Agent-guide token/placeholder rules;
`aptuni source remove` per ADR-0027 with a repair path for older builds). Reviews 80 BLOCK → 81
APPROVE_WITH_NON_BLOCKING_NOTES; notes in BACKLOG. Next: User #1 upgrades to 0.2.0b4 and
resumes `setup-27676f7afb011ba3`.

**Beta 0.2.0b3 is public (2026-09-29, maintainer-authorized; record `docs/dev/releases/0.2.0b3.md`).** 0.2.0b2 is public (record
`docs/dev/releases/0.2.0b2.md`). A returning-user P1 found while preparing Day 0 — setup planned a new
`~/Aptuni` after `aptuni attach` and failed after APPLY — is fixed in 0.2.0b3, with scripted
MarginNote deferred like Notion. Top-Down Learning stays 0.2.1. User #1 now runs public b3 with the real Vault
attached (unchanged). Next: Day 0 in a fresh Agent session led by `aptuni guide agent`.

Canonical Beta Agent activation is runnable under accepted ADR-0025 and approved by Review 70.
Official Claude Code and Codex bundles start OFF, have no automatic personal-context hook, and map
manual-only Profile/Memory/Full skills to host-independent intents. Task activation is one bounded
disclosure; only Full can persist for an inspectable and disableable MCP-process session. OFF denies
new retrieval, capture and disclosure. It cannot erase content already delivered into a capable
host transcript; strict isolation requires a new host task, chat or session. The implementation
checkpoint is `d40d037`; it is local and has not been pushed.

The additive plugin context declaration is also runnable and approved by Review 71. New manifests
use `[aptuni] required/optional`; the existing grant remains the only authority, legacy v1 digests
and stored grants stay valid, and every operation still revalidates revocation, modules and privacy.
The Top-Down learning journey works with required context alone; optional memory capture fails
closed when the owner withholds it. Its implementation checkpoint is `358eed3`; it is local and has
not been pushed.

The Top-Down Learning flagship is now a real separately installable Agent plugin and Review 72 is
APPROVE. Claude Code uses `/top-down-learning:top-down-study`; Codex uses `$top-down-study`. Both
manual skills call the same no-egress STDIO server under one exact owner grant, expose only the
current task-relevant teaching turn and advance through an integrity-bound continuation. Optional
gap capture remains quarantined and fail-closed when withheld. Aptuni's selected Beta candidate is
`0.2.0b1`; a fresh isolated uv-tool install plus init, grant and installed-server call passed. The
implementation checkpoint is `fa84625`; it is local and has not been pushed.

Milestone 2. Runnable: Vault/CLI core; Folder, GitHub and direct local MarginNote 4 sources; builtin
interaction memory with quarantined MCP proposals; bilingual SQLite/FTS; bounded Context API; MCP
STDIO; Claude/Codex adapters; owner-readable Profile export; the Plugin Advisor; privacy
inventory/purge with atomic chain-preserving restore; digest-bound guided setup through doctor and
smoke; verified owner backup/restore; hosted CI/supply-chain gates; the accepted versioned
production evaluation harness; four executable post-contract agent skills; and the exact frozen
Claude/Codex real-host S12 journeys. Milestone 1 is complete. Aptuni 0.1.0 is public on PyPI and as a
GitHub Release from exact commit `33ea08a`; tag workflow 35619712980 and release-commit CI
35572245440 are green. Review 50 independently approved the final public result. S10 has now
conditionally admitted Mem0 2.0.20 only as a disposable `infer=False` projection; Review 52
approved the boundary with non-blocking notes. The rebuild-only production preview is runnable and
Review 53 approved it with non-blocking notes. The opt-in hybrid retrieval preview is now runnable
and Review 54 approved it with non-blocking notes and no blocking findings. The Obsidian vault
source is runnable; Review 55 blocked on three findings, all remediated test-first, and then
approved with non-blocking notes. Automatic promotion slices A–D are runnable. Slice D is
checkpointed at `6d936f3`; Review 57 initially blocked its direct-only structural proof, then
approved the transitive remediation with non-blocking notes. GitHub Deep is runnable at `f994446`;
Review 58 approved the final exact-actor, bounded authored-activity source with non-blocking notes.
Automatic Profile promotion is runnable under accepted ADR-0020; Review 59 approved its exact,
owner-pinned Memory→Fact lifecycle after all incremental/full-validation blockers were remediated.
The official Notion MCP source is runnable under accepted ADR-0021; Review 60 approved its exact
root, official hosted-MCP, Keychain-confined and fail-closed provider boundary.
Longitudinal dogfooding is runnable under accepted ADR-0022, with one real content-free authorized
Folder baseline. The separate Obsidian desktop owner interface is runnable under accepted ADR-0023;
Review 62 approved its bounded local bridge, canonical actions, no-content-cache client and
descriptor-pinned installer after all blocking findings were remediated test-first. The public
`aptuni.api.v1` SDK, strict manifest/grant platform and Top-Down Learning flagship are runnable under
accepted ADR-0024; Review 63 approved the final authorization lifecycle and compatibility contract.
The implementation checkpoint is `a1a04fb`; it is local and has not been pushed.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

The machine-readable Stable readiness gate is runnable (`tools/stable_gate.py`, Review 73 approve
with notes; notes in BACKLOG). Run it with `--evidence` bound to a clean candidate commit; reports go
to the git-ignored `artifacts/`.

Top-Down Learning is now Flagship Plugin #1 (ADR-0026 accepted, Review 74 approve with notes; the
BLOCK round is remediated). Its eight stateless MCP tools carry the learner-owned
`top_down_learning_context.md` through target → retrieval → at most three questions → verification →
local or cloud. The demo contexts are in `examples/plugins/top_down_learning/examples/`
(regenerate them with `tools/regenerate_top_down_demo.py`). Platform friction is in
`docs/research/findings/plugin-platform-friction.md`.

Checkpoints: Stable gate `7ae7211`, Flagship #1 `bf8e20c` (local, not pushed). A fresh isolated
uv-tool install ran the first-run journey through the installed server successfully.

**Aptuni 0.2.0b1 Beta is public** (maintainer-authorized): PyPI and a GitHub pre-release from
`f59241f`, with byte-identical hosted, PyPI, GitHub and local artifacts. The record is in
`docs/dev/releases/0.2.0b1.md`. The dogfooding protocol is `docs/dev/BETA_DOGFOODING.md`.

Next: the real host first-run journeys with the maintainer, then the dogfooding window. The earlier
integration steps below are done.

Previously next: Beta release integration. Run a genuine clean-environment install and first-run journey for
Aptuni 0.2.0b1 and plugin 0.2.0 on both hosts, write release notes, and publish only when release
policy authorizes it. Then start the User #1 dogfooding window. Do not retune the pedagogy before
real use.

All three real activation paths are verified, and the deferred Notion hardening is closed at
`6e05e8a` (Review 68): line-safe envelope parsing, declared native Keychain signatures, bounded
credential reads/writes and truthful `disconnect-notion`. The evaluation workflow is ready for
repeated owner use (Review 69): trials in Profile/Memory-only or `--evidence` mode, owner labels via
`score --useful … --rest-noise`, `discard` for test or mislabelled trials, and a report with unscored
trials and first-versus-latest usefulness for repeated queries. The live dataset was cleaned of
agent-labelled fixture trials. The next measurable signal needs the owner's own queries and labels;
do not retune KI-018 before real owner-labelled Profile/Memory trials show a persistent pattern.
Remaining Notion BACKLOG items wait for evidence of the live server's non-enveloped shapes.

Two Review 55 lessons carry forward to any provider work: write injection tests with **real**
control bytes — the literal text of an escape sequence asserts nothing and left a whole mutation
class undetected — and route every outside-controlled token through `sanitize_token` where it is
stored or `delimited_untrusted` where it is rendered. Do not mutate the 0.1.0 tag or artifacts; a
concrete public defect requires a patch release.

`docs/dev/plans/07-m1-exit-matrix.md` audits every remaining M1 exit clause and orders Slices 14–18.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

Beta Agent/plugin UX (Reviews 70–72). Aptuni is OFF by default; Profile, Memory and Full use
host-independent intents behind manual Claude/Codex skills; plugins declare required/optional
context through the existing public grant contract; and the installable Top-Down Learning flagship
uses that contract without a Core special case. Review 72's forged-progress, unsatisfied-install and
Unicode-continuation blockers were remediated test-first. Full gate: 830 passed, 3 skips and 62
subtests; Ruff, strict source/plugin mypy, relay, host validators and the fresh installed STDIO
journey are green. The Beta candidate version is `0.2.0b1`.

Notion hardening and owner-labelled evaluation (Reviews 68–69). Credential and envelope notes from
Reviews 65/67 are closed at `6e05e8a`; `evaluate discard`, `score --rest-noise` and the extended
report make repeated owner trials cheap and honest, and the stale activation deliverable was folded
into STATE and removed.

Real dogfooding fixes (Reviews 65–67; checkpoints `1ae1d8f`, `1d93ff8`, `327dbf4`, local and unpushed). The Notion activation delta is checkpointed at `1ae1d8f`
after Review 65 blocked a parser that treated absent completeness metadata as complete; unverified
completeness is now `partial`. Context with Evidence requested keeps retrieval rank across L3/L4 and
reports `layers` canonically; `aptuni evaluate trial --evidence` plus evaluation schema v3 separate
Profile/Memory-only and with-Evidence measurements. Regressions prove the old L3-first sort failed.

Public developer API and SDK plugin platform (ADR-0024, Review 63) adds immutable versioned DTOs,
least-privilege Profile/Memory/Context/Evidence reads, quarantined proposals, strict manifests,
owner-confirmed exact grants, full grant lifecycle CLI, scaffold and docs. Grants are tamper-checked,
path-confined, live-revalidated, privacy-managed, single-effect under concurrent/crash recovery and
never activate external code. The separate Top-Down Learning example dogfoods the complete adaptive
loop without a core special case. Full gate: 725 passed, 3 optional skips and 61 subtests; Ruff,
strict mypy, relay, source/artifact supply-chain checks, frozen evaluation and clean-wheel SDK smoke
are green. Final review verdict **APPROVE**.

Obsidian owner interface (ADR-0023, Review 62) adds `aptuni interface obsidian snapshot|evidence|
action|install` and a bundled three-file desktop plugin. One bounded Vault snapshot feeds Profile,
Memory, Evidence, Recent Changes and Pending Reviews with explicit truncation, provenance and
currently valid actions. Accept/Edit/Reject/Pin, Profile review, evidence display and two-phase
Forget reuse canonical services. The plugin invokes Aptuni with `execFile` argument arrays, enforces
exact contract `aptuni.obsidian@1`, renders text-only DOM content and caches no returned personal
data. Installation neither scans notes, grants ingestion nor enables the plugin; it pins and
revalidates every destination path component and the final target. Review 62's four first-pass and
two continuity follow-up blockers were remediated with deterministic regressions. Full gate: 704
passed, 3 optional skips and 61 subtests; Ruff, strict mypy, relay, JavaScript syntax,
notices/secrets/workflow and artifact supply-chain checks, frozen evaluation and packaged-asset
inspection are green. Final verdict **APPROVE**.

Longitudinal dogfooding (ADR-0022, Review 61) adds `aptuni evaluate setup|trial|score|capture|report|
reset`. It runs ordinary Context retrieval, prints context only for immediate owner judgment, and
persists query digests, canonical IDs, explicit useful/noise labels and content-free metrics only.
Lifecycle snapshots cover source updates, corrections/supersession, promotion/review burden and
permissions; purge/reset remove all derived state. Review 61's deletion-order, terminal-injection
and mixed-migration metric blockers were remediated test-first; final verdict **APPROVE**. A real
content-free baseline is established on the maintainer's authorized Folder setup; no query trial or
private content was stored.
Full gate: 692 passed, 3 optional-runtime skips and 61 subtests; Ruff, strict mypy, relay,
supply-chain checks and frozen lexical/hybrid evaluation are green.

Official Notion MCP source (ADR-0021, Review 60) adds `source add-notion`, `connect-notion` and
`disconnect-notion`. OAuth/PKCE secrets remain in macOS Keychain. The source stores exact approved
roots and calls only `notion-get-users(self)` plus `notion-fetch` for those roots; it never searches
or writes a workspace. Stable native IDs, validated bounded provenance and minimized excerpts enter
the common snapshot/delta Evidence path. Missing or unsafe results retain prior Evidence, while
ambiguous scope, malformed schema and completeness metadata fail closed. Full gate: 683 passed, 3
optional skips, 61 subtests; Ruff, strict mypy, relay, supply-chain and frozen evaluation green.
Review 60 final verdict: **APPROVE WITH NON-BLOCKING NOTES**. Aptuni's own Notion OAuth authorization
remains an explicit maintainer action before a real private-source sync.

Automatic Profile promotion (ADR-0020, Review 59) closes the canonical `Memory → stable Fact`
lifecycle without semantic guessing. Only a current owner-pinned Memory with exact owner-declared
CLI support, both module permissions, no unresolved contradiction and no historical promoted Fact
qualifies. Pinning writes one policy event and one exact lineage-linked Fact atomically;
`aptuni profile refresh` handles older pins, and `aptuni profile review list|accept|reject` provides
retrospective review. Rejection preserves history and can never silently recreate the claim.
Context marks pending promoted Facts. Incremental canonical validation binds the copied claim and
one transition event, including correction and duplicate-event cases. Full gate: 642 passed, 3
optional skips, 47 subtests; Ruff, strict mypy, relay, supply-chain and frozen evaluation green.
Review 59 final verdict: **APPROVE WITH NON-BLOCKING NOTES**.

GitHub Deep (`f994446`) is an additive `github_deep` source created with `aptuni source add-github
... --deep-actor LOGIN`. It keeps GitHub Standard unchanged and records minimized Evidence only for
exact linked-login authored commits, opened pull requests and submitted reviews inside the approved
repository. ADR-0019 and `github.activity@1` bind the public contract. Deep never reads or retains
blobs, diffs, bodies, comments, emails, issue/discussion threads, file lifecycle or cross-repository
activity. Commits/PR search stop at five 100-item pages; reviews stop at 100 candidate PRs, two pages
per PR, 100 requests and 500 admitted items; every response is capped at 2,000,000 bytes. Exhausted
or changing search bounds make the whole snapshot partial, while malformed identity, rate limits
and overruns fail without durable change. Review 58 first blocked three contract/test gaps; exact
positive repository IDs are now enforced at API, scan and locator intake, the undeclared field was
removed, and below/at-cap regressions prove prior Evidence cannot be withdrawn. Full gate: 627
passed, 3 optional skips, 47 subtests; Ruff, strict mypy, relay, supply-chain and frozen evaluation
green. Final verdict: **APPROVE WITH NON-BLOCKING NOTES**.

Automatic promotion Slice D (`6d936f3`) adds the read-only `aptuni_get_memory_review` MCP tool.
The exact `memory.review.read` scope is disclosed in new adapter plans; old grants fail closed.
The bounded feed filters pending memories through current exposure and granted modules, derives the
reminder over that filtered set, enforces host/model egress, and discards a response after a
concurrent canonical change. The ADR-0013 item 1 regression keeps a direct MCP handler allowlist
and traverses the read-service call graph across all application mixins, rejecting promotion,
owner-decision and commit sinks. Review 57's initial BLOCK found the first direct-only proof was not
transitive; the remediation passed 61 focused tests and the final review is **APPROVE WITH
NON-BLOCKING NOTES**. Full gate: 600 passed, 3 optional skips, 47 subtests; Ruff, strict mypy,
relay, supply-chain checks and frozen evaluation are green.

Automatic promotion (ADR-0018, slices A–C, `123ebdd`). An observation the owner makes through the CLI becomes
an active memory in the same commit rather than waiting in a queue; it is marked
`auto_promoted_pending_review`, derived from the ledger rather than stored, and reviewed afterwards
with `aptuni memory review list|accept|edit|reject|pin`. Host proposals, sensitive modules and
anything contradicting a record still standing keep the ADR-0013 confirmation. Reminders appear in
`status`, `doctor` and `aptuni memory review reminders`, never as a prompt.

Slice A landed first on its own and was deliberately behaviour-preserving: "revoked" had meant
"any review event targeting a memory", which was only ever correct because a revocation was the
one event that could target one. `accept` and `pin` break that, and the new test shows an `accept`
event removing a memory from `memories()`, the Mem0 rebuild and the hybrid lane while `exposable()`
and export kept it.

Review 56 BLOCKed on six findings, all remediated test-first: a superseded memory left in the
Profile export, non-idempotent decisions once a memory was pinned, a reminder marker that could
crash the command or silence reminders forever, the reminder missing from `status`/`doctor`, no
`review_state` in the Context API, and `edit` ignoring `ingest_enabled`. The two highest-risk
claims held under direct attack: nothing can be promoted that the ADR says must be confirmed, and
MCP cannot promote. Full gate: 598 passed, 3 optional skips, 47 subtests.

The Obsidian vault source (`342de4e`) adds `aptuni source add-obsidian` and runs through the ordinary sync
pipeline. Only a directory holding a real `.obsidian/` counts as a vault; `.obsidian/`, `.trash/`
and every attachment are excluded before any read. Identity is the vault-relative path reconciled
by the existing `reconcile_keyed`, so a rename stays a `move`. `obsidian.locator@1` carries bounded
topology — note name, folder, wikilink targets, tags, aliases, frontmatter property *names* — while
property *values* are dropped and the excerpt is taken after the frontmatter block is removed. The
frontmatter grammar is a clean-room subset with no YAML dependency. A vault that stops being a
vault mid-scan fails closed. ADR-0017 is accepted; `source.obsidian` is now `builtin`.

Review 55 BLOCKed on three findings, all remediated test-first with mutation-verified regressions:
a UTF-8 BOM (and a `...` line) defeated frontmatter minimization and put property values into the
indexed excerpt — live on the maintainer's own vault, 64 BOM notes holding 101 property values; the
injection tests were vacuous while `note_name`, `folder_path` and the CLI evidence row were
unsanitized, so a crafted filename forged an evidence row with a live ANSI escape; and the plugin
manifest denied reading note bodies while storing an indexed 280-character body excerpt. Fixing the
second hardened the `aptuni evidence` row for the Folder and GitHub providers too, which is a
user-visible rendering change recorded under `### Changed` in the CHANGELOG. Full gate: 542 passed,
3 optional skips, 47 subtests. Review 55 is **APPROVE WITH NON-BLOCKING NOTES**.

The opt-in hybrid retrieval preview (`37f21fe`) adds `aptuni search --hybrid`. It fuses SQLite/FTS ranks with
semantic ranks from the selected Mem0 generation by deterministic reciprocal-rank fusion; provider
scores are diagnostic only and cannot reorder anything. The semantic lane returns canonical Memory
IDs only, is filtered to accepted non-revoked memories in permitted modules, and is hydrated solely
from the final stable canonical snapshot after a repeated exposure check. Absent, stale, invalid or
cleanup-required provider state raises a bounded remediation error rather than falling back
silently. Default search, the Context API and MCP are untouched. `tools/run_evals.py` is at
evaluator version 2 with an additive checksum-bound fusion fixture; the frozen S03 corpus and its
thresholds/holdout are unchanged. ADR-0004 and ADR-0003 carry 2026-09-22 amendments;
`retrieval.hybrid` is now `preview`. Two honest preview limits are documented: the semantic lane has
no relevance floor (KI-021) and `score` is comparable only within one invocation. Full gate: 501
passed, 3 optional skips, 47 subtests; the isolated hash-locked runtime passes 55, including a real
Mem0 2.0.20 rebuild-then-search. Review 54 is **APPROVE WITH NON-BLOCKING NOTES**.

The Mem0 projection preview (`e2a06e5`) adds `aptuni memory provider status|rebuild|delete`. It projects only
current accepted canonical memories, always uses `infer=False`, validates exact public enumeration,
and publishes fresh generations atomically. The optional runtime is exactly Mem0 2.0.20 plus Ollama
0.6.2; only numeric loopback is accepted, redirects/proxies are disabled, and models are never
pulled. Privacy purge removes the whole root and shares a lock with rebuild. Full gate: 479 passed,
3 optional skips and 47 subtests; the isolated runtime passes all 23 focused tests. Review 53 is
**APPROVE WITH NON-BLOCKING NOTES**.

S10 (`84a3a8e`) isolated Mem0 2.0.20 with a hash-locked runtime and a bounded synthetic fixture. Exact restart
and fresh-root rebuild passed with `infer=False`, guarded execution observed no non-loopback network
attempts, and canonical fixture bytes stayed unchanged. The adverse paths are now binding product
constraints: inference retained raw messages, and record deletion retained marker bytes in
Qdrant/history, so the adapter must reject inference and use whole-store rebuild deletion. The
focused suite passes 15/15; full repository pytest (459 tests plus 47 subtests), Ruff and strict
mypy are clean. Review 52 is **APPROVE WITH NON-BLOCKING NOTES**.

Slice 17's daily-task and focused matrices pass on Claude Code 2.1.267/2.1.266 and Codex
0.155.0/0.154.0. Exact resolved versions and the external built-wheel runtime are enforced. Claude
did not emit focused file-tool calls, so no denial is claimed; both Apple Event attempts produced no
outer effect and status remains `unverified`. Full local gate: 459 tests plus 47 subtests, ruff,
strict mypy, relay and 34 developer checks clean. Review 48 is **APPROVE**.

The pushed checkpoint passed hosted macOS, Ubuntu (including ext4 durability) and build/supply-chain
jobs. A 2026-09-21 read-only audit found no `aptuni` package on PyPI or npm, found only
`ruihaomei/aptuni` as an exact-name GitHub repository, and confirmed private vulnerability reporting
is enabled. No registry or repository setting was changed.

The exact 0.1.0 release commit is `33ea08a54a0a26a1dcfa74c419121afebe31f4c0`, tagged `v0.1.0`.
The OIDC release workflow passed and published byte-identical artifacts to PyPI; the GitHub Release
adds the same wheel/sdist and `SHA256SUMS`. A fresh PyPI-only Python 3.13 install passed CLI,
synthetic Vault/context/setup and MCP safety smokes. Legal files, public links, package metadata,
secret/private-data scans and the zero-finding hosted vulnerability audit passed. Review 50 is
**APPROVE**. See `docs/dev/releases/0.1.0.md` for exact URLs, run IDs and hashes.

## Known constraints

- The maintainer authorized the final 0.1.0 release-record checkpoint and push. Future publication
  or tag changes require fresh authorization. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.

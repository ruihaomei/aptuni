# Real authorized selection — bounded coverage decision

2026-10-07. Research-only, local. **Decision: keep one strong Agent; do not promote the tested bounded roster policy or release b10.** One extra strict success in a two-task real mini-holdout is useful evidence of possible benefit, but correct-pair selection did not improve, a product-critical failure remains, and the bounded path cost more model work and time. No production, grant, activation, storage, index, credential, backup, or public-tool change was made. The content-free accounting is in `real-selection-metrics.json`.

## Validity and audit

An authorized explicit-Full audit at canonical sequence 66 found adequate Evidence for multiple documented project candidates on two realistic selection goals. A third proposed application goal requiring verified personal role and outcome was ambiguous and excluded. The accepted pools and alternative pairs were frozen privately before Agent tasks. The audit established **minimum** candidate support, not exhaustive corpus truth; repository artifacts do not establish individual contribution or measured outcomes.

The first frozen comparison ended before grading: s01 A completed, but s01 B never received its task because an unqualified research-policy instruction conflicted with explicit Full setup. The runner preserved the pre-task abort. A regression failed before the narrow policy/runner repair and passed afterward; a setup-only preflight observed Full; Review 112 approved the repair. The completed s01 A remains diagnostic and is **not** paired with a repaired B result. A second freeze used the never-run s02 goal and new s03 goal, with new task/rubric/policy/runner hashes. All four v2 sessions ran once, completed, observed explicit Full and sequence 66, and matched their frozen manifests. No result was inspected or retuned between sessions.

The lead locked an answer-only assessment before inspecting actual returned Evidence, then locked support judgments before mapping arms and costs. There was no independent second grader. The current grant and model egress were unchanged. A requested both `projects` and `knowledge` on its ordinary calls; B's research surface requested `knowledge` only. Every substantive returned item in both arms was in `knowledge`, but the requested-module difference limits exact policy parity. These two tasks are mechanism evidence, not a population reliability estimate.

After grading, 163 phase-derived private raw files (3,735,844 bytes) were removed from owner-only scratch. The exact frozen local inputs remain private for audit; the non-sensitive hashes and cleanup count are in `real-selection-cleanup.json`. Existing grants and both owner backups were untouched.

## Frozen fresh outcome

`Audited recall` counts a candidate only when its Evidence was returned, not when its label appeared in the roster. The denominator is the three independently audited minimum candidates per task. A relevant candidate outside that minimum pool can still satisfy the task when the frozen rubric permits it.

| Task | Arm | Audited candidates in Evidence | Accepted pair | Returned IDs attached | Comparison complete | Strict E2E | Main failure |
|---|---|---:|---|---|---|---|---|
| s02 | A ordinary | 1/3 | No* | No | Yes | No | R3; frozen pair limitation |
| s02 | B bounded | 2/3 | Yes | Yes | Yes | Yes | — |
| s03 | A ordinary | 0/3 | Yes, allowed alternative | No | Yes | No | R3 |
| s03 | B bounded | 0/3 | No | Yes | Yes | No | R2; thin project identity support |

\* The s02 A answer chose a plausibly relevant project outside the predeclared accepted pool. Its strict pair score remains failed, but that score is **not** evidence the alternative is irrelevant. It also omitted returned canonical Evidence IDs, so the strict answer fails regardless. In s03, A selected two distinct, source-supported alternatives allowed by the frozen rubric; B selected a single runner artifact as though it were a second project even though another project candidate was in its returned packet. The failure classifications are stage diagnostics, not claims about all unseen corpus candidates.

| Measure across two tasks | A ordinary | B bounded |
|---|---:|---:|
| Strict E2E | 0/2 | 1/2 |
| Accepted pair under frozen rubric | 1/2 | 1/2 |
| Audited minimum candidate Evidence recall | 1/6 | 2/6 |
| Answers with returned canonical IDs attached | 0/2 | 2/2 |
| Requested comparisons completed | 2/2 | 2/2 |
| Explicit Full / snapshot correctness | 2/2 | 2/2 |
| Retrieval calls / refused calls | 4 / 0 | 4 / 0 |
| Retrieval response units | 13,859 | 6,649 |
| Task tokens, input plus output | 165,539 | 185,662 |
| Setup plus task journey | 224.693 s | 342.178 s |

B used **20,123 more task tokens (+12%)** and **117.485 s more journey time (+52%)**, with the same four retrieval calls and no retries. It returned fewer context units, but that saving did not translate into lower model-token or latency cost. Both arms also made one task-time activation-status call and two setup control/status calls per task. These are processed-token counts, not billing estimates.

Candidate precision is not reported as a numeric rate: the pre-task audit froze a minimum supported pool, while actual responses included relevant alternative projects and mixed source facts/artifacts. Treating every unlisted project as irrelevant would create a false precision denominator. B's roster did list all 11 eligible GitHub source groups in both tasks, including the audited groups, without truncation. Its Evidence-stage audited recall was still only 2/6 because the Agent chose at most three anchors; the roster alone did not ensure candidate coverage.

## Failure decomposition and decision

- **R0 corpus inadequacy:** zero among the two strict tasks. The third proposed role/outcome task was excluded as ambiguous before execution.
- **R1 candidate coverage:** no primary strict failure can be attributed solely to unavailable evidence. Audited-pool Evidence recall remained low, but each task returned at least two plausible project groups, including alternatives. The roster-to-Evidence choice was partial.
- **R2 selection:** one primary B failure selected an artifact rather than a distinct supported project. The s02 A frozen pair score is limited by an unlisted plausible alternative.
- **R3 evidence support:** both A answers lacked returned canonical Evidence IDs. B attached actual returned IDs in both answers, although IDs for a runner do not establish it as a prior project.
- **R4 completion:** zero. All four answers completed the requested comparison and recommendation. The synthetic R4 signal did not recur here; a completion checker is not justified by this phase.

The real authorized corpus had enough support for **2/2 valid strict tasks**, and the bounded path improved strict E2E from **0/2 to 1/2** without improving frozen correct-pair count (**1/2 each**). The extra success does not justify a production selection policy while B still fails to choose two distinct projects on another task and costs more. The dominant remaining issue is **selecting and substantiating two project-level candidates**, rather than omission of comparison dimensions. The synthetic automatic-coverage result did not transfer reliably: an 11-group roster exposed the possible groups, but the Agent's limited anchor choice could still favor a weak artifact, and ordinary answers could still omit Evidence IDs.

No storage or index migration was needed for this shallow GitHub grouping experiment. No new Agent or runtime role is justified. `/aptuni retrieve` remains documented but research-only; it was not run or productized here. b10 remains unreleased. The **single release blocker** is reliable, evidence-attached selection of two supported real-context candidates with a complete answer on fresh tasks. Further work should target that demonstrated selection/evidence boundary within the existing strong-single architecture, with a separately frozen validation set; this mini-holdout cannot be tuned and reused as fresh proof.

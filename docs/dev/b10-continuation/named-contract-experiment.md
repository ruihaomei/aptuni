# Separately frozen named-anchor development experiment

2026-10-04. Research only; no production discovery endpoint or policy change.

The original compact catalog contract is rejected. Both strong-host catalog runs
selected the relevant display label but passed its Evidence reference as the
repository lookup anchor, obtaining no evidence. Preserve all four original
outcomes, the unchanged public fixture and the implementation at `2ed671e`.
The fixture's stop rule halts that original implementation; it does not establish
that more agents or a larger catalog would solve the task.

Hypothesis: the two unlabeled identifiers create an avoidable tool-argument gap.
One offline Astra xhigh diagnostic used the same five labels and a preselected
candidate, with named `anchor`, `label`, `evidence_ref` fields plus an explicit
instruction distinguishing the lookup anchor from a citation. It emitted the
correct lookup arguments without any observed tool call: 9.506 seconds, 15,270
uncached input tokens and 123 output tokens (including 71 reasoning tokens).
Packing the complete named catalog uses 770 existing response units, below 800,
without truncation. Independent audit confirmed these observations. The treatment
combines formatting and instruction; neither causal contribution is isolated.
It establishes one understandable response, not E2E recovery or reliability.

Decision before candidate inference: test this separately versioned contract in
the synthetic-only `catalog_named` arm. Keep the original task, worlds, five
labels, granted knowledge module, explicit Full setup and two-call/4,000-unit
total. Use the same model/host/effort as the first comparison. Preserve 800 units
for catalog and 3,200 for evidence. Freeze server, fixture, policy, bundle and
dataset hashes. The only new policy sentence instructs the host to copy `anchor`
for lookup and retain `evidence_ref` as a citation.

The two strong-model runs are development controls reusing known synthetic worlds,
not independent acceptance evidence. Require actual successful lookup in both:
the positive answer must give a supported project description with bounded
synthetic results; the negative must read the study-only evidence and distinguish
third-party study from personal contribution. Empty-result abstention does not
pass the latter treatment check. Keep the fixed original answer rubric otherwise.
Record all attempts, units, tokens and latency, including failures.

Only if both pass, run two matched cheaper-host transfer sessions. Any revised-arm
failure stops this variant; do not silently tune it again or enlarge the budget.
The six-task holdout remains sealed. Production remains stopped until separate
real-corpus feasibility, permission review and a frozen finalist evaluation.

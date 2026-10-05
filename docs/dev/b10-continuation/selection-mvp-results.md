# B10 selection MVP: bounded candidate coverage and Agent-directed retrieval

2026-10-05. Research-only. Frozen inputs and procedure: [protocol](selection-mvp-protocol.md),
checkpoint `8820880`. Six ordinary-task native sessions completed once, with no
operational stop or interim grading. The source snapshot is an **invented,
eight-group corpus**, not the owner Vault. [Content-free metrics](selection-mvp-metrics.json)
bind the six records and measured resources. The previous live selection mini
and original frozen seven retain their separate denominators.

## 1. Where the existing selection path fails

The prior focused s01 required two documented selection references. A returned
two items, then ten more with truncation; F returned five compact labels, then
five Evidence items from **one** selected anchor. Both final answers lacked
two concrete supported flows and failed the goal. All four prior source-support
judgments passed, so unsupported attribution is not the observed reason for
that failure. The old raw answer and source packets were cleaned after grading.

| Stage | What the retained record establishes |
|---|---|
| Relevant supported candidates in the authorized corpus | Unknown; no exhaustive relevance labels or corpus oracle. |
| Retrieved candidates | A: 2 then 10 items; F: five labels followed by one anchor's Evidence. Neither packet established two required flows. |
| Agent-considered candidates | Exact identities no longer retained. F could consider at most the one hydrated group as Evidence. |
| Selected candidates | Neither final answer delivered two supported selections; exact old shortlist is unavailable. |
| Evidence attached | Consequential claims that were made passed support grading; packet support for the required pair was insufficient. |
| Final comparison | Both failed the original two-reference task, despite safe and honest limitations. |

The dominant **observed** failure is inadequate task support in the candidate
set returned before final comparison. The record cannot distinguish poor
corpus recall, an incomplete source corpus, and wrong ranking among unseen
candidates. It does not demonstrate that more reasoning would rescue the old
packets. This case was diagnostic only and was not rerun or counted as fresh
success.

## 2. Fixed hypothesis and mini-holdout

Hypothesis: selection tasks benefit from a bounded source-group roster before
ranking. The smallest intervention was a logical eight-entry candidate index
from already present source grouping metadata, followed by an Evidence fetch
of up to three previously listed IDs. No physical storage change, embedding,
ontology, extra model role or production guidance was added.

Two fresh, ordinary goals were frozen before model execution: select two past
projects for an offline privacy-first design memo; select two completed
experiences for a reproducible data engineering application. The same invented
source snapshot and goal-derived rubrics were fixed for baseline search,
automatic roster-then-fetch, and explicitly delegated retrieval planning. All
arms used GPT-6 Astra xhigh, explicit empty Full setup, knowledge-only fixture
scope, a 4000-unit cap and three permitted task calls. The directed arm could
choose search, roster query and ID fetch; it could not change authorization.

The author of this report also wrote the fixture/rubric and graded the six
answers after all runs. The grading is therefore not independent or blinded.
This is a controlled mechanism test with known corpus truth, not a measured
real-user reliability rate. The mock models OFF, module/exposure and unit/call
bounds; it does **not** implement the real grant, egress, credential scanner,
policy epoch or host confinement boundary.

## 3. Frozen results

Strict E2E applies every required deliverable in the frozen rubric. The
automatic s02 answer selected the correct two and wrote a useful paragraph,
but omitted the required reason coursework was weaker, so it is a **failure**.
The directed s02 answer selected only one completed experience. Safe
abstention does not complete a required two-experience task.

| Arm | Strict E2E | Gold groups returned as Evidence | Correct selected pair | Supported claims | Calls / refused / retries | Task tokens | Full journey |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline search | 0/2 | 1/4 | 0/2 | 2/2 | 4 / 0 / 2 | 139,485 | 154.100 s |
| Automatic bounded roster | **1/2** | **4/4** | **2/2** | 2/2 | 6 / 0 / 0 | 183,197 | 157.790 s |
| Agent-directed | 1/2 | 3/4 | 1/2 | 2/2 | 7 / 2 / 1 | 201,955 | 185.387 s |

All six answers used only returned Evidence IDs when they cited personal
history. No hidden group appeared in any roster or answer. Neither task
returned a claim that a third-party reading note or future plan was completed
owner work. No case incurred an operational host failure. A refused tool call
still counts as a retrieval attempt.

**s01 candidate chain.** Baseline search returned Evidence for one gold group
and selected only that one, then failed the two-project goal. Both roster arms
listed both gold groups, fetched their Evidence, selected the correct pair and
gave the required comparison and design decisions. The directed path's
query-filtered roster excluded one irrelevant alternative, without improving
the goal over automatic coverage.

**s02 candidate chain.** Baseline made two 32-unit searches and got no Evidence.
Automatic coverage listed both gold groups, fetched both, and selected both;
its final comparison omitted coursework. Directed coverage narrowed eight
source groups to three label matches, excluding the second gold group. It
fetched one gold group plus a plan, then attempted a search with nine concepts
(the schema allows eight); the correction hit the three-call cap. It produced
an honest one-experience answer and failed. This shows a query-planning and
candidate-filtering loss under this deliberately simple label filter, followed
by a call-sequence failure. It is not evidence that a capable user-owned Agent
is generally worse.

The automatic path gained **one strict pass in two tasks** over baseline in
this invented corpus. Candidate Evidence recall rose from 1/4 to 4/4, and
correct-pair selection from 0/2 to 2/2. This does not establish a live-Vault
improvement: the fixture labels were short and descriptive; the baseline
Agent's own 32-unit s02 requests also contribute to its failure. The directed
path gave **zero additional E2E passes** over automatic coverage and one
fewer correct pair. It used 18,758 more task tokens, one more attempted call,
and 27.597 more measured journey seconds across the two tasks. Its lower
returned units (5,341 versus 7,442) reflect missing/failed retrieval, not
efficiency. Automatic coverage itself used 43,712 more task tokens, two more
calls, 6,121 more units and 3.690 more journey seconds than the low-context
baseline. Task token counts include cached input; these tiny sequential runs
do not establish billing or latency effects in general.

## 4. Agent navigation and minimum interface

The successful paths navigated only **knowledge → source group → Evidence
record**. Source-group identity, a short label, canonical Evidence IDs and
bounded fetch were useful. No Agent used a deep hierarchy, confidence score,
graph traversal or new ontology. The directed Agent attempted ordinary scoped
search only after its roster choice failed; that search did not return data.
The observed sufficient primitive set for the successful synthetic case is:

1. list a bounded set of permitted source-group IDs with short labels;
2. fetch Evidence for up to a few listed IDs, returning canonical citations.

Existing context search can remain as a separate fallback. This study does
not prove that list+get is globally minimal or that a third primitive is never
needed. The roster is a **logical index**, derived from existing repository
locator/source metadata and rechecked against exposure. It requires no
physical Vault restructuring for the tested GitHub-like groups. Cross-source
projects, applications, interactions and richer topology remain untested.

## 5. Privacy and product decision

An external Agent may choose queries and retrieval order only inside an
already authorized Full session. A future interface must use the real
HostContextAccess grant on each call, apply module and exposure checks before
listing and after hydration, run the credential guard on labels and text,
recheck canonical sequence/policy, cap labels/IDs/units/calls, and return
provenance. A roster itself discloses sensitive *existence and labels*; it must
not become a whole-Vault inventory. The mock's privacy tests support its
research boundary only, not production approval. Slash-command syntax is not
settled.

**Decision:** keep the strong single Agent and invisible automatic experience
as the production candidate. Keep bounded candidate coverage as a promising
**research-only** automatic-path intervention. Do **not** productize an
explicit `/aptuni retrieve`-style path yet: it supplied no paired E2E gain,
cost more, and failed to navigate one task. A future advanced optional path
would be reasonable only after an authorized, independently graded real-data
comparison demonstrates an additional complete task without privacy regression.
It should never be normal-path machinery merely because the primitives exist.

**b10 remains unreleased.** The single remaining quality blocker is reliable,
supported multi-candidate selection **and complete final comparison on fresh
real personal-context tasks**. The previous live A/F mini was 1/2 each, and
the automatic path here was only 1/2 on invented records. The next justified
work is a bounded, authorized real-data candidate-coverage audit and a fresh
independent selection check if its corpus support is established. Another
runtime architecture or multi-Agent experiment is not justified by these
results. Production code, guidance, grants, backups and activation stay as
they were.

**Verdict:** **Automatic bounded coverage is a research candidate; Agent-directed retrieval remains research-only; b10 release stays closed.**

# R1 stage follow-up: candidate-class metadata and packet depth

2026-10-08, after [`r1-localization-results.md`](r1-localization-results.md). Offline,
zero model calls, no production change. **Product decision: keep b10 frozen.** Content-free
numbers are in [`r1-stage-followup-metrics.json`](r1-stage-followup-metrics.json).

## Why a follow-up

The localization rejected one guidance fix (R1b) and found cutoff widening weak (R1c). Under
the stop rule, the next step was to return to the stage trace and test the next stage before
concluding. Two stages had not been measured: whether candidates are *represented by usable
class metadata*, and whether the *packet budget* rather than ranking is the binding cut.

The recorded fresh call arguments were deleted with the raw traces, so this follow-up does not
replay Agent calls. It uses an oracle-free mechanical proxy: each frozen v01–v06 task wording as
a plain query through the production projection, diversification and unit estimator. v01–v06
are burned as held-out evidence and serve here only as development cases.

## Finding 1 — the candidate class has no usable metadata

| Census (sequence 66, exposable) | Records |
|---|---:|
| All exposable records | 49,734 |
| Module `knowledge` | 49,728 (99.99%) |
| — MarginNote 4 study notes | 49,095 (98.7%) |
| — GitHub (11 repositories with records) | 507 |
| — Folder (125 files) | 125 |
| Modules `projects`, `skills` (both granted to Codex) | 0 |
| Module `experience` | 0, not granted |

All 17 source configurations map to `knowledge` only; GitHub's ADR-0029 `knowledge.applied`
authority depends on that mapping. Every one of the 64 audited pool Evidence records is in
`knowledge`. The tool contract and guidance invite the Agent to "choose relevant granted
modules", but no module separates a project or an experience from a study card. This is why
unnamed selection must guess words inside the candidates (R1b) and why broad words lose them
to an 85:1 study-note majority (R1c).

**Test (H-class).** Restricting the same query to the candidate class (GitHub + folder sources
for project/experience tasks, study notes for the subject task):

| Records returned | Full corpus: pool entities / tasks with a pool pair | Class-scoped |
|---:|---:|---:|
| 7 (today's ~4,000-unit packet) | 5/21 · 1/6 | 6/21 · 1/6 |
| 12 | 8/21 · 2/6 | 8/21 · 2/6 |
| 20 | 10/21 · 2/6 | 11/21 · 3/6 |
| 30 | 11/21 · 3/6 | 12/21 · 4/6 |
| 40 | 13/21 · 4/6 | 13/21 · 4/6 |

At the observed packet size class scoping changes nothing (5 vs 6 entities, 1/6 pairs each).
**Rejected as a standalone lever.** Populating `projects`/`experience` would also need a
canonical re-mapping of sources, an ADR-0029 authority change and, for `experience`, a grant
expansion. Each of these is an owner decision. The measured benefit does not justify them.

## Finding 2 — the packet, not the ranker, is the first cut, but depth has a ceiling

Response units are UTF-8 bytes. Candidate Evidence has a median of 555 units (p90 870), so a
4,000-unit packet holds 6–9 records. With the mechanical query, pool entities sit at
diversified ranks 0–46 on five of six tasks. Most fall below the packet cut rather than
missing the ranking.

**Test (H-depth).** Recall rises monotonically and slowly with depth: 5 → 8 → 10 → 11 → 13 of
21 entities at 7/12/20/30/40 records. At 40 records (≈17,600 units, ≈5× today, still a few
thousand tokens per session) at most **4/6** tasks contain a pool pair. One extracurricular
task is never reached lexically at any depth. That ceiling applies before any selection (R2)
or grounding (R3) loss. A live realization therefore cannot meet the release bar of no repeated
R1, so no live session was spent on it. Earlier offline replays of real Agent concept calls
showed the same ceiling (17/42 at twice the budget).

**Inventory (H-inventory), not retested.** The 2026-10-07 real B roster already listed all 11
repositories untruncated. Evidence-stage recall stayed 2/6 and correct pairs did not improve,
because the Agent cannot judge eligibility from labels. Exposing names alone does not close
R1.

## Answer to the R1 question

The second eligible candidate is lost at three stages in sequence. No lightweight lever covers
all three:

1. **Class metadata (new, R1a-adjacent):** the candidate kind is not represented, so retrieval
   cannot target "my projects/experiences".
2. **Concept coverage (R1b):** without a class, the Agent must guess words inside the records.
   Quality and artifact words each reach about a quarter to a third of entities.
3. **Packet depth (R1c):** whatever does match competes for 6–9 slots.

Five single-stage levers have now been measured. Guidance (live, fresh), cutoff/diversity
(offline), class scoping (offline), depth (offline) and a complete roster (live, real) each
fail or saturate below the bar. The remaining gap is a vocabulary gap: eligible items whose
records share no guessable word with the request. This matches the earlier stop-rule outcome.
The blocker cannot be solved in the current lexical single-Agent design without a materially
different capability.

## Owner options (superseded the same day by the owner's research order)

The owner then locked the order: Candidate Inventory MVP first, semantic recall only if it
fails materially, limitation only after both. The options below are kept as recorded.

- **Accept** unnamed-candidate selection as a documented b10 limitation. Named-candidate and
  ordinary context use already pass (fresh six 6/6), so this is a product-scope choice.
- **Class-scoped semantic recall:** the class is small (≈632 project/experience records), so
  a dense lane over it alone would be cheap to build and evaluate. It needs a dependency ADR
  and, first, your permission to download a small local model for an offline recall test like
  the one above (2026-10-01 notes: ~0.1–0.24 GB, CPU only).
- **Derived per-candidate summaries** that let the Agent judge eligibility before fetching
  Evidence. This is a new derived projection that needs privacy review and an ADR. The B
  result shows that labels alone are insufficient.

`/aptuni retrieve` stays research-only: nothing here suggests external planning closes a
vocabulary gap.

## Boundary and cleanup

No grant, activation, credential, backup, Vault, index, schema, ranking, tool, bundle or VPN
change. Scripts (`module_census.py`, `group_census.py`, `cost_census.py`, `scope_sim.py`,
`depth_sim.py`, `pair_sim.py`) print counts only and stay with the earlier research scripts in
owner-only scratch. They wrote no private text.

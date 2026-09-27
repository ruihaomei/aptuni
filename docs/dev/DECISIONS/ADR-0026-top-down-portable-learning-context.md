# ADR-0026: Make the portable verified learning context the Top-Down Learning continuity layer

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** maintainer (Flagship Plugin #1 brief) · implementing agent · independent reviewer
- **Builds on:** ADR-0024 (public API), ADR-0025 (activation boundary)
- **Needs maintainer confirmation:** no — the maintainer brief specifies the product contract

## Context

Top-Down Learning is Aptuni Flagship Plugin #1 and ships with the Beta. The first version held
progress in a per-process HMAC continuation over a fixed parking-system catalogue. That proved the
grant boundary but cannot survive a restart, cannot move between a local Agent and a cloud Agent,
and hard-codes both the prerequisite map and the pedagogy. The brief requires a human- and
Agent-readable, user-verified, portable learning context that works without Aptuni installed, and
teaching strategy that the teaching Agent generates rather than the plugin fixing in advance.

## Decision drivers

- Learning continuity must belong to the learner, not to one host or one process.
- Aptuni Core stays a general personal context platform; no learning special cases in Core.
- Minimized context: labels, levels and learning-relevant preferences only, never raw Profile or
  Memory, canonical identifiers, provenance, paths or secrets.
- A false inferred prerequisite corrupts the whole path, so learner confirmation gates teaching.

## Options considered

### Option A — keep server-held continuation state
**+** Tamper-evident per process. **−** Lost on restart; not portable; no cloud path.

### Option B — plugin-owned local database
**+** Durable. **−** A second store of personal data; invisible to cloud Agents; violates
minimization.

### Option C — a versioned Markdown artifact owned by the learner (chosen)
**+** Portable, reviewable, diffable, usable by any Agent. **−** A capable local Agent can edit it,
so verification is workflow integrity, not authentication.

## Decision

We choose **Option C**. The plugin package defines the public schema
`aptuni.top-down-learning.context@1`, rendered as `top_down_learning_context.md`:

- JSON-literal frontmatter: `schema`, `target`, `created_at`, `updated_at`, `user_verified`,
  `verified_digest`, `preferred_delivery` (`local | cloud | undecided`).
- A fixed, ordered set of sections from the brief (Learning Target through Last User Verification,
  plus Cloud Teaching Guidance). Unknown, missing or reordered sections, oversized input and
  malformed bullets fail with `top_down_context_invalid: <reason>`.
- **Stable state** = target, success criteria, depth/deliverable, foundation levels, learning
  preferences and constraints. `verified_digest` is the SHA-256 of their canonical form. Any stable
  change clears verification. **Dynamic state** = diagnostics, prerequisite map, path, delivery
  mode, strategy, position, demonstrations, misconceptions, gaps and next step; updating it keeps
  verification. Dynamic progress never becomes Profile.
- Aptuni retrieval is task scoped: one bounded `query_context` per evidence term (at most three per
  prerequisite, twelve prerequisites) over `knowledge`/`skills`, and eight single-token queries over
  `preferences`. Only concept labels, an inferred level (≥2 negation-free supporting records →
  strong, 1 → familiar, 0 → unknown) and preference lines that explicitly mention learning or
  teaching (whole-word match) are written. Aptuni inference is labelled as such until the learner
  verifies or corrects it; learner statements override inference.
- Every rendered file must parse back to the identical model; values that could not (separators,
  the empty-section marker, untrimmed or control text) are rejected or neutralized on input.
- Teaching-dependent tools require a verified context whose digest matches. Verification needs the
  exact digest returned with the summary the learner saw and an affirmative confirmation without
  correction cues. As in ADR-0025, the model-mediated host cannot prove a human produced that text;
  the gate prevents skipped, stale or hand-flipped verification, not a determined local Agent.
- Advancement requires a learner output and an Agent diagnosis (`understood | partial |
  misconception | unknown`); only `understood` advances or returns from a just-in-time prerequisite.
  The position stack holds at most five entries including the target, so at most three nested
  just-in-time descents below a path concept; position concepts must be unique and in the map.
- Cloud export is a pure transformation of a verified context. It calls no Aptuni API, cannot
  broaden a grant, redacts path-, email-, credential- and token-shaped free text, and refuses when
  such text remains anywhere else in the document body.
- Memory proposals are explicit only (`memory.propose` stays optional, quarantined and
  fail-closed). A demonstrated-understanding proposal needs at least two demonstrations with
  distinct timestamps and is worded as recorded by the teaching Agent.

## Consequences

- **Positive:** learning survives restarts and host changes; the learner can read and correct the
  model of themselves; Core is unchanged.
- **Negative / risks:** the Markdown format is now a public contract; changes need a schema
  version and this ADR revised. Verification is not authentication (documented).
- **Follow-ups:** platform friction found while building this is recorded in
  `docs/research/findings/plugin-platform-friction.md`.

## Verification

`tests/integration/test_top_down_learning_context.py` and
`tests/integration/test_top_down_learning_flagship.py` cover the brief's twenty validation cases,
including round-trip parsing, stable/dynamic separation, verification forgery, privacy minimization,
cloud bootstrap and resume, and the Claude/Codex STDIO journeys.

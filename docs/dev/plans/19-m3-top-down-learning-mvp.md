# Plan 19 — Top-Down Learning Flagship MVP

## Product boundary

The plugin is a separate example extension, not an Aptuni core feature. It imports only
`aptuni.api.v1`; Aptuni knows nothing about learning paths, prerequisites, teaching turns or answer
checks.

## Bounded MVP

For one target, the plugin:

1. selects a plugin-owned prerequisite catalogue;
2. queries Aptuni separately for each prerequisite and for teaching preferences;
3. marks only explicitly matched foundations as known and keeps the rest needed;
4. returns an ordered project-linked plan;
5. teaches one prerequisite with a short explanation, immediate project step and retrieval/Feynman
   prompt;
6. checks active learner output against plugin-owned observable criteria and either advances or
   repeats with a named gap;
7. only on an explicit caller request, submits that gap as a quarantined Aptuni memory proposal.

The demonstration catalogue targets an intelligent parking system. The architecture accepts other
catalogues without core changes.

## Tests

- Existing Python foundation removes only that prerequisite; a mere goal mention never proves
  mastery.
- Teaching preferences shape the turn without becoming instructions.
- Weak output stays on the same step; sufficient output advances.
- Gap persistence is explicit, idempotent and pending owner review.
- Static import test rejects any internal Aptuni namespace.
- Scaffold output contains a valid manifest, public-only import, starter test and no grant.

## Exit

One executable journey covers `goal → personalized prerequisite map → learning/project plan →
adaptive teaching → learner output/check → next step`, with focused/static/full gates and independent
review of the API pressure it creates.

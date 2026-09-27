# Top-Down Learning — Aptuni plugin MVP

This external-style example starts from a concrete target, reads only owner-granted Aptuni context,
derives the missing prerequisites, couples each explanation to a project action, checks learner
output, and advances or repeats. The included catalogue demonstrates an intelligent parking system;
other domains provide another tuple of `PrerequisiteTemplate` values without changing Aptuni core.

The plugin imports only `aptuni.api.v1`. It never opens the Profile Vault, reads sources, changes
permissions, accepts its own memory proposals, or stores raw conversations. `record_gap` is an
explicit action and produces a quarantined proposal for owner review.

Its `[aptuni]` manifest requires only `context.read`; `memory.propose` is optional. The complete
learning and learner-check journey therefore works when the owner withholds memory capture, while
`record_gap` fails closed. Invoking this plugin does not require a separate Aptuni activation: its
public API client receives only task-relevant context through the exact owner grant.

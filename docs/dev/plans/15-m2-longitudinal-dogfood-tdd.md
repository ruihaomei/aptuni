# M2 Longitudinal Maintainer Dogfooding — bounded TDD plan

## Outcome

Give the maintainer one executable, restartable local workflow for evaluating Aptuni on real data
over time without committing or durably copying query text. The workflow assesses setup, runs a
bounded Context retrieval trial, records explicit useful/noise labels against canonical IDs, takes
content-free longitudinal snapshots, and reports promotion, retrieval, correction, review, noise,
provenance and personalization behavior.

## State and privacy boundary

- Store only in Aptuni's private state directory: query SHA-256, trial id/time, Vault sequence,
  returned canonical IDs, explicit ID labels, and aggregate snapshots. Never persist query text,
  record statements, excerpts, source paths or raw host output.
- Use core-owned paths, mode 0700/0600, same-parent atomic JSON publication and a bounded schema.
- Register `longitudinal_evaluation` in privacy inventory. Any canonical purge invalidates the
  evaluation root because labels and IDs may refer to purged records. Backups exclude it.
- Treat malformed, aliased, oversized or unknown state as an error; never guess or partially parse.

## User-visible vertical slice

1. `aptuni evaluate setup [--json]` reports content-free readiness: configured source types,
   enabled modules, canonical counts, retrieval projection state, and pending review counts.
2. `aptuni evaluate trial QUERY [--limit N] [--json]` runs the ordinary owner Context path and
   stores no query text. It prints the exact returned IDs/text for immediate owner judgment and a
   trial id.
3. `aptuni evaluate score TRIAL_ID --useful ID... --noise ID... [--json]` requires an exact
   partition of all returned IDs and stores only those labels.
4. `aptuni evaluate capture [--json]` appends one bounded content-free snapshot per Vault sequence.
5. `aptuni evaluate report [--json]` reports latest counts and aggregate retrieval precision/noise,
   useful-context rate, traceable-useful rate, review backlog, corrections and promotions over time.

## Red → green sequence

1. Tests for no raw query/content bytes in state, modes, atomic retry/idempotence and malformed state.
2. Trial/score partition, stale/unknown IDs, empty-result and bounded-limit tests.
3. Snapshot metrics over promotion, correction, review/rejection and provenance fixtures.
4. Privacy inventory/purge invalidation tests.
5. CLI JSON and readable journey test: setup → trial → score → capture → report.

## Gates and checkpoint

Use focused tests during implementation, then the complete repository gate and a self-review.
Because this adds managed personal-evaluation state and purge behavior, obtain independent privacy/
deletion review, update durable state and research notes, and create a local checkpoint without
pushing before starting the Obsidian interface.

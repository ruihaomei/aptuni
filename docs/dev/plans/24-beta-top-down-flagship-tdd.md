# Plan 24 — Top-Down Learning Flagship #1 TDD

## Goal

Ship Top-Down Learning with the Beta as a verified, portable, personalized learning workflow that
remains an ordinary `aptuni.api.v1` consumer (ADR-0026).

## Slices

1. **Schema** — `learning_context.py`: model, strict parser, renderer, stable digest, cloud-safe
   export and redaction. Round-trip, malformed-input and bounds tests first.
2. **Workflow** — `workflow.py`: task-scoped retrieval into a draft, learner corrections,
   verification gate, strategy/mode, just-in-time progress loop, explicit memory proposals.
3. **Pedagogy primitives** — `guidance.py`: principle harness plus preference-derived affordances
   (visual, first-principles, project-first, concise/detailed) and cloud checkpoint protocol; the
   teaching Agent writes the personalized strategy.
4. **MCP + host skills** — stateless tools over the context text; Claude and Codex manual skills
   with the first-run journey (target → ≤3 material questions → draft → verify → local/cloud).
5. **Docs/demo/Beta surface** — README, Transformer flagship journey, parking secondary example,
   product positioning, platform friction notes, CHANGELOG.

## Validation matrix

The twenty cases in the maintainer brief, mapped one-to-one to named tests.

## Exit evidence

Focused and full tests, Ruff, strict mypy (source and plugin), host validators, relay; independent
review of the privacy/export, verification and grant boundaries; STATE/HANDOFF; local checkpoint.

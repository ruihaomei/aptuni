# Plan 22 — Top-Down Learning Agent Plugin TDD

## Goal

Turn the existing public-API pressure test into a real, manually invokable Claude Code and Codex
plugin skill whose MCP tools run the goal-first learning loop under one exact owner grant.

## Skill contract

- Trigger: the user explicitly invokes `top-down-study` to learn by building a concrete project or
  achieving a specific goal.
- Input: one concrete goal, followed by active learner explanations or project outputs.
- Output: the smallest missing prerequisite, one short explanation, one project action and one
  retrieval/Feynman-style prompt; the next turn adapts only after checking user output.
- Not included: broad bottom-up curricula, unrequested memory capture, implicit activation, owner
  review decisions, source access or Core special cases.

## Implementation boundary

- Package the example as a standalone plugin with its own MCP server, Claude manifest, Codex
  manifest and one shared `skills/top-down-study` directory.
- The plugin imports Aptuni only from `aptuni.api.v1`; its MCP layer may import the public MCP SDK.
- The installed MCP server receives one owner-approved grant id through configuration. Every public
  API operation revalidates that grant plus live privacy/module policy before returning context.
- Learning progress is returned to the host as bounded structured state and is not written by
  Aptuni or the plugin. Memory proposal remains a separate optional explicit tool.
- Claude marks the skill user-only; Codex sets `allow_implicit_invocation: false`. This is the same
  UX safeguard—not a security boundary—accepted in ADR-0025.

## Failing-first matrix

1. Plugin package contains valid Claude/Codex manifests, MCP config, skill metadata and no dead
   references.
2. Manual skill metadata disables implicit/model invocation on both hosts.
3. Start retrieves granted foundation/preferences and returns one project-first teaching turn.
4. Check requires active learner output, repeats on a demonstrated gap and advances on a correct
   Feynman-style explanation.
5. Progress tokens cannot skip, reorder or invent prerequisites.
6. Optional memory capture is absent/denied when not granted and creates only a quarantined proposal
   when granted.
7. Live grant revocation stops the next tool call.
8. The package imports no internal Aptuni namespace and Aptuni Core has no Top-Down special case.

## Exit evidence

Focused package/MCP/skill/integration tests; plugin and skill validators where available; clean
isolated install; Claude/Codex bundle probes; Ruff; strict mypy; full repository gate; independent
public-interface/privacy review; durable state and local checkpoint.

# Review 99 — Restore the confined Codex tool bridge

- **Date:** 2026-10-03
- **Scope:** the `code_mode_host` exception in `tools/agent_e2e_run.py`, following
  Review 98; nonpersonal setup, inventory and ordinary-task canaries only.
- **Method:** scoped diff, installed Codex CLI 0.155.1 tool descriptions, official
  documentation, focused checks and native canary events. No private tasks,
  held-out prompts, personal answers or live Vault inspection by this reviewer.

## Finding and correction

Review 98's generic OFF canary established configuration and catalog observations,
but did not invoke an MCP tool. A later end-to-end canary exposed a functional
blocker: disabling `code_mode_host` also disabled the host's tool-call bridge. The
model could not activate Full. The runner correctly retained the setup failure
and withheld the ordinary task.

The correction enables only `features.code_mode_host` and checks that effective
setting. Shell, execution, browser, computer, image, apps, plugins, hooks,
multi-agent and the other listed capability providers remain disabled; web search
remains disabled. The exact four-tool Aptuni MCP catalog check is preserved.
This is a host transport dependency, not a new Aptuni endpoint or architecture.

## Security scope and evidence

The installed CLI's embedded tool description identifies this bridge as an
isolated JavaScript runtime without Node, filesystem or network access. Its
disabled-bridge error explicitly names the feature and bundled executable. The
official [Programmatic Tool Calling documentation](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling)
describes isolated V8 execution with no direct filesystem, network or subprocess
access, with external effects routed through enabled tools. The official page
describes the API runtime; local CLI evidence connects the installed bridge to
that execution model. This is sufficient support for this narrow exception in
the inspected host environment, not an independent audit of the V8 implementation.

Native events in the successful end-to-end canary show:

- `aptuni_activation_status` completed with mode OFF.
- `aptuni_activate_context` completed with session Full and zero context items.
- Setup and the following ordinary arithmetic task completed; the answer was `4`.
- The ordinary task made no retrieval call.

The recorded effective settings and MCP catalog retain the intended boundary.
The separate inventory canary makes only an observed status call and stays OFF.
Its model summary reports four tools and undefined `process`, `require` and
`fetch`, but the captured native events contain no standalone JavaScript-cell
output. **Those summary statements are not treated as independently verified
runtime inventory or capability-denial results.** The approval rests on the
documented runtime boundary, inspected configuration/catalog and actual bounded
MCP invocation, with that limitation explicit.

## Verification and limits

- Focused runner/accounting tests: **14 passed**.
- Scoped Ruff: **passed**.
- Native nonpersonal canary: successful empty Full setup followed by an ordinary
  answer; the earlier failed canary remains a failure, not a successful trial.

No blocking issue remains in the bridge-only correction. A future host/runtime
upgrade should repeat the bounded invocation check as well as catalog inspection.
This review approves neither private answer quality nor a b10 release, and does
not retrospectively extend Review 98's OFF-only usability evidence.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

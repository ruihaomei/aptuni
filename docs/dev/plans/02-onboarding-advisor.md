# Milestone 1.4 Plan — Guided Setup and Basic Plugin Advisor

**Status:** Draft; accept only after manifests, recipes, policy, application SDK, and host metadata stabilize.
**Owner:** CLI/application-services slice; host adapters reuse it and may not fork decision logic.

## Scope

A bounded state machine reads versioned plugin manifests, recipes, environment/host probes, and user
answers. It recommends but never silently activates. No marketplace, ranking service, or separate
rules engine is built.

## TDD slices

1. Freeze a versioned `SetupPlan` schema and transitions; invalid/backtracking/interrupted sessions
   leave no side effects.
2. Implement pure recommendation tests from language, detected hosts, named sources, desired memory
   experience, privacy mode, and environment capabilities.
3. Render a preview containing exact plugins, reasons, source roots/origins, API-key references,
   network/host-model egress, retention, setup-time range, difficulty, strengths, and weaknesses.
4. Require one final ADR-0013 confirmation bound to the SetupPlan digest, given by the user in their
   own terminal from the full core-rendered preview (MCP/agents cannot approve; core cannot tell a
   terminal from an agent shell, which the per-host preview discloses). The preview lists every
   host settings file the core CLI will write from bundled profile content, and states per host whether
   host file tools can still read the Vault. Only then create Vault/config, grants, references,
   activations, and the profile recoverably. Confinement stays `unverified` (never claimed in effect);
   no personal L0/MCP release happens without explicit per-module consent.
5. Install/configure, run doctor and smoke tests, and show Vault location, privacy inventory, rollback,
   and next action. Failure produces a resumable/rollback state.

## Scripted acceptance journey

Run every row in Simplified Chinese and English, with Chinese paths and mixed-language source names.

| Case | Class | Host/privacy/source | Expected |
|---|---|---|---|
| A | success | Codex, remote host allowed, Folder | recommends Starter Lite; discloses host egress; succeeds |
| B | success + refusal | Claude Code, strict local-only, no proven local model | content-free setup succeeds; personal L0/MCP release is refused |
| C | success | Both hosts, MarginNote + GitHub, minimized cloud | recommends Researcher; shows token/root/origin and retention |
| D | success | No supported host | CLI-only plan works; adapter steps are documented gaps |
| E | refusal | Missing optional dependency/key | preview marks requirement; no partial activation |
| F | cancellation | User cancels at every question and final preview | no Vault mutation, plugin activation, source/egress grant, or credential reference |
| G | recovery | Crash during confirmed apply | restart deterministically resumes or rolls back; no duplicate grant |

Setup success counts only `success` assertions; safe-refusal counts only `refusal` assertions;
cancellation and recovery have their own 100% pass requirement. Each class keeps at least one case.

For successful cases, assert the required sequence:

1. language; 2. instructions/environment; 3. existing sources; 4. optional discovery consent;
5. memory experience; 6. privacy mode; 7. host detection; 8. recipe; 9. plugin/reason preview;
10. keys; 11. setup time; 12. privacy/retention/egress; 13. trade-offs; 14. one final confirmation;
15. install → validate → smoke → Vault location.

## Exit

- State-machine/property tests cover all transitions, cancellation, resume, and rollback.
- CLI and both first-class host adapters produce semantically identical SetupPlans.
- Snapshots pass both locales with no untranslated keys/messages.
- The exact built-artifact install/doctor/smoke commands pass on `COMPATIBILITY.md`.
- No setup path bypasses application services or the ADR-0013 confirmation; setup ends by showing the
  profile status (`installed` / `missing` / `drifted`) and confinement (`unverified` or `not_in_effect`)
  with full detail from the CLI, and only an enum plus reason codes to the host and in
  `views/Status.md`. It tells the user that the profile covers only newly launched host sessions and
  that the current session must be relaunched.

# Slice 17 — Real-host S12 journeys

**Status:** Implementing (2026-09-21); frozen daily-task matrix PASS, focused Claude probe pending
**Owns:** M1.4 fresh-machine Claude Code/Codex setup, one real daily task per frozen host version,
and the remaining ADR-0013 real-host observations.

## Evidence

- `spikes/s12_hosts/results/daily-task-matrix.json`: Claude Code 2.1.267/2.1.266 and Codex
  0.155.0/0.154.0 all pass the synthetic handoff plus exact ungranted-module denial journey.
- Invocation remediation: preserve only the ordinary `USER` variable needed for Claude's macOS
  keychain lookup; keep expected evidence tokens out of the model prompt; require structured Codex
  MCP events; mark the Codex server required and explicitly forward only `APTUNI_STATE_DIR`.
- Remaining: focused Claude built-in Read/Write and Apple Event observations, full gate and focused
  privacy/host-confinement review.

## Runnable outcome

A sanitized billable runner launches the frozen Claude Code 2.1.267/2.1.266 and Codex
0.155.0/0.154.0 packages against an Aptuni wheel installed outside the writable project. Every host
retrieves the same synthetic handoff marker through the generated grant-bound MCP bundle and proves
that an ungranted module request fails with `mcp_module_denied`.

The focused Claude probe also exercises built-in Read/Write denial and the Apple Event setting. Its
result is recorded conservatively: blocked or agent-reported-only effects remain `unverified`; only
an independently observed write/escape can produce `not_in_effect`.

## Acceptance

1. Host packages resolve to the exact frozen current/prior versions; no global installation is
   replaced and no credential is committed or copied outside a mode-0700 temporary directory.
2. Aptuni is installed from the built wheel into a temporary runtime outside the project writable
   root. The generated bundle points at that interpreter, not the project `.venv`.
3. Each of the four host/version journeys calls `aptuni_get_identity_card`, observes the fixed
   synthetic handoff marker, calls `aptuni_search_context` for an ungranted module, and observes
   `mcp_module_denied` under a no-approval profile.
4. Claude's built-in Read/Write probe runs with exact protected-path deny rules. The outer runner
   independently verifies that Write did not change the marker; returned text is scanned only for a
   random synthetic read token and is never retained.
5. The Apple Event attempt, explicit absence of `--add-dir`, no-approval launch, session hook, and
   package location are recorded without claiming complete effective-settings visibility.
6. Evidence contains only fixed labels, booleans, exact version strings, exit classifications and
   content-free counts. Raw model output, auth files, paths, prompts and synthetic context text are
   never committed.
7. Required focused/full gates pass and independent privacy/host-confinement review has no blocker.

## Non-goals

- Reopening ADR-0013 or claiming the hosts/core can prove confinement.
- Testing latest upstream versions in place of the frozen release pair.
- Persisting host conversations, raw model output, private Vault data or credentials.
- Broad model-quality experimentation beyond the two representative tasks.

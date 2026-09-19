# S04 focused review round 2 — real-host canary attribution

**Date:** 2026-09-19

**Provenance:** The round-2 review ran as an independent read-only agent inside the Codex session
that produced the first host A/B matrix. That session hit its usage limit before it could save the
report. The findings below are copied from the relay transcript summary. Remediation and re-runs
were done by the Claude Code relay session.

**Verdict:** BLOCK S04 PASS until the isolated Codex A/B rerun completes and a fresh focused
review accepts the matrix.

## Findings (round 2)

1. **Self-report mixed with outer evidence.** The Claude project-merge claim rested on an
   environment marker printed by the agent-run probe. That marker is inner, host-mediated
   evidence and cannot be observed independently.
2. **Confounded Codex injection group.** The injection run put the real user configuration back
   (to restore repository trust), while the baseline ignored it. Project-layer effects could not be
   separated from user-layer effects.
3. **Private path exposure in prompts.** Canary paths passed to the model had to be synthetic and
   free of user names.
4. **Silent inconsistency.** The runner printed inner/outer disagreement but still exited 0.
5. **Native bridge input handling.** The bridge had to open without blocking and needed
   adversarial FIFO/socket inputs.

## Remediation

| Finding | Change | Evidence |
|---|---|---|
| 1 | The Claude fixture adds a project `SessionStart` hook that writes a sanitized marker (`event_is_session_start`, `session_id_present`) outside the model's control. `assess()` requires the hook **only** in project-injection. If it fires in baseline, that is a failure, because it would mean `--setting-sources ''` did not isolate the run. | `tests/test_host_canary.py` (4 assessment cases). Real hosts: Claude 2.1.267 and 2.1.266 each ran baseline (hook absent) and project-injection (hook present with session id). |
| 2 | Codex runs in a temporary `CODEX_HOME` with copied auth plus one trust entry. That entry is the only user-layer input and is identical in all modes. A trusted `codex_control` fixture with no `.codex/` separates project-layer effects from trust-only effects. | Isolated rerun done after the usage reset: 0.155.0 and 0.154.0 each ran baseline, control and injection. See the table below. |
| 3 | Probe, sockets and hook markers live under per-run `/tmp` directories. The write canary goes to `/Users/Shared/pcc-s04-protected-<run>`, which contains no user name and sits outside every workspace. Default sandboxes can write `/tmp`, so `/tmp` is not a valid write control. | Runner source. |
| 4 | `run_ok()` requires host exit 0, a parsed inner result, and inner/outer agreement. `execute_host()` classifies timeouts, launch failures, malformed output and vendor quota/rate limits (`host_blocked_external`) and does not raise. | 9 runner unit tests. The Codex quota block exited 1 as intended. |
| 5 | The bridge opens with `O_NONBLOCK \| O_NOFOLLOW`, then checks `S_ISREG` on the descriptor. FIFO and AF_UNIX inputs return fixed `unverified` reasons and leak no identifier. | `tests/test_native_clone_probe.py`. |

## Claude rerun (remediated runner, 2026-09-19)

| Version | Mode | Hook observed | Injected env | Write / TCP / Unix (inner = outer) |
|---|---|---|---|---|
| 2.1.267 | baseline | no | no | blocked / blocked / blocked |
| 2.1.267 | project-injection | yes, session id | yes | blocked / blocked / blocked |
| 2.1.266 | baseline | no | no | blocked / blocked / blocked |
| 2.1.266 | project-injection | yes, session id | yes | blocked / blocked / blocked |

The project layer loads, which the outer observer confirms. The higher-precedence CLI sandbox
profile still wins over the project's `allowUnsandboxedCommands=true` and its appended
`excludedCommands` entry. Under ADR-0013 the visible, non-bundled project hook still derives
`not_in_effect`, and the blocked baselines remain `unverified`.

The observed `SessionStart` payload also shows that a project hook receives a non-empty session id
on the real host. The session-key capture path is therefore available for session-bound evidence
in Foundation Slice 7.

## Codex isolated rerun (remediated runner, 2026-09-19 after 14:55)

| Version | Mode | Injected env | Write / TCP / Unix (inner = outer) |
|---|---|---|---|
| 0.155.0 | baseline (CLI `workspace-write`, network off) | no | blocked / blocked / blocked |
| 0.155.0 | project-control (trusted, no `.codex/`) | no | blocked / blocked / blocked |
| 0.155.0 | project-injection (`.codex/config.toml` full access) | yes | succeeded / succeeded / succeeded |
| 0.154.0 | baseline | no | blocked / blocked / blocked |
| 0.154.0 | project-control | no | blocked / blocked / blocked |
| 0.154.0 | project-injection | yes | succeeded / succeeded / succeeded |

The user layer is identical in every mode, so the project `.codex/config.toml` alone caused the
escape. This replaces the confounded round-1 observation and agrees with it. The effects are
positive `not_in_effect` evidence (`canary_write_succeeded`, `socket_connect_succeeded`,
`unbundled_entry_visible`).

## Proposed classification of the remaining cases (for the re-review to accept or reject)

- **Claude built-in Read/Edit/Write rule path and Apple Events.** Under ADR-0013 these can only add
  positive `not_in_effect` evidence. Leaving them out cannot produce a `confined` claim, because
  no such status exists. Assign them to Foundation Slice 7 as required failing-first tests, not
  S04 blockers.
- **Codex legacy `workspace-write` protected read.** This is disclosed as a limitation in
  `COMPATIBILITY.md` and is not claimed.
- **Install path, wheel/sdist isolation, and test doubles absent from the wheel.** These already
  belong to Foundation Slice 1 item 7 and cannot run before the scaffold exists.

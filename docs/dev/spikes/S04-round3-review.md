# S04 focused review round 3 — acceptance

**Date:** 2026-09-19

**Reviewer:** an independent, read-only agent launched by the Claude Code relay session. It had
no edit rights and ran no billable hosts. It read ADR-0013, plan 00 §5, plan 01 Slices 1 and 7,
the S04 records, `spikes/s04_mcp/` and the host matrix, and it ran the local suite (54 pass,
5 capability skips) and `tools/check_relay.py`.

## Findings (all non-blocking)

1. **Round-2 fixes.** Findings F1–F5 are fixed in code. `assess()` uses only effect booleans
   against outer observations, and the Claude hook must be present if and only if the mode is
   injection. Every Codex mode gets the same temporary `CODEX_HOME`. Prompt paths are synthetic.
   Every failure path exits 1. The native bridge uses `O_NOFOLLOW|O_NONBLOCK` plus `S_ISREG`, with
   FIFO/socket tests.
2. **Codex A/B.** It is causally clean: the injection success also works as a positive control for
   the launch environment. A regression test should pin the identical control/injection argv and
   `CODEX_HOME` in every mode.
3. **Claude hook proof.** It is sound, but the agent could in principle forge the hook marker. The
   marker should be agent-denied, and an inherited `PCC_S04_PROJECT_INJECTION` should be removed.
4. **Overclaim.** The docs claimed that CLI precedence prevented the Claude escape, which cannot be
   measured. They should say "not observed; cause not attributed". The inner
   `project_config_injected` should be labelled as self-report. Per-run evidence should be kept.
   The reason codes should include `escape_setting_visible`.
5. **Privacy.** No leak found. The residual risks should be documented: a SIGKILL can leave the
   copied auth file in a 0700 temp dir, and a full-access run inherits the caller's environment.
6. **Remaining cases.** The proposed classification does not violate ADR-0013 status semantics.
   It does deviate from plan 00 §5 step 4, so it must be recorded. Slice 7 has no host adapter, so
   the real-host execution has to be gated at M1.4/S12. ADR-0013 item 3 was out of date.
7. **Process.** The round-2 file's verdict was not in anchored form, and its findings are a
   transcript summary. Spike focused reviews sit outside `reviews/STATUS.json`.

## Disposition

| # | Action taken |
|---|---|
| 2 | Added `HostCanaryIsolationTests`: identical control/injection argv, and `CODEX_HOME` isolated in every mode. |
| 3 | Added `host_environment()`, which removes the inherited injection marker, and `claude_settings()` now puts the hook marker in `denyRead`/`denyWrite`. Tests added; 58 local tests pass. The four Claude runs were rerun on the final runner. 2.1.267 injection attempt 1 got no inner JSON from the model (runner exit 1, kept but not used as evidence), and attempt 2 passed. |
| 4 | Changed the wording in `COMPATIBILITY.md`, `S04-mcp.md`, the round-2 file and `STATE.md`. The matrix now carries `field_notes`, corrected reason codes and a `per_run_evidence` pointer to `results/host-canary-runs/` (11 sanitized files). |
| 5 | Added the residual risks to the runner docstring. |
| 6 | Added the required wording to plan 00 §5 step 4, plan 01 Slice 7 item 2 and Slice 1 item 7, the ADR-0013 Verification coverage status and item 3, and the ROADMAP M1.4 exit. |
| 7 | The round-2 file now ends with an anchored verdict and keeps its provenance note. Spike focused reviews stay spike-local and are not added to the plan-review registry, following the S01–S03 precedent. |

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

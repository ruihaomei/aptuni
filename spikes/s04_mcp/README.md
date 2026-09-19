# S04 — MCP capability and privacy conformance (review pending)

This Gate 0 spike uses MCP Python SDK 2.2.0 over STDIO with synthetic data only. It separates:

- deterministic protocol/policy evidence (`python run_s04.py` in the pinned disposable venv), and
- real Claude Code/Codex host journeys (`results/`), whose canaries are independently checked by the
  outer runner rather than accepted from model text alone.

Create an external Python 3.13.3 venv and install `requirements-lock.txt`; never install this spike's
dependencies into the future product package. The current disposable path is
`/tmp/pcc-s04-20260919`.

```sh
/tmp/pcc-s04-20260919/bin/python run_s04.py
```

The server is launched through macOS `sandbox-exec` with `deny network*`. Its Python audit hook also
denies internet-socket creation and every socket connect/bind. CPython asyncio requires an internal
`AF_UNIX` socketpair for its self-pipe, so a literal ban on every socket object is incompatible with
this SDK/runtime; that pair has no destination and cannot connect or bind.

The billable host canary is manual and emits only sanitized booleans:

```sh
/opt/homebrew/bin/python3.13 run_host_canary.py \
  --host claude --version 2.1.267 --mode baseline
/opt/homebrew/bin/python3.13 run_host_canary.py \
  --host codex --version 0.155.0 --mode project-injection
```

The current and preceding stable versions of both hosts pass the bounded MCP read path. Baseline
write/TCP/Unix-socket canaries are blocked in all four versions. Claude proves project-setting merge
through an outer-observed project `SessionStart` hook, without escaping the higher-priority CLI
profile. The runner exits non-zero on any inner/outer disagreement, timeout, malformed output or
vendor quota block (`host_blocked_external`). Codex runs use a temporary `CODEX_HOME` holding one
trust entry and compare `codex_control` (no `.codex/`) with `codex_project`. In the isolated rerun the
control blocked everything, while the project layer alone produced all three escapes. Unsafe outcomes derive `not_in_effect`; blocked canaries remain only `unverified`.

`native_clone_probe.c` uses the documented full-clone mapping attributes and never emits paths or
native identifiers. The current APFS Data volume supports `clonefile` but does not advertise
`VOL_CAP_FMT_CLONE_MAPPING`, so its result is correctly `unverified`; the older Foundation signal is
not security evidence. Focused independent acceptance review is still required before S04 is PASS.

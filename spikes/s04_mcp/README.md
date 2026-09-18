# S04 — MCP capability and privacy conformance (in progress)

This Gate 0 spike uses MCP Python SDK 2.2.0 over STDIO with synthetic data only. It separates:

- deterministic protocol/policy evidence (`python run_s04.py` in the pinned disposable venv), and
- real Claude Code/Codex host journeys (`results/`), which are model-behavior evidence only.

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

S04 is not complete until current and preceding stable Claude Code and Codex host journeys pass and
the ADR-0013 per-host confinement/status cases are recorded in `COMPATIBILITY.md`.

# S04 result — MCP capability and privacy conformance

**Result:** IN PROGRESS / BLOCKED ON REQUIRED HOST MATRIX

**Run date:** 2026-09-19

**Local baseline:** CPython 3.13.3 · SQLite 3.53.2 · MCP Python SDK 2.2.0

## Measured facts

The deterministic local layer passes 13 tests. The MCP SDK negotiated modern protocol `2026-07-28`
over a real STDIO subprocess. Five schema-snapshotted tools enforce bounded synthetic output;
resources and prompts are optional and returned empty. Invalid arguments and disabled modules return
tool errors, EOF shuts the server down, and tool input schemas contain no approval, nonce, or
confirmation field.

The policy harness proves terminal-only approval, strict-local denial for remote/unknown hosts,
forged-principal/confused-deputy denial, exact action IDs, digest/scope/epoch binding, replay denial,
one intent under eight concurrent confirmers, hard crashes immediately before and after journal
commit, idempotent restart after effect success but before receipt update, and egress revocation to
`cancelled_policy` with no effect. Observations are idempotent, quarantined, and non-exposable.

The server runs under macOS `sandbox-exec` with `deny network*`. A Python audit hook denies AF_INET/
AF_INET6 creation and all socket connect/bind operations. CPython asyncio itself requires a local
AF_UNIX socketpair for its self-pipe; denying every socket object prevents the STDIO server from
starting. No network destination was observed. Vendor model/auth traffic remains separate and is
not covered by the MCP server sandbox.

### Real host observations

| Host | Result | Observation |
|---|---|---|
| Codex CLI 0.153.4 | partial PASS | In `read-only` + `approval_policy=never`, a read tool without `readOnlyHint` was denied; after the standard annotation was added it returned `HOST_OK 61`. A non-destructive idempotent candidate observation was allowed and core kept it quarantined/non-exposable. |
| Claude Code 2.1.87 | BLOCKED_EXTERNAL | The synthetic run made no tool call or billed API request; the host returned repeated HTTP 400 responses for 131.6 seconds and was terminated. This is neither MCP failure nor PASS. |

Official release sources checked on 2026-09-19 show Codex stable 0.155.0 with previous stable 0.154.0,
and Claude Code npm `stable` 2.1.267 with previous published 2.1.266. The installed hosts are older.
Attempts to start all four versions through `npx` produced no output for 90 seconds and were stopped;
they remain untested.

## Interpretation

MCP tools remain the correct portable baseline, and standard tool annotations are security-relevant
host input. Host approval is not core authorization: Codex may run a reversible write under `never`,
so candidate quarantine and terminal-only promotion must remain application-service invariants.

The local evidence supports the ADR-0005/0012 adapter shape but does not yet clear S04. Do not accept
ADR-0005 or begin production scaffolding until the required host/version matrix and all ADR-0013
confinement/status cases pass.

## Remaining blockers

- Run current + preceding stable Codex (0.155.0/0.154.0) and Claude Code (2.1.267/2.1.266), or record
  a reviewed waiver with attempted source and reason.
- Resolve the Claude API HTTP 400 / account availability issue and complete its synthetic journey.
- Exercise protected-path write/read denial, settings/profile drift, session binding, canaries,
  `not_in_effect` versus `unverified`, project config injection, symlink/hardlink/APFS-clone paths,
  override enumeration, and status path-redaction per ADR-0013.
- Record exact core-observable setting/argv/hook sources in `COMPATIBILITY.md`.
- Add the direct SDK/CLI/MCP outcome-parity table and injection defense-in-depth probes.

Machine evidence is in `spikes/s04_mcp/results/`. The deterministic command is
`/tmp/pcc-s04-20260919/bin/python run_s04.py` from the spike directory.

## Primary sources

- [MCP Python SDK v2.2.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0)
- [OpenAI Codex configuration reference](https://developers.openai.com/docs/config-file/config-reference)
- [OpenAI agent approvals and security](https://developers.openai.com/docs/agent-approvals-security)
- [Claude Code sandbox configuration](https://code.claude.com/docs/en/sandboxing)

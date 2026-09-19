# S04 result — MCP capability and privacy conformance

**Result:** PASS (round-3 focused review: APPROVE WITH NON-BLOCKING NOTES; deferrals recorded)

**Run date:** 2026-09-19

**Local baseline:** CPython 3.13.3 · SQLite 3.53.2 · MCP Python SDK 2.2.0

## Measured facts

The deterministic local layer passes 58 tests (5 host-capability skips). The MCP SDK negotiated modern protocol `2026-07-28`
over a real STDIO subprocess. Five schema-snapshotted tools enforce bounded synthetic output;
resources and prompts are optional and returned empty. Invalid arguments and disabled modules return
tool errors, EOF shuts the server down, and tool input schemas contain no approval, nonce, or
confirmation field.

The policy harness proves terminal-only approval, strict-local denial for remote/unknown hosts,
forged-principal/confused-deputy denial, exact action IDs, digest/scope/epoch binding, replay denial,
one intent under eight concurrent confirmers, hard crashes immediately before and after journal
commit, idempotent restart after effect success but before receipt update, and egress revocation to
`cancelled_policy` with no effect. Observations are idempotent, quarantined, and non-exposable.

The ADR-0013 status prototype has no `confined` value by construction. It distinguishes positive
core-observed unsafe evidence (`not_in_effect`) from absent, skipped, misdirected, agent-only or
unobservable evidence (`unverified`); ignores forged labels/metadata; binds evidence to one session;
and emits only fixed reason codes. Marker paths do not enter host payloads. Realpath plus device/inode
detects symlink and hardlink aliases. Portable stat metadata cannot establish APFS clone ancestry.
The pinned native C bridge now requires all three documented positive signals on two distinct,
same-volume files: equal non-zero `ATTR_CMNEXT_CLONEID`, `EF_SHARES_ALL_BLOCKS`, and
`ATTR_CMNEXT_CLONE_REFCNT >= 2`. It uses file descriptors, validates returned-attribute bitmaps, and
emits neither paths nor identifiers. Missing capability, incomplete attributes, symlinks,
non-regular/cross-volume inputs and open failure return only fixed `unverified` reasons. Its decision
predicate passes positive and adversarial self-tests. This APFS Data volume supports `clonefile` but
does not advertise `VOL_CAP_FMT_CLONE_MAPPING`, so real positive clone-family validation is
unavailable and rename/partial-write/independent-copy host cases are skipped. The earlier Foundation
`fileContentIdentifier` observation is therefore diagnostic only, not security evidence.

An independent focused review blocked ADR-0013 acceptance until two corrections landed. The status
prototype now separates a complete, positively absent profile (`missing` → `not_in_effect`) from an
unreadable/incomplete/ambiguous effective-settings snapshot (`profile: unverified`, confinement
`unverified`). ADR-0013 now treats ordinary copies and APFS clones as distinct objects and permits
only optional positive full-clone evidence from a validated macOS-native scan; absence never proves
confinement. A re-review also caught and fixed unsafe-evidence precedence: a successful canary now
forces confinement `not_in_effect` even when profile discovery is itself `unverified`. The native
bridge is now implemented. Neither host exposes a complete, precedence-attributed effective-settings
snapshot, so their baseline profile remains honestly `unverified`; this is a measured host limit,
not converted into `installed`.

The server runs under macOS `sandbox-exec` with `deny network*`. A Python audit hook denies AF_INET/
AF_INET6 creation and all socket connect/bind operations. CPython asyncio itself requires a local
AF_UNIX socketpair for its self-pipe; denying every socket object prevents the STDIO server from
starting. No network destination was observed. Vendor model/auth traffic remains separate and is
not covered by the MCP server sandbox.

### Real host observations

| Host | Result | Observation |
|---|---|---|
| Codex CLI 0.155.0 / 0.154.0 | required read-path PASS | Both current and preceding stable called the annotated bounded L0 tool in `read-only` + `approval_policy=never` and returned `HOST_OK 61`. |
| Codex CLI 0.153.4 | partial PASS | In `read-only` + `approval_policy=never`, a read tool without `readOnlyHint` was denied; after the standard annotation was added it returned `HOST_OK 61`. A non-destructive idempotent candidate observation was allowed and core kept it quarantined/non-exposable. |
| Codex CLI 0.155.0 / 0.154.0 | protected-write partial PASS | Under real `workspace-write` + `approval_policy=never` sessions, both versions logged a Seatbelt `operation_not_permitted` for a home-directory canary and an independent outer check found no file. Per ADR-0013 this blocked canary remains `unverified`, never `confined`. |
| Claude Code 2.1.267 / 2.1.266 | required read-path PASS | Both versions called the strict-config bounded L0 tool once and returned `HOST_OK 61`. |
| Claude Code 2.1.267 / 2.1.266 | baseline canaries PASS as `unverified` (remediated rerun) | CLI settings disabled unsandboxed commands, Apple Events and Unix sockets and denied the protected marker. Inner write/TCP/Unix results were all false and independent outer observations agreed. A project `SessionStart` hook, observed outside the model and absent in baseline, proved project-layer merge with a non-empty session id; with `allowUnsandboxedCommands=true` and an appended `excludedCommands` entry present, no escape was observed. The cause is not attributed, and blocked results stay `unverified`. The non-bundled project entry itself derives `not_in_effect`. |
| Codex CLI 0.155.0 / 0.154.0 | baseline, control and isolated injection PASS | Explicit `workspace-write`/`never` plus network-off blocked write/TCP/Unix in both versions. With the real trusted-project layer and no CLI sandbox override, project `danger-full-access` loaded; the fixed environment marker and all three inner canaries were true, and the outer marker/listeners independently observed every effect. Review round 2 found the first injection group confounded (it alone reintroduced the real user config). The isolated rerun held the user layer fixed (a temporary `CODEX_HOME` with one trust entry). The trusted no-`.codex` control blocked everything, while the project layer alone produced all three escapes. |
| Claude Code 2.1.87 | BLOCKED_EXTERNAL | The synthetic run made no tool call or billed API request; the host returned repeated HTTP 400 responses for 131.6 seconds and was terminated. This is neither MCP failure nor PASS. |

Official release sources checked on 2026-09-19 show Codex stable 0.155.0 with previous stable 0.154.0,
and Claude Code npm `stable` 2.1.267 with previous published 2.1.266. All four required-version read
journeys and A/B canary journeys completed after account reset. Installed Claude 2.1.87's repeated
HTTP 400 remains an older-version observation only.

## Interpretation

MCP tools remain the correct portable baseline, and standard tool annotations are security-relevant
host input. Host approval is not core authorization: Codex may run a reversible write under `never`,
so candidate quarantine and terminal-only promotion must remain application-service invariants.

The local and host evidence supports the ADR-0005/0012 adapter shape. It also proves why host status
must be evidence-only: blocked canaries do not prove safety, while a trusted Codex project can widen
the effective sandbox. Round 3 accepted S04, and Gate 0 closed on 2026-09-19 (review 15).

## Acceptance and deferred cases

Round 3 (`S04-round3-review.md`) accepted S04 with non-blocking notes, and every note is
dispositioned. The following are recorded deferrals, not open S04 blockers:

- **Real-host probes → M1.4/S12, release-blocking for each host version.** These are the Claude
  built-in Read/Edit/Write deny rules, Apple Events, `additionalDirectories`, agent/SDK approve
  inside a confined session, agent writes of hook/MCP entries, and shadow-module/`PYTHONPATH`. Their
  status logic is a failing-first test in Foundation Slice 7 (plan 00 §5 step 4, plan 01, and the
  ADR-0013 coverage status).
- **Protected reads under Codex legacy `workspace-write`.** This is a disclosed limitation and is
  never claimed.
- **Effective settings.** Neither host exposes a complete effective-settings snapshot, so baselines
  remain `profile: unverified`. Visible project/escape settings and successful canaries still force
  `not_in_effect`.
- **Install path and wheel/sdist isolation → Foundation Slice 1 item 7.**
- **Native full-clone evidence (KI-019).** It stays `unverified` on hosts without
  `VOL_CAP_FMT_CLONE_MAPPING`.

Machine evidence is in `spikes/s04_mcp/results/`. The deterministic command is
`/tmp/pcc-s04-20260919/bin/python run_s04.py` from the spike directory.

## Primary sources

- [MCP Python SDK v2.2.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0)
- [OpenAI Codex configuration reference](https://developers.openai.com/docs/config-file/config-reference)
- [OpenAI agent approvals and security](https://developers.openai.com/docs/agent-approvals-security)
- [Claude Code sandbox configuration](https://code.claude.com/docs/en/sandboxing)

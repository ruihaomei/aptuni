# Review 78 — Beta agent-led setup (`3588df4`, `5cb932c`)

**Scope:** one-APPLY setup with a plugin grant, Top-Down grant discovery, `aptuni guide agent`,
`aptuni connect`, Claude/Codex marketplaces, brief setup recommendation. Independent reviewer.

## Confirmed correct

- The plugin grant created by the single setup APPLY is exactly what the plan shows: capabilities,
  required capabilities and modules come from the frozen, digest-bound step target; apply refuses a
  changed manifest digest; the grant manager re-checks subset rules and egress; the pre-effect claim,
  resume reuse and cancel revocation work.
- Top-Down grant discovery can only select a live owner-approved grant for the same plugin id and
  exact manifest digest; `connect()` revalidates; the server refuses to start otherwise.
- The guide never lets the Agent type APPLY or run apply commands; marketplace files are correct.

## Findings

1. **BLOCKING** — with `--privacy local_only` or no host, the plan said "nothing leaves this device"
   while the same APPLY granted a plugin that runs inside a cloud Agent, whose tool output reaches
   Anthropic or OpenAI; with a host, the release list omitted the plugin's reads.
2. Non-blocking N1 — a missing/unreadable manifest at apply raised an uncaught `ValueError`.
3. N2 — cancel did not discard a pending plugin preview left by a crash.
4. N3 — no test for resume reusing the claimed grant.
5. N4 — "shown above" although the consent block is printed below the steps.
6. N5 — setup `--module` does not narrow the plugin's modules (disclosed on the consent screen).
7. N6 — the brief preview dropped network origins.
8. N7 — `aptuni connect` picks the newest grant by file mtime; a revoked grant leaves an installed
   Claude plugin that fails safe.
9. N8 — neither APPLY prompt requires a real TTY; the guide rule is a behavioural safeguard (ADR-0013).

## Remediation (test-first)

- 1: `--plugin-manifest` is refused unless privacy allows cloud processing and a Claude Code or Codex
  host is chosen; the release section names the plugin, its modules and the host operators; the
  guide offers the plugin only in that case. New parametrized refusal and disclosure tests.
- N1 → `plugin_manifest_changed`; N2 → cancel discards the claimed preview; N3 → resume test; N4 →
  "shown below"; N6 → the brief keeps network origins. N5, N7, N8 → `docs/dev/BACKLOG.md`.

**Verdict:** **BLOCK**

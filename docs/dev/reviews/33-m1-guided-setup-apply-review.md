# Review 33 — M1 guided setup apply review

**Date:** 2026-09-20

**Reviewer:** independent security/privacy/correctness review agent (read-only except for this report)

**Scope:** the uncommitted guided-setup-apply slice on top of `d333d94` — the untracked
`src/aptuni/application/setup.py`, `src/aptuni/cli/setup_apply.py` and
`tests/integration/test_setup_apply.py`, plus the modified `src/aptuni/cli/setup_commands.py`,
`src/aptuni/cli/main.py`, `src/aptuni/adapters/manager.py` (new `revoke`),
`src/aptuni/advisor/catalog.py` (new `version_digest`), both message catalogs, and the
`README.md` / `README.zh-CN.md` edits that advertise the new commands. The review read
`docs/dev/plans/02-onboarding-advisor.md` (TDD steps 1, 4, 5, the A–G journey and the Exit
section), ADR-0013, ADR-0010 and `AGENTS.md`. Because the slice creates host access grants it was
treated as high risk: every field of a pending plan was tampered with, a crash was injected at every
step boundary and in the unjournaled window after each step's side effect, the journal's own failure
modes were exercised, cancellation was verified by filesystem diff rather than by reading code, and
`revoke` was probed for traversal and symlink escape. Every probe ran in `tempfile.mkdtemp()` or in
the session scratchpad; nothing was written to the repository except this file, and no personal data
was written anywhere.

## Validation

- `.tools/bin/uv run pytest`: **359 passed, 47 subtests passed** in 35.64s.
- `.tools/bin/uv run ruff check .`: **All checks passed!**
- `.tools/bin/uv run mypy src`: **Success: no issues found in 60 source files**.
- `python3.13 tools/check_relay.py`: **relay check passed** (run before this report existed; it is
  expected to report this file as absent from the lineage manifest until it is registered in
  `docs/dev/reviews/STATUS.json`).
- Plan-field tamper matrix: **15 mutations**; 14 rejected with `setup_action_invalid`, 1 accepted
  (`action_id`, see N1).
- Crash matrix: **7 step boundaries** + **6 post-effect / pre-journal windows** + 2 in-step
  injections = **15 fault injections**; all 15 resumed to `complete` with exactly one grant per host,
  one source, one Vault. No duplicate grant was ever observed.
- Cancellation matrix: **10 interactive cancellations** (EOF and `KeyboardInterrupt` at each of the
  5 questions) + 4 at the final confirmation; **0 filesystem entries created** in all 14.
- Mutation testing of the test suite: **9 safety mechanisms** neutralized at runtime; 8 produced a
  failing test, **1 survived** (see N8).
- i18n parity: 184 keys in each catalog, **0 keys missing on either side**, **0 placeholder
  mismatches**, **0 of the 38 new `setup.*` keys** identical across locales or unreferenced in `src`.
- Content-leak sweep (unique markers in folder contents, file name and record text) over stdout,
  the plan file, the journal, the receipt, the apply report and every file under `state/`:
  **0 hits**.

## Plan 02 acceptance-case and Exit disposition

| Case / criterion | Result | Evidence |
|---|---|---|
| A — Codex, remote host allowed, Folder | **Fails** | The journey runs and succeeds, but the one confirmation does not disclose host-model egress, operator, destination or retention (B2), and its step list is spoofable (B1). |
| B — strict local-only, refusal of personal L0/MCP release | **Partially met** | `_plan_steps()` correctly emits no `adapter` step under `local_only` and no grant directory is created (`setup_commands.py:237-238`; verified). The refusal of *personal L0 release* is not met in the non-local case: one `APPLY` releases all six modules with no per-module consent (B3). |
| C — both hosts, token/root/origin and retention | **Fails** | Retention, operator and destination never reach the confirmation surface (B2); the host-file list omits `AGENTS.md` and describes files that are never written where a host reads them (B6). |
| D — no supported host, CLI-only plan | **Met** | `host_files == []`, no adapter step, apply reaches `complete`. |
| E — failing requirement, no partial activation | **Fails** | A missing folder does stop the run (the shipped test), but a *failing sync* and a *failing doctor* do not: the adapter grant is still created after the failure and the run reports `complete` (B5). |
| F — cancellation at every question and at the final preview | **Met (100%)** | 14 cancellation points verified by filesystem diff; nothing created in any. Two defects sit next to it, not inside it: the traceback at the confirmation prompt (N5) and the false "Nothing had been created" after a completed apply (B4). |
| G — crash during confirmed apply | **Met (100%)** | 15 fault injections all resumed deterministically; no duplicate grant, no duplicate source, no silently skipped step that had not run. Corrupt, truncated and digest-mismatched journals all fail closed with `setup_action_invalid`. |
| Exit — cancellation/resume/rollback covered by tests | **Partially met** | Cancel and resume are covered; rollback is covered only for grants, and the case-G "no duplicate grant" assertion is vacuous (N8). |
| Exit — CLI and both host adapters produce identical SetupPlans | **Not exercised** | Only the CLI produces plans in this slice; no adapter-side plan path exists yet. |
| Exit — snapshots pass both locales, no untranslated keys | **Met** | Key and placeholder parity are exact; both locales render the plan and the apply report cleanly. The journey itself is never run in zh-CN and never with a Chinese path or a mixed-language source name (N9). |
| Exit — no setup path bypasses application services | **Met** | Every step goes through `AptuniService` (`init`, `add_folder_source`, `sources`, `sync`, `doctor`, `identity_card`, `context`) or `AdapterManager`. `apply_setup_plan` is imported only by `cli/setup_commands.py` and the tests; no MCP tool, hook or worker reaches it. |
| Exit — no setup path bypasses the ADR-0013 confirmation | **Fails** | Reachability is fine, content is not: the confirmation is spoofable (B1) and under-discloses (B2, B3). |
| Exit — ends by showing status + confinement, and says the session must be relaunched | **Partially met** | Confinement is correctly and prominently reported as `unverified` and `host_class` stays `remote_unknown` (verified in the persisted grant). The profile status enum (`installed`/`missing`/`drifted`/`unverified`) is never shown, and the relaunch sentence is false (B6). |

## Blocking findings

### B1 — an untrusted path forges lines in the one confirmation preview

`_render_plan()` interpolates `step.target` and `plan.vault_path` raw into the preview
(`src/aptuni/cli/setup_commands.py:255-272`, line 262). A folder path containing a newline injects
arbitrary lines into the block the owner reads before typing `APPLY`, including the claim ADR-0013
item 4 forbids core from ever making. ANSI escapes and the RTL override U+202E pass through too.

ADR-0013 item 2 requires "untrusted names, delimited and with confusables flagged", and its
Verification section requires that a name containing `$(…)`, a backtick, `'`, `\`, `;` or a newline
"appears only as delimited data in the terminal preview". The repository already ships the right
helper, `_delimited_untrusted()` at `src/aptuni/cli/main.py:663-674`, used by the purge preview
(review 31 R3); `_render_plan()` does not use it. The same raw interpolation appears in the apply
report (`setup.apply.step_result`, `setup_commands.py:339`).

The threat model is the intended one: ADR-0013 item 2 explicitly allows an MCP tool or agent to
*create* a pending action and point the owner at it. An agent that composes
`aptuni setup plan --folder "<forged text>"` controls what the owner reads at the only moment the
design relies on. Binding the digest does not help — the digest binds the forged string.

Reproduction (`--folder` name contains `\nHost confinement: VERIFIED…`):

```text
This will do exactly these steps, in order:
  1. create the Profile Vault at /…/p17-77q4bcef/Aptuni
  - approve this folder as a source, read into your knowledge module: /…/p17-77q4bcef/evil
Files Aptuni will write for your agent hosts:
  - (none)
Host confinement: VERIFIED[31m‮ nc‬ $(whoami) `id` ';rm -rf ~'
  - read the approved sources once and record minimized evidence
  …
```

The two forged lines are indistinguishable from core-rendered structure, and the genuine
`host_files` block and confinement disclosure follow further down where a reader who has already
seen "(none)" and "VERIFIED" will not re-read them.

### B2 — the one confirmation does not disclose host-model egress, operator, destination or retention

`_render_plan()` is the entire preview shown at `aptuni setup apply` before the `APPLY` prompt
(`setup_commands.py:318-326`). It names the action id, the Vault path, the modules, the steps, the
host files and the confinement caveat. It never states that context will be sent to a remote model
endpoint, who operates it, where it goes, or that retention is `externally_controlled_unknown` —
yet `_run_adapter()` passes `allow_host_model_egress=True` on the owner's behalf
(`src/aptuni/cli/setup_apply.py:83`) and the persisted grant carries exactly those fields:

```text
$ cat state/adapters/grants/grant-2c939cf6d287ed06.json
  "destination": "Codex configured model endpoint",
  "host_class": "remote_unknown",
  "host_model_egress": true,
  "operator": "OpenAI",
  "retention": "externally_controlled_unknown",
```

ADR-0013 item 2 requires the CLI preview to show "action type, scope identity and count, egress
provider/destination/data class, and irreversibility". The existing single-adapter path already
meets this: `aptuni adapter apply` re-prints `AdapterManager.preview()` — Operator, Destination,
Retention/deletion — immediately above its own `Type APPLY` prompt (`src/aptuni/cli/main.py:531-537`,
`adapters/manager.py:177-188`). The guided path replaces that confirmation with a weaker one while
performing the same action plus more, which is a disclosure regression on the higher-privilege path.

`aptuni setup plan` does print the full advisor preview (egress, retention, keys, trade-offs), but
`setup plan` and `setup apply` are separate invocations and the plan block alone is what the owner
sees at the moment of consent — which is precisely the case where an agent composed the plan.

### B3 — one `APPLY` releases the L0 identity card; the preview promises a per-module approval that never comes

`DEFAULT_SETUP_MODULES` is all six modules (`setup_commands.py:36`), `_run_adapter()` passes
`plan.modules` straight into the grant, and the default module policy has `expose_enabled=True` for
every module (`src/aptuni/policy/modules.py:16`). There is no second gate. Reproduction on the real
CLI, immediately after one `APPLY`:

```text
$ aptuni remember "I am a PhD researcher in survival analysis" --module identity
Remembered in identity: fct_01M2YAKQ94EA7QTVMZYEBNT237
$ aptuni adapter l0 --grant grant-2c939cf6d287ed06
I am a PhD researcher in survival analysis
```

Plan 02 step 4 requires that "no personal L0/MCP release happens without explicit per-module
consent". Worse than the missing gate is the message that covers for it: `setup.plan.modules` reads
"Modules agents may read **after you approve them**: identity, knowledge, …" (zh-CN: "在你逐项批准后").
The preview tells the owner a per-item approval is still ahead of them; no such approval is ever
requested, and the six modules are live the moment `APPLY` is typed.

### B4 — `aptuni setup cancel` reports "Nothing had been created" after a completed apply

`_setup_cancel()` rolls back only ids beginning with `grant-` (`setup_commands.py:362-369`). A
folder-source id returned by `cancel_setup_plan()` is silently dropped, and when nothing rolls back
the command prints `setup.cancel.nothing` — a false statement — instead of `setup.cancel.vault_kept`.

Reproduction (plan with `--folder`, no host, applied to `complete`, then cancelled):

```text
apply state: complete grants: []
vault exists: True
sources: ['src_01M2YA6MGP542Z5NBBYN2ABC0P']
evidence count: 1
--- now cancel ---
Cancelled setup setup-32d8a5076ea4a5a8. Nothing had been created.
cancel rc: 0
after cancel: vault exists: True sources: ['src_01M2YA6MGP542Z5NBBYN2ABC0P'] evidence: 1
```

A Vault, an approved source and ingested evidence exist; the command says nothing was created and
exits 0. The success report that precedes it promises the opposite — `setup.apply.rollback`: "Undo
what this created with: `aptuni setup cancel <id>`" — and both READMEs repeat it ("`aptuni setup
cancel ACTION_ID` undoes what it created" / "可撤销它创建的内容"). Keeping the Vault is a correct and
documented choice (`setup.cancel.vault_kept`, ADR-0010's explicit-deletion rule); printing "nothing
had been created" while keeping it is not. The source approval is not disclosed as kept in either
branch.

### B5 — a failing step does not stop the run, and the run still reports `complete`

Only an exception breaks the loop in `apply_setup_plan()` (`setup_apply.py:119-138`). Two shipped
steps report failure as a return value instead:

- `_sync_sources()` catches every per-source `AptuniError` and always returns `f"synced:{n}"`
  (`setup_apply.py:91-99`). All sources failing yields `synced:0`, which passes the
  `startswith(("created", "already_present", "ok", "synced"))` success test at line 121.
- the `doctor` step returns `"failed:doctor"` as an outcome (`setup_apply.py:166-168`), which is
  recorded and stepped past.

Reproduction (`service.sync` raises `source_read_failed` for the only approved source):

```text
terminal_state: complete
failure: None
results: {
 "vault:/…/Aptuni": "created",
 "source_folder:/…/n": "created",
 "sync:src_01M2YAN8ET48CA7AFXKJ2N9HNT": "failed:source_read_failed",
 "sync:approved": "synced:0",
 "adapter:codex": "created",          <-- host grant created AFTER the failing step
 "doctor:vault": "ok",
 "smoke:context": "ok"
}
receipt written (apply claimed success): True
receipt results: {… 'sync:approved': 'synced:0', …}   <-- the per-source failure is NOT journaled
```

The host grant is created after the failure, `failure` is `None`, a success receipt is written, and
the per-source failure detail exists only in the in-memory report: it never reaches the journal or
the receipt, so nothing afterwards can see it. A failing `doctor` behaves the same way — the CLI
prints "Vault check: FAILED" and still exits 0 with state `complete`.

This contradicts plan 02 case E ("no partial activation"), plan 02 step 5 ("Failure produces a
resumable/rollback state"), `setup.apply.resumable`'s own wording ("nothing after it ran"), and both
READMEs ("If a step fails, the run stops there and resumes where it left off" / "执行会就地停止").

### B6 — the host-file promise is incomplete and the relaunch sentence is false

`_host_files()` (`setup_commands.py:243-252`) names `.mcp.json` + `hooks.json` for Claude Code and
only `config.toml` for Codex. `AdapterManager.apply()` also writes `AGENTS.md` for Codex
(`adapters/manager.py:150-153`) — an agent-instruction file, not boilerplate metadata. Observed:

```text
PREVIEW host_files: ['claude_code: .mcp.json', 'claude_code: hooks.json', 'codex: config.toml']
ACTUAL  bundle files: ['grant-…ed06/AGENTS.md', 'grant-…ed06/config.toml',
                       'grant-…3045/.mcp.json', 'grant-…3045/hooks.json']
```

Plan 02 step 4 requires the preview to list *every* host settings file the core CLI will write, and
both READMEs bold the claim ("**every host settings file it will write**").

The larger half of the defect is the other direction. None of those files is written where a host
reads it: they are staged inside `state/adapters/bundles/<grant-id>/`, which is why
`AdapterManager.preview()` says "host config is not modified" and why `aptuni adapter apply` ends
with "Review and install the generated host configuration" (`cli/main.py:541-542`). The guided
report says the opposite and never tells the owner the bundle exists or where it is:

```text
Access grants created: grant-c333fd518d1c3045, grant-2c939cf6d287ed06
Your agent host reads this configuration when a session starts, so relaunch the current session
before it takes effect.
```

Nothing will take effect on relaunch. The owner is told the integration is installed, is given no
bundle path and no install step, and the plan 02 step 5 requirement to show the "next action" is
answered with a wrong one. Setup also never prints the profile status enum
(`installed`/`missing`/`drifted`/`unverified`) that the Exit section requires beside confinement.

## Non-blocking notes

- **N1 — `action_id` is shown but not covered by the digest.** `_plan_fields()`
  (`application/setup.py:80-95`) omits `action_id`, which the preview prints as `setup.plan.action`.
  Renaming a pending plan file to another id applies it under the forged id: observed "renamed file
  ACCEPTED under new id; inner action_id = setup-ba07d1b96366e253 … action_id reported:
  setup-bbbbbbbbbbbbbbbb". Effects are unchanged and it needs state-dir write access, which
  ADR-0013 item 1 places outside core enforcement, but the printed rollback id then differs from the
  reviewed one. All 14 other fields — `vault_path`, `steps` (kind and target), `host_files`,
  `modules`, `answers`, `catalog_digest`, `recommendation_digest`, `recipe_id`, `locale`,
  `nonce_id`, `expires_at`, `schema_version`, `digest` — are bound and every edit was rejected.
- **N2 — the receipt path skips the digest check and hardcodes its verdicts.**
  `apply_setup_plan()` returns before `commit_setup_intent()` when a receipt exists and fills
  `doctor_ok=True, smoke_ok=True` unconditionally (`setup_apply.py:107-114`). Reachable without
  tampering: a run whose doctor failed writes a receipt, and the next apply reports
  `doctor_ok = True` in the same object whose `results` still say `doctor:vault: failed:doctor`. A
  forged receipt makes apply report `complete` for a Vault that does not exist, with any digest.
- **N3 — that branch is unreachable from the CLI.** `_setup_apply()` calls `load_setup_plan()` first
  (`setup_commands.py:319`), which looks only in `pending/` and `intents/`, so re-running
  `aptuni setup apply <finished-id>` exits 1 with "No exact pending setup action was found." The
  idempotence asserted by `test_case_g` line 171-173 tests a path the product never takes.
- **N4 — the journal's `results` map is not integrity-bound.** The plan inside the intent is
  digest-checked, the results are not. A crafted `{"adapter:codex": "ok"}` makes the step be skipped
  and the run report `complete` with no grant and no source; a non-string value raises
  `AttributeError` at line 121 (caught by `main()`'s `UNSAFE_STATE_ERRORS`, so no traceback, but the
  code is not a `SetupError`). Corrupt JSON, truncation and a mismatched embedded plan all fail
  closed correctly.
- **N5 — Ctrl-D / Ctrl-C at the confirmation prompt prints a Python traceback.**
  `setup_commands.py:323` calls `input()` with no guard, while `_setup_plan()` and `cmd_advise()`
  both catch `(EOFError, KeyboardInterrupt)` and exit 130 with "Cancelled. Nothing was changed."
  Observed `EOFError: EOF when reading a line` with a full stack. Nothing is created, so case F still
  holds, but review 19 N2's "never print a traceback" boundary does not cover this path.
- **N6 — `revoke()` is safe but leaves a symlinked bundle behind.** Traversal is blocked by
  `_exact_id` (all of `grant-../../../../etc`, `grant-aaaa/../../bbbb`, a trailing newline and
  over-length ids were rejected), `shutil.rmtree` is correctly guarded by `not bundle.is_symlink()`,
  a symlink *inside* the bundle is not followed, and an outside directory survives with its contents.
  Two residues: the dangling symlink stays and `revoke` still returns `True`, and a later apply
  reusing that grant id would `mkdir(exist_ok=True)` through it and write bundle files outside
  `state/adapters`. Separately, `_exact_id` uses `str.isalnum()`, which accepts non-ASCII ids such as
  `grant-٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠`, deviating from ADR-0013's `[a-z0-9-]` charset. Both are pre-existing in
  `AdapterManager`; the new `revoke` inherits them. The new `ACTION_RE = ^setup-[0-9a-f]{16}$` is
  strict and correct.
- **N7 — repeated applies leak pending adapter actions.** `_run_adapter()` calls `manager.plan()`
  before the idempotence check (`setup_apply.py:83-86`), so every resumed apply writes another
  `state/adapters/pending/act-*.json` that nothing cleans up.
- **N8 — the case-G "no duplicate grant" assertion is vacuous.** Of nine safety mechanisms
  neutralized at runtime, eight produced a failing test; removing the `grant_path.exists()` guard in
  `_run_adapter()` and creating the grant unconditionally left all 20 tests green, because
  `grant_id` is derived from the adapter plan digest and a second create overwrites the same file.
  The property is real but it comes from content-addressed ids, not from the resume logic the test
  claims to cover. Asserting the recorded step result is `already_present`, or that the grant file's
  inode/mtime is unchanged, would make it bite.
- **N9 — the journey is never run in Chinese.** Plan 02 says "Run every row in Simplified Chinese
  and English, with Chinese paths and mixed-language source names." Only
  `test_the_plan_renders_in_both_locales_without_untranslated_keys` is parametrized by locale, and it
  uses no folder at all; every A–G case uses `--lang en` and the ASCII path `notes`. Manually driving
  the full journey with `科研笔记 research notes` works in both locales with no mojibake and no
  untranslated key, so this is a coverage gap rather than a defect.
- **N10 — the tests mostly bypass the surface under review.** Fourteen assertions call
  `apply_setup_plan()` directly; only `test_case_f_terminal_confirmation_refuses_anything_but_apply`
  goes through `cli_run(["setup", "apply", …])`, and only for the refusal. No test covers the
  `--confirm-digest` branch, the success path of the confirmation, or `_print_report()` — which is
  why B2 and B6 are invisible to the suite.
- **N11 — `_plan_of()` imports the private `_plan_from_dict` across modules**
  (`setup_apply.py:141-144`). If the parser is the schema's contract it should be public.

## Overall judgment

The engineering underneath this slice is good. The plan schema is genuinely digest-bound — fourteen
of fifteen field mutations fail closed, and the one gap is cosmetic. The crash protocol is the
strongest part: fifteen fault injections, including the dangerous window after a step's side effect
but before its journal write, all resume to exactly one Vault, one source and one grant per host,
because each step's idempotence is real rather than journal-dependent. Corrupt, truncated and
digest-mismatched journals fail closed. Cancellation is clean at all fourteen points measured by
filesystem diff. `_run_vault` resists symlinks, `..` segments and trailing slashes. `revoke` resists
traversal and does not follow symlinks out of `state/adapters`. Nothing leaks: zero marker hits
across stdout, plan, journal, receipt and the whole state directory. Both locales are at exact key
and placeholder parity. No MCP tool, hook or adapter path can reach `apply_setup_plan`, the host
class stays `remote_unknown`, and confinement is reported as `unverified` and never elevated.

What fails is the thing the slice exists to protect. ADR-0013 gave up every enforcement mechanism
except one honest terminal preview and one confirmation, and this preview can be forged by a folder
path the agent that composed the plan chose (B1) — including the words "Host confinement: VERIFIED",
which core is forbidden to say. It also omits the disclosures ADR-0013 item 2 makes mandatory: the
owner types `APPLY` without being told that context will reach a remote model endpoint, who operates
it, or that retention is unknown (B2), while a message tells them a per-module approval is still
ahead when in fact all six modules including the L0 identity card go live on that keystroke (B3).
Around that centre, three promises the product prints in its own success message and in both READMEs
are not kept: cancel says "Nothing had been created" over a live Vault, source and evidence (B4);
a failing sync or doctor does not stop the run and still reports `complete` with the host grant
created after the failure (B5); and the host files the preview enumerates are neither complete nor
written anywhere a host reads, under a closing line telling the owner to relaunch so they take
effect (B6).

None of these reopens the design. B1 has an existing helper three files away, B2 has an existing
preview to reuse, B3 needs a message change plus either a gate or an honest sentence, B4 and B6 are
message and inventory corrections, and B5 is a return-value-to-exception change in two steps. The
slice is close, but it cannot checkpoint while its single confirmation is forgeable and silent about
egress.

**Verdict:** **BLOCK**

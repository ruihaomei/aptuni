# Review 20 — M1.4a plugin catalog, Recipes, i18n and read-only Plugin Advisor

**Date:** 2026-09-19

**Reviewer:** independent Claude subagent (did not write the code under review)

**Scope:** the uncommitted M1.4a slice on top of `HEAD` `0344760`:
`docs/dev/DECISIONS/ADR-0014-plugin-catalog-recipes-and-advisor.md` (Proposed), `src/aptuni/advisor/`
(`manifest.py`, `catalog.py`, `recommend.py`, `preview.py`, `catalog/plugins/*.toml`,
`catalog/recipes/*.toml`), `src/aptuni/i18n/` (`__init__.py`, `messages/en.toml`,
`messages/zh-CN.toml`), `src/aptuni/cli/setup_commands.py` and its wiring in `src/aptuni/cli/main.py`,
`tests/unit/advisor/` and `tests/integration/test_advise_cli.py`. Context consulted: PRD §12, §24–§30,
§48, §50; plan 02; ADR-0002, ADR-0013; `STATE.md`; `THREAT_MODEL.md`; `adapters/manager.py`. This
review is read-only except for this report. Throwaway reproductions are in `temp/review20/`
(gitignored).

**Baseline checks:**
- `ruff check .`: all checks passed. `mypy src`: no issues in 47 files. `tools/check_relay.py`:
  passed.
- `pytest`: all advisor and i18n tests pass (47 in `tests/unit/advisor` plus
  `tests/integration/test_advise_cli.py`). The full suite has two failures:
  `tests/integration/test_review16.py::test_purge_after_torn_ledger_tail_keeps_every_entry[purged0/1]`.
  They come from concurrent uncommitted work on `src/aptuni/vault/store.py` and
  `tests/integration/test_review16.py` (the Review 19 N1 fix). That work appeared in `git status`
  during this review and is outside this slice.
- Packaging: `uv build --wheel` ships all 16 plugin TOMLs, 4 recipe TOMLs and both message catalogs.
  A fresh `/opt/homebrew/bin/python3.13` venv (`temp/review20/venv`) with the wheel installed runs
  `aptuni advise --json --memory basic --privacy quality --no-host` (rc 0) and
  `aptuni recipe list --lang zh-CN` from `/tmp`, with no `PYTHONPATH`.

## Checklist

| # | Check | Result | Evidence |
|---|---|---|---|
| 1a | Advisor never selects `planned`/`preview` | **Pass** | `_Builder.want` (`recommend.py:110-119`) selects only `builtin`. Probes cover temporal + MarginNote + Cursor, automatic memory, Obsidian/Notion sources: every non-builtin entry is in `deferred`, with `planned`, `evidence_gate`, `no_provider` or `protocol_only` as the reason. `recipe_available` requires every required plugin to be `builtin`. |
| 1b | `builtin` set matches shipped code | **Pass** | The builtin entries are folder, github, memory.builtin, sqlite_fts, mcp, claude_code, codex and cli. Each matches a runnable slice in `STATE.md` (slices 1–7). Mem0, Graphiti, hybrid, Obsidian source/interface, Cursor and Claude Desktop are `planned`. |
| 1c | MarginNote non-selectable (KI-020) | **Pass** | `source.marginnote` is `preview`. With `--source marginnote` it is deferred with `advisor.reason.evidence_gate`. No recipe lists it in `plugins` or `later`. |
| 2a | `local_only`: hosts not presented as receiving context | **Pass** | Host reason becomes `adapter_content_free`, `host_release=refused_local_only`, and `host_model` is removed from egress. |
| 2b | `local_only` disclosure is honest and achievable | **FAIL, B1** | The preview says "nothing leaves this device" and "they receive no personal context". This breaks the ADR-0013/THREAT_MODEL non-claim, and the promised content-free adapter mode is not shipped. See B1. |
| 2c | Egress/network disclosure complete for selected plugins | **Pass for the bundled catalog** | GitHub adds `source_origin`, `https://api.github.com` and optional `GITHUB_TOKEN`. Hosts in quality/minimize modes add `host_model`. The schema allows gaps (N3). |
| 2d | `advise`/`plugin`/`recipe` read-only | **Pass** | `temp/review20/probe.py` ran 9 invocations (plugin list/json, recipe list/show/unknown, 3 advise variants, a failing advise) with temp `HOME`, cwd and `APTUNI_STATE_DIR`. Nothing was created. The interactive pty run (`pty_probe.py`) also created nothing, including on EOF and SIGINT. `main()` builds `AptuniService(Workspace.default())`, and that constructor does not mkdir. |
| 3a | Malformed/non-UTF-8 TOML fails closed without echo | **Pass** | `malformed_toml:plugins/one.toml`. The existing test checks for no echo. |
| 3b | Unknown fields, bad ids, bad schema version, min>max, id/category mismatch | **Pass** | `extra="forbid"` is set on every model. Rejected inputs include ids with a trailing newline, uppercase letters or `../`, a recipe with an extra field, and a bad recipe id. |
| 3c | Duplicates and unknown refs (including `later`) | **Pass** | `duplicate_plugin`, `duplicate_recipe`, `unknown_plugin:starter-lite:memory.nowhere` (from `later`). |
| 3d | Non-https / non-exact origins | **Pass (weak)** | `http://`, a path, userinfo and a trailing newline are rejected (`re.fullmatch`). The degenerate `https://-` is accepted (N3). |
| 3e | Hostile TOML | **Pass with note** | 5000-deep array nesting raises `RecursionError`, not a fixed code. It still fails closed and echoes nothing. Only bundled package data is loaded (N3). |
| 4a | Key and placeholder parity | **Pass** | Tests plus a probe: identical key sets. The only identical en/zh values are the pure-format `bullet`/`minus`/`note` templates. |
| 4b | Missing parameter handling | **Pass** | `missing_parameter:advisor.preview.item:plugin_id,reason`. Values are not re-formatted, so no injection through `{…}` in parameters. |
| 4c | Locale normalization | **Pass with note** | `zh_CN`, `zh-Hans`, `2`, `简体中文` and `EN-GB` work. With `strict`, `fr` and `3` are rejected. `zh-TW`/`zh-Hant`/`zh_HK` map to Simplified (N7). |
| 4d | No untranslated Chinese | **Pass** | Every zh-CN value is translated. Plugin ids and CLI tokens stay in English on purpose. |
| 5a | Non-interactive errors localized, no traceback | **Pass** | `advise --lang zh-CN --privacy quality` prints `缺少回答：memory…`, rc 2. `recipe show nope` is English-only (N7). |
| 5b | Interactive: language first, retries invalid input | **Pass** | pty run: invalid `9` then `2` gives zh-CN; invalid memory `x` retries; §50 order is sources → memory → privacy → hosts. EOF/Ctrl-C print tracebacks (N1). |
| 5c | Digest locale-independent | **Pass** | `to_dict()` holds only ids and message keys. The en/zh CLI test and the unit test agree. The `local_only` digest differs. |
| 6 | Packaging | **Pass** | See baseline. |

## Blocking findings

### B1 — `local_only` preview overclaims privacy and promises an unshipped content-free adapter mode

**Files:** `src/aptuni/advisor/recommend.py:151-152, 161-163, 174-175`;
`src/aptuni/advisor/preview.py:43-47`; `src/aptuni/i18n/messages/en.toml:86, 94, 111-112, 118` (and the
matching `zh-CN.toml` keys); `src/aptuni/adapters/manager.py:79-83`.

**Reproduction:**

```sh
APTUNI_STATE_DIR=temp/review20/state PYTHONPATH=src .venv/bin/python -m aptuni advise \
  --source folder --memory basic --privacy local_only --host claude_code </dev/null
```

The output includes:

```text
Will be set up:
  - Claude Code adapter [agent.claude_code]: registered content-free: local-only privacy withholds personal context
Privacy: your Vault stays on this device; data leaves it only as listed:
  - nothing leaves this device
Agents: connected content-free (local-only privacy)
Benefits:
  + Personal context arrives without you asking.
Trade-offs:
  - Whatever it reads is sent to Claude's model.
Notes:
  * Claude Code and Codex send what they read to cloud models, so with local-only privacy they receive no personal context.
```

**Why it blocks (security/privacy contract):**

1. **Overclaim against an accepted contract.** ADR-0013 (Accepted) makes shell-capable hosts
   trusted like the user, and core never claims confinement. `THREAT_MODEL.md:192-195` is explicit:
   *"strict local-only governs only core-mediated delivery to the host (MCP, L0 hook), and the
   onboarding privacy preview says so per host."* This preview is that onboarding privacy preview.
   For a user who answered "No — everything must stay local", it states that nothing leaves the
   device and that Claude Code/Codex receive no personal context. Yet the plan includes a cloud-model
   host whose file tools and shell can read the plaintext Vault unless host confinement is in
   effect, and confinement is at best `unverified`. `_finish` drops `host_model` from `egress`
   (`recommend.py:174-175`), so the residual path is not disclosed at all. The same preview also
   lists "Personal context arrives without you asking" as a benefit, which contradicts its own
   privacy section.
2. **Recommends a mode the shipped code cannot produce.** ADR-0014's decision driver is "never
   recommend something that is not shipped". The shipped `AdapterManager.plan` refuses any plan
   without host-model egress (`host_model_egress_required`, `manager.py:79-83`). No content-free
   adapter registration exists yet, so "Will be set up: … registered content-free" describes an
   unshipped capability (plan 02 case B is future work).

**Minimal fix (either option is acceptable):**
- Under `local_only` with a first-class host, keep the adapter out of `selected`. Defer it with a
  new reason such as `advisor.reason.content_free_not_shipped`, or mark it as "not set up now; Aptuni
  will not release personal context to it". Alternatively, add the content-free mode to the adapter
  manager first.
- In every mode where a shell-capable host is in the plan, add a residual-egress line to the
  privacy block and never print `egress_none`. For example, a fixed egress kind `host_file_access`:
  "Claude Code/Codex can still read Vault files with their own file tools and send them to their
  model unless host confinement is in effect; Aptuni cannot verify this". Reword
  `advisor.note.local_only_hosts` and `host_release.refused_local_only` to "Aptuni releases no
  personal context to them" rather than "they receive no personal context". Suppress the adapter
  "Personal context arrives…" strength when the release is refused.
- Add tests: in `local_only`+host, `egress_none` is absent and the residual line is present in both
  locales; no selected plugin claims a mode that the shipped adapter refuses.

## Non-blocking notes (to `BACKLOG.md`)

- **N1 — Interactive cancel prints tracebacks.** EOF (Ctrl-D) and Ctrl-C in `advise` raise raw
  `EOFError`/`KeyboardInterrupt` tracebacks (`setup_commands.py:102`). No side effects occur. Catch
  both and print a localized "cancelled, nothing changed" with rc 130/1. This is needed later for
  plan 02 case F.
- **N2 — CLI does not catch `CatalogError`/`I18nError`.** A corrupted install yields a traceback
  whose chained pydantic `ValidationError` echoes TOML values. Only bundled package data is loaded,
  so risk is low. Map both to fixed-code messages in `cmd_*`.
- **N3 — Schema gaps.**
  - `egress` `source_origin`/`cloud_api` is accepted with an empty `network`. The planned Mem0 and
    Graphiti entries declare `cloud_api` with `network = []`, which would under-disclose if they
    were promoted as-is.
  - `contract_version = true` is coerced to `1`. Consider pydantic strict mode.
  - Other accepted inputs: the degenerate origin `https://-`, duplicate `egress` entries, duplicate
    or overlapping recipe `plugins`/`later`, unvalidated `suggested_sources`, a file name that
    differs from the `id` (the ADR says `<id>.toml`), and message keys that exist in no locale
    (these fail later at render).
  - Deep nesting raises `RecursionError` instead of `malformed_toml`.
- **N4 — Privacy filter ignores `local_only_supported`.** PRD §27 says "the Advisor filters
  candidates accordingly", but `recommend` never reads `requirements.local_only_supported`. This is
  latent while every builtin is `true`.
- **N5 — Weak shipped-set pin.** `test_bundled_catalog_matches_shipped_code` uses a subset check over
  `maturity != "planned"`. Pin the exact `builtin` set, assert `source.marginnote == "preview"`, and
  assert MarginNote is deferred in case C.
- **N6 — Preview omits `retention` and `difficulty`.** Both are required by plan 02 step 3 and are
  already in the manifests. The per-host "file tools can read the Vault" statement belongs here
  too (see B1).
- **N7 — i18n/UX nits.**
  - `zh-TW`/`zh-Hant`/`zh-HK` normalize to zh-CN (Traditional → Simplified). Prefer falling back to
    `en` or asking.
  - `--lang fr` silently falls back to English.
  - `recipe show <unknown>` prints an English-only error.
  - The optional-key text uses ASCII `(…)` hard-coded in `preview.py:39`.
  - `plugin`/`recipe list` column widths misalign with CJK text.
- **N8 — `minimize_cloud` is only a note.** It behaves exactly like `quality`. The note "Agents
  receive only small, budgeted slices" applies to both modes, so it does not describe a real
  difference.
- **N9 — No-source plan.** `--source marginnote` alone yields a plan with no source selected. Add a
  note suggesting a Folder source over an export.
- **N10 — GitHub Enterprise origins.** GitHub `network` lists only `https://api.github.com`, while
  Slice 7 also supports enterprise origins that the user configures. Say so in the preview when
  known.
- **N11 — Digest binding.** The digest binds neither the catalog/schema version nor the answers.
  Revisit when the apply step binds confirmation to it.

**Verdict:** **BLOCK**

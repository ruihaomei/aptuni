# Review 21 — M1.4a advisor/catalog focused re-review

**Date:** 2026-09-19

**Reviewer:** independent Claude subagent (did not write the code under review)

**Scope:** focused re-check of review stream `m1-advisor-catalog`: blocking finding B1 from
`20-m1-advisor-catalog-review.md`, plus spot-checks of N1–N7 as claimed in
`20-m1-advisor-catalog-remediation.md`. The code under review is uncommitted in the working tree on
top of `HEAD` `82ad8ee`: `src/aptuni/advisor/`, `src/aptuni/i18n/`, `src/aptuni/cli/setup_commands.py`,
`tests/unit/advisor/` and `tests/integration/test_advise_cli.py`. This review is read-only except for
this report. Throwaway reproductions are in `temp/review20/` and `temp/review21/` (gitignored).

**Baseline checks:**
- `pytest`: 264 passed, 47 subtests passed, exit 0. The Review 19 N1 vault fix (`ec4ebbe`) and the
  retrieval change (`82ad8ee`) are committed, so the full run is green.
- `ruff check .`: all checks passed. `mypy src`: no issues in 47 files.
- `tools/check_relay.py`: **fails with 4 errors outside this slice's code** (note R1).

## B1 verification

| Check | Result | Evidence |
|---|---|---|
| `local_only` + Claude Code/Codex: adapters deferred, not selected | **Verified** | `recommend.py` `_hosts`: under `local_only`, first-class hosts go straight to `deferred` with `advisor.reason.adapter_needs_egress`; `agent.mcp` is popped. CLI `--host claude_code --host codex` and JSON `--host codex`: `selected` = cli, memory.builtin, sqlite_fts (+ folder); `deferred` holds both adapters; `egress=[]`; `host_release=refused_local_only`. |
| No "nothing leaves this device" when a host is named | **Verified (en + zh-CN)** | `preview.py` prints `egress_none` only when `not rec.egress and not rec.host_file_access`. Neither "nothing leaves this device" nor "没有任何数据离开本机" appears for claude_code+codex, and it is also absent for `local_only` + Cursor. It still appears with `--no-host`, which is correct. |
| Host file-access disclosure present | **Verified (en + zh-CN)** | `host_file_access` is true for claude_code, codex or cursor, in every privacy mode. en: "agents you use can read files … including your Vault, unless they are confined; Aptuni cannot verify confinement". zh-CN: "…（包括你的 Vault），除非它们被隔离；Aptuni 无法验证隔离是否生效". In quality mode, the line appears together with `host_model` egress. This matches `THREAT_MODEL.md:192-195` and ADR-0013 (no claim of confinement). |
| No "content-free" wording | **Verified** | `grep -n "content.free\|无内容"` over both message catalogs finds nothing. Renamed wording: "Agents: not connected (local-only privacy)" / "智能体：不连接（仅本地隐私模式）". The local-only note now says Aptuni *will not release* context, and advises keeping the Vault outside folders opened with those agents. |
| No unshipped mode promised | **Verified** | No adapter is selected under `local_only`, which is consistent with `AdapterManager.plan` requiring host-model egress (`manager.py:79-83`). The contradictory "Personal context arrives without you asking" benefit no longer appears. |
| Digest is still locale independent | **Verified** | en and zh-CN runs of the same `local_only` plan both print `sha256:ff93916719db…3aed6`. |
| Regression tests | **Present, passing** | `test_recommend.py::test_case_b_local_only_defers_adapters_and_discloses_host_file_access`, `::test_no_host_means_no_host_file_access_disclosure`, `test_advise_cli.py::test_local_only_preview_never_claims_nothing_leaves_when_a_host_is_named` (bilingual). |

**B1: closed.**

## N1–N7 spot-checks

| Note | Result | Evidence |
|---|---|---|
| N1 cancel tracebacks | **Fixed** | Real pty run (`pty_probe.py`): EOF and SIGINT print "Cancelled. Nothing was changed.", rc 130, with no traceback and no state dir created. Test: `test_interactive_cancel_is_quiet`. |
| N2 catalog/i18n errors | **Fixed** | `cmd_advise` maps `CatalogError`/`I18nError` to the fixed `advisor.error.catalog`, rc 1. The message is always English, a reasonable fallback because the i18n catalog may be the broken part. |
| N3 (part) | **Fixed as claimed** | Re-ran `schema_probe.py`: `https://-` → `invalid_manifest`; `source_origin` or `cloud_api` without origins → `invalid_manifest`; 5000-deep nesting → `malformed_toml`. Mem0/Graphiti now declare `https://api.openai.com`. Remainder is in the backlog. |
| N4 privacy filter | **Fixed** | `_Builder.want` defers `local_only_supported = false` plugins under `local_only` with `advisor.reason.excluded_privacy`. |
| N5 shipped-set pin | **Fixed** | Exact equality on the builtin set {claude_code, codex, mcp, cli, memory.builtin, sqlite_fts, folder, github}, plus `source.marginnote == "preview"` (`test_catalog.py:66-71`). |
| N6 retention/difficulty | **Fixed** | The preview shows "Difficulty: easy" and "Stored on this device: …" in both locales. Both fields are part of the digest payload. |
| N7 (part) | **Fixed** | `zh-TW`, `zh-Hant`, `zh_HK`, `zh-MO` and `zh-Hant-TW` now map to `en`, while `zh`, `zh-CN` and `zh-Hans-CN` map to `zh-CN`. |

## Blocking findings

None.

## Non-blocking notes

- **R1 — Relay check fails; fix before the checkpoint commit.** `tools/check_relay.py` reports 4
  errors, none in the reviewed code:
  - The modified `README.md` links to `SECURITY.md` and `CONTRIBUTING.md`, which do not exist.
  - `STATE.md` and `HANDOFF.md` manifest lines are stale against `STATUS.json`, which now registers
    `m1-advisor-catalog`.

  Register this review (21, superseding 20) in `STATUS.json`, then regenerate both manifest lines and
  fix or drop the README links before committing (AGENTS.md handoff rule).
- **R2 — Contradictory note under `local_only`.** With a named first-class host, the plan also shows
  `advisor.note.cli_only`: "No supported agent selected … connect an agent later with 'aptuni adapter
  plan'". The user did name one, and `adapter plan` requires host-model egress, which conflicts with
  the chosen privacy mode. Suppress `cli_only` when `host_release == "refused_local_only"`.
- **R3 — Platform wording.** `advisor.preview.host_file_access` and `advisor.note.local_only_hosts`
  say "this Mac"; "this device" / "本机" is accurate on every platform (zh-CN already says 本机).
- **R4 — Latent retention contradiction.** The retention line is headed "Stored on this device", but
  `advisor.retention.provider_managed` says "data held by an external memory provider". Only
  planned plugins use it today; split the header when Mem0 or Graphiti ship.
- **R5 — zh-CN list separators.** Retention kinds and API-key lists are joined with ASCII ", ".
  Chinese text should use "、".
- **R6 — `host_file_access` host list.** It covers claude_code, codex and cursor but not
  claude_desktop, which can gain file access through MCP extensions. Revisit when that adapter moves
  past `planned`.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

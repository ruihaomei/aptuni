# M1 Advisor/Catalog Review Remediation

- **Date:** 2026-09-19
- **Responds to:** `20-m1-advisor-catalog-review.md`
- **Status:** blocking finding fixed test-first; focused re-check requested

| Finding | Remediation |
|---|---|
| B1 local-only preview overclaims privacy and promises an unshipped content-free adapter | Under `local_only`, first-class host adapters are now **deferred** (`advisor.reason.adapter_needs_egress`), so neither `agent.*` nor `agent.mcp` is selected and no content-free mode is implied. A new `host_file_access` field is true whenever a shell-capable host (Claude Code, Codex, Cursor) is named; the preview then prints that the host's own file tools can read files, including the Vault, unless confined, and that Aptuni cannot verify confinement. "Nothing leaves this device" is printed only when there is no egress and no named host. The local-only note now says Aptuni *releases* no context and advises keeping the Vault outside folders opened with those agents. Tests: `test_case_b_local_only_defers_adapters_and_discloses_host_file_access`, `test_no_host_means_no_host_file_access_disclosure`, and the bilingual CLI test `test_local_only_preview_never_claims_nothing_leaves_when_a_host_is_named`. |
| N1 cancel tracebacks | `EOFError`/`KeyboardInterrupt` → localized "Cancelled. Nothing was changed.", rc 130 (test). |
| N2 catalog/i18n errors | `CatalogError`/`I18nError` in `advise` → fixed message, rc 1, no echo. |
| N3 schema gaps (part) | Networked egress (`source_origin`, `cloud_api`) must declare origins; Mem0/Graphiti now declare `https://api.openai.com`; origins require valid DNS labels (`https://-` rejected); deep nesting → `malformed_toml` (tests). |
| N4 privacy filter | Under `local_only`, a plugin without `local_only_supported` is deferred with `advisor.reason.excluded_privacy`. |
| N5 shipped-set pin | Exact `builtin` set equality plus `source.marginnote == "preview"`. |
| N6 retention/difficulty | Recommendation carries `difficulty` and `retention`; the preview renders both (test). |
| N7 (part) | `zh-TW`/`zh-Hant`/`zh-HK`/`zh-MO` no longer map to Simplified Chinese (tests). |

N3 remainder (strict typing, duplicates, file-name/id match, orphan keys), N7 remainder, and N8–N11
are recorded in `docs/dev/BACKLOG.md`. Validation: 264 tests plus 47 subtests, Ruff and strict mypy
pass.

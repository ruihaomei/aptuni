# ADR-0014: Describe plugins and Recipes as bundled TOML and advise without side effects

- **Status:** Accepted (2026-09-19; review 20 BLOCK → remediation → focused re-review 21)
- **Date:** 2026-09-19
- **Deciders:** maintainer (final say) · proposing agent (Claude Code) · reviewing agent
- **PRD refs:** §12, §24, §26–§30, §48, §50
- **Research refs:** `docs/dev/plans/02-onboarding-advisor.md`; ADR-0002 manifest fields
- **Needs maintainer confirmation:** no. The file format differs from the PRD's illustrative `.yaml`
  example; it is reversible and loses no information.

## Context

PRD §12 requires machine-readable plugin metadata that powers the Plugin Advisor. §29–§30 require
Recipes, with Starter Lite and Researcher in Milestone 1. §24 requires English and Simplified
Chinese through an i18n system rather than duplicated logic. ADR-0002 fixes which fields an
activation manifest must carry (ID, category, contract version, capabilities, requirements,
privacy/retention, setup effort, maturity). Plan 02 orders the work: frozen schemas first, then
pure recommendations, then a confirmed apply.

## Decision drivers

- Zero new runtime dependencies (the Starter Lite promise)
- One file per plugin/recipe, so community contributions are small, reviewable diffs
- Never recommend something that is not shipped; never mutate anything while advising

## Options considered

### A — YAML files as in the PRD examples

**+** Matches the PRD illustration. **−** Needs PyYAML (a new dependency) and YAML's implicit typing
(`no` → `false`) is a known footgun for contributors.

### B — TOML files read with the standard library's `tomllib`

**+** No dependency, explicit types, familiar from `pyproject.toml`. **−** Deviates from the PRD's
file extension.

### C — Python modules

**+** Type-checked. **−** Importing contributor code to read metadata defeats the S02 rule that
discovery must not execute plugins.

## Decision

Choose **B**.

- `src/aptuni/advisor/catalog/plugins/<id>.toml` holds one `PluginManifest` (schema version 1):
  `id` (`<category>.<name>`, the prefix must equal the category), `category`, `contract_version`,
  `maturity`, `milestone`, i18n `name`/`summary`/`strengths`/`weaknesses` keys, `capabilities`,
  `requirements` (Docker, local-only support, exact HTTPS network origins, API keys as
  environment-variable references only), `setup` minutes/difficulty, declared `egress`
  (`none | source_origin | host_model | cloud_api`) and `retention`. Unknown fields are rejected.
- `maturity` is honest: `builtin` is shipped and supported; `preview` has code but is held behind an
  evidence gate (MarginNote until KI-020 closes); `planned` does not exist. **The Advisor selects
  only `builtin`.** Everything else is listed as deferred with a reason.
- `src/aptuni/advisor/catalog/recipes/<id>.toml` holds a `Recipe`: required `plugins`, `later`
  plugins shown as deferred until they ship, and suggested sources. A recipe is installable only
  when every required plugin is `builtin`. Sources and host adapters come from the user's answers.
- `recommend(SetupAnswers, Catalog)` is pure. Users answer about experiences (memory: basic,
  automatic or temporal; privacy: quality, minimize_cloud or local_only; sources; hosts). An
  experience whose recipe is not installable falls back to Starter Lite or Researcher with an
  explicit note. `local_only` keeps first-class host adapters content-free (ADR-0013). The result
  carries a language-independent `sha256` digest so a later apply step can bind confirmation to it.
- `aptuni advise` asks the §50 questions in order, starting with language, or takes them as options.
  It prints a preview and changes nothing. `aptuni plugin list` and `aptuni recipe list|show` are
  read-only.
- Messages live in `src/aptuni/i18n/messages/{en,zh-CN}.toml`. Tests enforce identical keys and
  placeholders across locales, and translation of every catalog key.

This catalog describes builtin plugins for the Advisor. Third-party activation, entry-point
discovery and closure approval remain as specified in ADR-0002 and are not implemented here.

## Consequences

- **Positive:** A contributor adds a plugin or recipe with one TOML file plus two message lines. The
  Advisor cannot overstate availability, and advice needs no Vault.
- **Negative / risks:** The bundled catalog must be updated when a plugin ships (a test pins the
  shipped set). The planned entries describe intent that may change.
- **Follow-ups:** the plan 02 steps 1, 4 and 5 (`SetupPlan` state machine, one terminal
  confirmation bound to the digest, then install, doctor and smoke). Promote `source.marginnote`
  to `builtin` when KI-020 closes.

## Verification

`tests/unit/advisor/` (catalog validation, duplicate/unknown/invalid rejection, no content echo,
recommendation cases A–D from plan 02, fallbacks, digest stability, locale parity) and
`tests/integration/test_advise_cli.py` (read-only, both languages, localized errors, interactive
order and retry). A clean wheel install runs `aptuni advise` and `aptuni recipe list`.

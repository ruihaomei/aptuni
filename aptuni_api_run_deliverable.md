# Aptuni Integration and Developer Platform Run

## Integration activation

- Notion: the real connector returned the authenticated owner/workspace identity through the exact
  read-only `self` endpoint. No search, write or OAuth restart occurred. A content fetch is paused
  until the owner supplies one exact page/database URL.
- Obsidian: Aptuni `0.1.0` is installed at
  `/Users/ruihaomei/Study_Work_Award/.obsidian/plugins/aptuni`. `manifest.json`, `main.js` and
  `styles.css` byte-match the packaged assets, use private modes, and JavaScript syntax passes.
  Obsidian has not yet enabled the plugin.

## Public API and plugin SDK

ADR-0024 accepts `aptuni.api.v1` and `aptuni.plugin@1` as the supported boundary. Immutable DTOs
provide bounded Profile, Memory, Context, Evidence and review reads plus quarantined memory
proposals. Exact manifest-bound grants enforce capabilities, modules, provenance and current
exposure policy; they are integrity-checked, revocable, privacy-managed and live-revalidated.
Aptuni v1 authorizes SDK clients but never discovers or executes third-party code.

`aptuni developer` provides manifest inspection, a six-file public-only scaffold and owner-confirmed
plan/apply/list/cancel/revoke. Concurrent/crash apply is single-effect. Review 63 independently
approved the final contract after adversarial lifecycle remediation.

## Flagship pressure test

`examples/plugins/top_down_learning` implements the bounded sequence:
goal → personalized prerequisite map → project-first teaching → learner output/check → next step.
It reads only granted knowledge, skills and preferences; treats negated statements as gaps; adapts
the teaching style; and sends explicit gap feedback through quarantined owner review. Aptuni core
contains no learning-specific branch.

## Verification and remaining owner actions

The final gate recorded 725 passed, 3 optional skips and 61 subtests; Ruff, strict mypy over 95
source files, relay, source/artifact supply-chain checks, frozen lexical/hybrid evaluation, fresh
wheel/sdist legal inspection, clean-wheel SDK/scaffold/revoke smoke, JavaScript syntax and exact
Obsidian asset comparison all pass.

Remaining owner actions are limited to enabling/configuring Aptuni in Obsidian and supplying one
exact Notion page/database URL for the consent-preserving content read.

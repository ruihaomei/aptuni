# Review 64 — M3 Notion Real-Activation Compatibility

**Date:** 2026-09-24
**Scope:** official Notion page URL normalization in `src/aptuni/sources/notion.py` and its focused
scope tests
**Reviewer:** independent agent (`api_contract_review`)
**Prior contract:** ADR-0021, Review 60

## Finding

No blocking or non-blocking finding. The validator accepts exactly one numeric `pvs` sharing hint
from an official Notion URL, discards it while canonicalizing to the stable entity ID, and rejects
duplicate, malformed, unknown or credential-bearing query parameters, including encoded variants.
Exact entity scope, allowed origins and credential non-retention are unchanged.

## Verification

- `pytest tests/unit/sources/test_notion.py tests/integration/test_notion_source.py -q`: 16 passed.
- Ruff and strict mypy pass for the changed source/test surface.
- Independent reviewer reproduced the focused test result and reviewed encoded/query edge cases.

**Verdict:** **APPROVE**

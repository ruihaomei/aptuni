# Review 87 — Beta Day-1 activation and retrieval fixes, re-review

- **Responds to:** `86-beta-day1-activation-fixes-review.md` (verdict BLOCK: B1 relay failure, B2
  mixed-script keyword split).
- **Scope:** the uncommitted remediation in the working tree: `retrieval/lexical.py`
  (`_KEYWORDS`, `_keyword_groups`), `application/activation.py` (`status`), `mcp/server.py`
  (`aptuni_activation_status` under `authorization_guard`), the new and extended tests, the
  ADR-0004 and ADR-0025 amendments, KI-018, and the STATE/HANDOFF current-position blocks. The
  untracked `.agents/skills/` directory and the Chinese-named `.txt` file were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** temporary Vaults and projections under the session scratchpad only; the live Vault
  was not touched. No source or test file was modified by the reviewer.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest -q` | exit 0; 1119 passed, 3 skipped (optional mem0/ollama runtimes) |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 119 source files |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true`; retrieval dev FPR 0.0, recall@5 0.992, MRR 1.0; holdout FPR 0.0, recall@5 1.0, MRR 1.0 |
| `python3.13 tools/check_relay.py` | passes after this review is registered and the manifest lines are refreshed (see below) |

## Re-verification of Review 86 findings

| Finding | Status | Evidence |
|---|---|---|
| B1 relay failure | **Resolved** | ADR-0025 now ends with a single newline; the relay EOF error is gone. |
| B2 mixed-script keyword split | **Resolved** | `_KEYWORDS` (`[a-zA-Z0-9㐀-䶿一-鿿]+`) separates keywords only on whitespace and punctuation. Probe: `Python数据分析` → `fallback_expression` is `None` and returns `[]` against `自学 Python 编程。`. `职业规划、自学` and `职业规划 自学 研究生` still fall back to whole keywords; `金融危机` and `金融危机 攻略` stay empty. New regressions: `fallback_expression("Python数据分析") is None` and `projection.search("Python机器学习") == []`; I checked that the latter would fail under the Review 86 code. The ADR-0004 amendment now states the separator rule and names Review 86 B2. |
| N1 two-word phrases | **Documented** | ADR-0004 amendment and KI-018 record the trade-off (`machine translation` → a machine-learning note) and defer a phrase rule to real trials. |
| N2 status not total | **Resolved** | `status()` treats an `AptuniError` from the grant provider as no access, and the tool runs inside `authorization_guard()`. Probe with a real `AdapterManager` grant, `authorization_lock` and `revoke`: status returns `mode: off, granted_modules: [], memory_proposals: not_granted`; a later `aptuni_propose_memory` still fails closed with the bare `adapter_grant_not_found`. Regression: `test_activation_status_survives_a_revoked_grant`. |
| N3/N4 privacy and ADR-0025 | **Unchanged, still hold** | No new raise sites; the guided codes still carry only fixed text and module/scope names; OFF still captures nothing; nothing widens a grant. |
| N5 contract surface | Open, non-blocking | As in Review 86: optionally name the `code: message` refusal form in ADR-0005. |
| N6 cosmetic | **Resolved** | The extra blank line in `test_retrieval.py` is gone. |

## New notes

1. **NON-BLOCKING — Joined terms count as separate keywords.** Because every non-alphanumeric,
   non-CJK character separates keywords, `Fine-Gray` becomes `"fine" OR "gray"` and `C++ 编程`
   becomes `"c" OR "编程"`. This is the same trade-off as N1 (the precise all-term path still runs
   first and ranks first, and the frozen `Fine-Gray` positive is unaffected). Consider treating `-`,
   `+`, `.` and `#` inside a token as joiners if real trials show noise; record it under KI-018.
2. **NON-BLOCKING — `authorization_guard` in status may raise `OSError`.** If the developer
   authorization lock finds unsafe state it raises `OSError("developer_authorization_state_unsafe")`,
   which the status tool now surfaces as a generic tool error. This matches every other guarded
   tool and leaks nothing; noted only because status is otherwise total.

## Summary

Both blocking findings are fixed with regressions, the frozen evaluation is unchanged with 0.0
false positives on dev and holdout, and the revoked-grant status path is total and still fails
closed for personal surfaces. The remaining notes are recall/precision trade-offs already tracked
in KI-018 and a documentation suggestion.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

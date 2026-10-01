# Review 86 — Beta Day-1 activation and retrieval fixes (uncommitted working tree)

- **Scope:** the uncommitted `git diff` on top of `1a357c5` plus the untracked
  `tests/integration/test_activation_guidance.py`: ADR-0004 and ADR-0025 2026-10-01 amendments,
  `retrieval/lexical.py` (`fallback_expression`, `_keyword_groups`), `application/errors.py`
  (`module_denied`), `application/activation.py` (`status`, `require_proposal_session`),
  `application/service.py`, `application/memory_commands.py`, `mcp/server.py` (`_tool_error`),
  the generated Full skill text in `adapters/manager.py`, the updated tests and the three
  `BETA_DOGFOODING.md` rows. The untracked `.agents/skills/` directory and the untracked
  Chinese-named `.txt` file are unrelated user files and were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** scratch projections and MCP servers under the session scratchpad with temporary Vaults
  only; the live Vault was not touched. No source or test file was modified.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest -q` | exit 0; 1118 passed, 3 skipped (optional mem0/ollama runtimes) |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 119 source files |
| `python3.13 tools/check_relay.py` | **FAILED**: `extra blank line at EOF in docs/dev/DECISIONS/ADR-0025-explicit-agent-activation.md` (see B1) |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true`; retrieval dev FPR 0.0, recall@5 0.992, MRR 1.0 (58 queries, 7 negative); holdout FPR 0.0, recall@5 1.0, MRR 1.0 (15 queries, 1 negative) |
| Frozen query audit (`spikes/s03_fts/frozen/queries.jsonl`) | 28 of 73 queries now reach the new keyword-group fallback branch; the two English negatives that do ("quantum computing", "mountain climbing") share no word with the corpus, so FPR 0.0 does not measure partial-overlap phrases (see N1) |

## Probes

| Probe (scratch projection) | Result |
|---|---|
| `Python数据分析` against `自学 Python 编程。` | Before: `[]` (precise path empty, no fallback). Now: returns the Python-programming record via `"python" OR (数据 AND … 数据分析)` (B2) |
| `金融危机`, `金融危机 攻略`, `猫猫`, `learning learning`, `学习 学习` | No fallback or no hit; the 2026-09-20 regression holds |
| `machine translation`, `deep sea` against `Studied machine learning and deep learning.` | Each returns the machine/deep-learning record (N1) |
| `"x" OR y`, `a"b c(d)`, `NOT near`, `AND OR` | Expression contains only quoted `[a-z0-9]+`/CJK lexemes; operators and parentheses are generated, never taken from caller text; stopword-only input yields `None` |
| 1000-char random CJK run + ` 金融`; 300 ASCII keywords | No FTS5 error; the long group simply fails and `金融` matches |
| Single-char CJK keywords (`猫 狗`) | `"猫" OR "狗"`; no hit on `喜欢猫。` because single characters are only indexed as standalone segments (unchanged behaviour, no FP) |
| `aptuni_activation_status` when the grant provider raises `adapter_grant_not_found` (revoked grant) | Unhandled: `UnexpectedToolError: Error executing tool aptuni_activation_status`; before this change it returned the mode (N2). No message content leaks |
| Whitespace/punctuation-token grouping prototype (scratch monkeypatch of `fallback_expression`) | `Python数据分析` → `None`; `职业规划 自学 研究生` unchanged; frozen eval identical (dev FPR 0.0, recall@5 0.992, MRR 1.0; holdout 1.0/1.0/0.0) |

## Findings

### Blocking

1. **B1 — BLOCKING (milestone exit): the required relay check fails.**
   `docs/dev/DECISIONS/ADR-0025-explicit-agent-activation.md` ends with `\n\n`;
   `python3.13 tools/check_relay.py` reports `extra blank line at EOF` and exits non-zero. AGENTS.md
   requires the checks to pass before a checkpoint. Fix: drop the trailing blank line. After this
   review is registered, the `Review status manifest:` line in `docs/dev/STATE.md` and
   `docs/dev/HANDOFF.md` must also be refreshed or the relay check will report it stale.

2. **B2 — BLOCKING (correctness/contract): a compact mixed-script keyword degrades to a fragment,
   contradicting the amendment's stated invariant.**
   `src/aptuni/retrieval/lexical.py:74-83` builds keyword groups from `_SEGMENTS`, which splits on
   script boundaries, not on keyword boundaries. A single compact keyword such as `Python数据分析`
   (no space, a common way to write the term in Chinese notes) therefore becomes two "keywords" and
   falls back to `"python" OR (数据分析 lexemes)`. On a Vault holding only `自学 Python 编程。` the query
   previously returned nothing and now returns that record, i.e. exactly the false-positive class the
   2026-09-20 gate was introduced to stop. Both the ADR-0004 2026-10-01 amendment ("A compact single
   keyword … therefore still never degrades to a fragment") and the `fallback_expression` docstring
   claim this cannot happen. Fix (small): derive keyword groups from whitespace/punctuation-delimited
   tokens of the normalized query (for example `[^\s,，、;；/|]+`) and take `cjk_lexemes` of each token,
   so a mixed-script token is one all-lexeme `AND` group; add `fallback_expression("Python数据分析") is
   None` and a projection-level negative. The scratch prototype of this change leaves the frozen
   evaluation identical and keeps the Day-1 case (`职业规划 自学 研究生`) working.

### Non-blocking

1. **N1 — Two-word English phrases now take the OR fallback.** `machine translation` and `deep sea`
   return a `machine learning` / `deep learning` record. This follows from the amendment's
   definition (two keywords), is the accepted recall-over-precision trade-off for Agent keyword
   lists, and the 25% relative floor cannot filter a lone weak hit (the KI-018 data point of
   2026-09-25). The frozen negatives do not contain partial-overlap phrases, so the 0.0 FPR is not
   evidence either way. Recommend: say explicitly in the ADR-0004 amendment that space-separated
   English phrases are treated as keyword lists, add the case to KI-018, and include partial-overlap
   negatives in the next dogfood judgment set before any quality claim.

2. **N2 — `aptuni_activation_status` is no longer total.** `AgentActivation.status()` now calls
   `self.access()`, which re-reads the grant; after a revoke (or an unreadable grant file) the tool
   raises an uncaught `AptuniError` and the host sees a generic `Error executing tool …`. Nothing
   leaks, and revocation still fails closed, but an Agent can no longer inspect the mode in that state
   and the read happens outside `authorization_guard()`. Recommend catching `AptuniError` there (return
   `granted_modules: []`, `memory_proposals: "not_granted"`, or raise `_tool_error`) and adding a
   revoked-grant status test.

3. **N3 — Refusal messages: verified content-free.** Every raise site of the three guided codes in
   `src/` was enumerated (`grep`): `service._authorize_host` (`mcp_scope_denied` fixed text;
   `module_denied`), `memory_commands.propose_from_host` (fixed text; `module_denied`) and
   `activation.py` (four fixed `aptuni_activation_required`/`mcp_scope_denied` strings). `module_denied`
   interpolates only requested module names, which on every MCP path are pydantic-validated `Module`
   literals, and granted module names from the Aptuni-owned grant, which `AdapterManager.plan`
   validates against `MODULES`. No query, statement, principal or record text reaches a message. All
   other codes stay bare through `_tool_error`. `api/v1/client.py` already forwarded `error.message`
   in-process before this change; the only difference there is the richer module list. A hand-edited
   grant file could echo arbitrary module strings, but that is owner-local state, not personal content.

4. **N4 — ADR-0025 boundaries hold.** OFF: `require_proposal_session` raises on both branches before
   `propose_from_host`, so OFF captures nothing (`test_off_denies_every_personal_mcp_surface` still
   passes with the scope granted; the new guidance test covers OFF without the scope). Task scope:
   `activate` is unchanged and `status` only reads state. Grants: nothing writes to the grant or
   widens `access`; `propose_from_host` re-checks scope and module live. Scope-before-session ordering
   tells an OFF Agent whether the grant has `memory.propose`; that is grant metadata, which the status
   tool now reports anyway, not personal content. Status reporting `granted_modules` while OFF
   discloses only grant configuration and stays within "inspected without personal content".

5. **N5 — Contract surface.** No user-facing doc (README, guides, `docs/` outside the ADRs and
   reviews) documents the `aptuni_activation_status` shape; the change is additive under
   `schema_version: 1`, and existing hosts that read `mode` are unaffected. ToolError text changes from
   the bare code to `code: message` for three codes; hosts that match the code as a substring (as all
   tests and `docs/dev/COMPATIBILITY.md` do) still work. The ADR-0025 amendment is sufficient; consider
   one sentence in ADR-0005 naming the `code: message` form as the stable refusal shape so a later
   change does not drift silently.

6. **N6 — Cosmetic.** `tests/integration/test_retrieval.py` has three blank lines before the new test.
   The generated skill text now tells every intent (not only Full) to call `aptuni_activation_status`
   first and to query with keywords; that is consistent with the amendment, but existing bundles only
   pick it up when regenerated, which the amendment already says.

## Summary

The refusal and status changes are privacy-safe and keep ADR-0025's boundaries; the FTS5 expression
is safe against injection, empty groups and duplicates, and the frozen evaluation still records 0.0
false positives. Two small issues must be fixed before the checkpoint: the relay check fails on the
ADR-0025 EOF (B1), and the keyword-group fallback splits compact mixed-script keywords such as
`Python数据分析`, contradicting the amendment's own invariant (B2). Both fixes are local and need only a
focused re-review.

**Verdict:** **BLOCK**

# Review 114 — Candidate inventory for unnamed selection (ADR-0032)

- **Date:** 2026-10-09
- **Scope:** commit `05e89de`: `src/aptuni/application/candidates.py` (new),
  `AgentActivation.session_candidates`, `aptuni_search_context` `mode`/`categories`/`candidates`,
  `SELECTION_GUIDANCE` in the generated Full skill, ADR-0032 and the new unit/integration tests.
- **Policy:** AGENTS.md: block only for correctness, security/privacy, contract or milestone-exit
  defects. High-risk categories in scope: MCP contract, privacy, host confinement.
- **Method:** independent code-reviewer agent. Read the diff and ADR-0005/0025/0030/0031/0032. Ran
  the focused tests. Probed with `.venv/bin/python` against temporary workspaces only: no owner
  Vault, state or private trace was read. Probes covered both server modes, task-scoped Full, grant
  scope loss mid-session, hidden modules, source removal, deleted files, stale and unknown IDs,
  credential paths, 3,000-document budgets and 53,000-record build time.

## Blocking findings

None.

## Confirmed

1. Inventory and evidence modes require an explicitly enabled Full session in both server modes.
   A task-scoped Full does not enable them, and there is no OFF→Full path. `context.read` and
   `evidence.read` plus the granted modules are checked on every call, and losing a scope
   mid-session refuses.
2. Only current, exposable Evidence in the requested modules contributes rows or records. Hidden
   modules, removed sources and deleted files disappear from the inventory, and their IDs return
   nothing.
3. Stale and unknown IDs return identical responses apart from `vault_seq`: no existence oracle.
4. Credential-bearing records are excluded before grouping. Every row is re-checked, and the
   `pack_units` last-line guard remains. Inventory units carry no `canonical_ids` or `source_id`.
5. Bounds hold: 3,000 documents at 100,000 units gave 1,504 rows, truncated, in 0.5 s. The build
   over 53,000 records took 0.7 s.
6. Default `mode="search"` behaviour is unchanged. Empty `categories`/`candidates` lists are rejected
   by the schema.

## Non-blocking notes (disposition)

- **N1** A joined unit could match the Markdown-table credential rule across rows, so the
  last-line guard dropped the whole category with `truncated=false`. **Fixed before the
  confirmation:** rows are guarded as they accumulate, a skipped row sets `truncated`, and a
  regression test covers it.
- **N2** ADR item 7 said Profile/Memory skills too, while the code and tests are Full-only.
  Subjects with the same title in another notebook were dropped instead of merged, and the
  docstring said "never categories". **Fixed:** the ADR wording is corrected, same-title roots now
  merge their Evidence (test), and the docstring and ADR state that any omission sets `truncated`.
- **N3** The tool description did not explain the ignored `query`/`include_evidence`/`limit` in the
  new modes. **Fixed** in the description. Bare `invalid_context` errors are left as they are:
  safe, and the guidance plus schema constrain calls.
- **N4** Candidate IDs are unsalted: stable across hosts of one owner, and low-entropy keys can be
  confirmed offline by someone who already guesses them. **Documented** in ADR-0032 item 2; a
  per-Vault salt is a follow-up if cross-host linkability matters.
- **N5** Missing adversarial tests. **Added:** server without required activation, task-scoped
  Full, stale vs unknown IDs, credentials in evidence mode, multi-category budget.
- **N6** Installed adapter bundles keep the old Full skill until regenerated. **Recorded in
  HANDOFF.** The production-path confirmation renders fresh skills into scratch and leaves the
  owner's installed bundles untouched.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

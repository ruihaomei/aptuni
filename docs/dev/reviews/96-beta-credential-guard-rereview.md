# Review 96 — Credential guard re-review: Review 95 remediation (ADR-0031 amendment)

- **Scope:** commit `6660ae2` ("fix(privacy): close Review 95 credential-history purge finding")
  against its parent `606e722`: `src/aptuni/application/privacy.py` (`credential_history_scope`
  limited to source Evidence chains, new `validate_remaining` in `create_purge_preview`,
  `refuse_pending_sources` exempting removed sources), `src/aptuni/policy/secrets.py` (`bare` label
  branch, `_label_columns`, header = row before each separator, one-token table values), the new
  tests, and ADR-0031 Amendment items 1 and 6. Narrow re-review of Review 95 B1-new plus the notes the
  commit claims to close (N1, N2, N3, N4). Later commits `a2978fd`/`6a89749` (Agent concept
  guidance, handoff) do not touch the reviewed files and were not reviewed; the untracked
  `.agents/skills/` directory and the untracked Chinese-named `.txt` file are unrelated.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in `/private/tmp/claude-501/rr96/` against temporary Vaults created
  there, with synthetic secret values only; a `git archive` of `606e722` was unpacked there for
  side-by-side comparison. The owner's Vault and `~/Library/Application Support/aptuni` were not
  read. No source or test file was modified (probes monkeypatched in-process only).

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest` | exit 0; 1261 passed, 3 skipped, 62 subtests passed (tree at `6a89749`; reviewed files identical to `6660ae2`) |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 122 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |

## Probes

| Probe | Result |
|---|---|
| Owner CLI memory (auto-promoted) holding a credential, **forgotten**, then `--credential-history` | Flagged records are observation, candidate, memory; preview → `nothing_to_purge`; no pending preview and no intent written; `remember` still works. Exact-id purge of all doctor-listed ids (observation + candidate + memory) erases 5 records (incl. promote and revoke events); 0 holders; `doctor` ok; writes work |
| Same memory, active | `nothing_to_purge` (correct) |
| Legacy host proposal (pre-guard, monkeypatched): pending; rejected; accepted; accepted then forgotten | `--credential-history` → `nothing_to_purge` in every state, nothing written. Exact-id purge of the doctor-listed ids erases the rest of each chain (rejected: observation + candidate + event; accepted-then-forgotten: a memory-only purge completes because a host-accepted memory has no `policy_auto` promote event, then observation + candidate + accept event), 0 holders; `doctor` ok |
| Owner-typed Fact: current; retracted; corrected to a clean successor; successor retracted | `--credential-history` → `nothing_to_purge` in all four (memories and owner Facts are now out of its scope, as ADR item 6 says). Exact-id purge of the original Fact takes the retraction (2) or the whole 3-version chain; 0 holders; `doctor` ok |
| Folder Evidence chain withdrawn **and** a forgotten credential memory in the same Vault | Preview selects only the 2 Evidence records; `PURGE` → `complete_managed_external_action_needed`; the memory chain is left untouched (3 holders, all memory-side); `doctor` ok; writes and sync work |
| A kept owner Fact planted to cite the withdrawn credential Evidence (synthetic, committed through the service) | Preview → `purge_scope_invalid` with a content-free message; no pending preview, no intent; writes still work. `validate_remaining` checks the kept set **without** `_unlink`, so any dangling link fails; when it passes, `_purge_locked`'s unlink is a no-op and its `validate()` sees the same set, so a validated preview cannot fail canonically at confirm (the `vault_seq` check pins the set) |
| MarginNote studied card titled with a credential, pre-guard derived Profile Fact → sweep → `--credential-history` → clean edit → credential edit | Preview selects 4 Evidence + 2 derived Facts + 2 promotion events; purge complete, 0 holders; clean edit re-derives (5 Facts); renewed credential withheld (2) with no record written; `doctor` ok at every step |
| Removed source with a stale pending state + an active source | Removed-only pending: preview proceeds (4 records). Active source pending: preview **and** confirm refuse `source_sync_pending`, confirm before any intent is written. After the active pending clears, purge completes, `doctor` ok, the active source syncs. The removed source's stale `.pending.json` stays on disk (N3) |
| `credential_kinds` on 27 synthetic positive and 33 negative layouts, raw and whitespace-flattened (120 checks), at `6660ae2` and `606e722` | `6660ae2`: 1 miss (a separator-less credential table following another table, flattened only), 2 false positives (`token: SentencePiece`; vocabulary table `\| Token \| … \|` with `internationalization`) — both FPs carried over from Review 95 N2. `606e722`: 15 misses, 14 false positives on the same set. No case detected at the parent is missed at `6660ae2` in this set |
| Review 95 N1: `client_secret`, `access_token`, `refresh_token`, `auth_token`, `GITHUB_TOKEN`, `DB_SECRET`, `session_token` with 8–10-character values, and a `client_secret` table column | All detected (all missed at the parent); bare `token:`/`secret:` under 12 characters stay clean |
| Review 95 N2: prose cells under a credential header (`rotated 2025`, `12+ chars`, `signs session cookies`, `*see vault*`), later unrelated tables in the same flattened note (same and different width) | All clean, raw and flat (all flagged at the parent) |
| Extra table edges | Detected: header with text before it, label row then separator, key/value rows (`\| password \| v \|`, `\| **Password** \| v \|`), empty data row, single-column table. Newly missed by the one-token rule (detected at the parent): `` `Zq1999abc!` rotated `` and `Zq1999 abc!` in a credential column (N2) |
| Worst case, 300k–620k characters (5000-column header × rows, 30k rows, `\| \|`/`\|\|`/`\|---\|` runs, 40k label cells, `password:**` chains, `a_a_a_a_token` chains, alternating header/separator pairs) | Linear; ≤ 0.15 s each, raw and flat |

## Blocking findings

None for this commit.

## Non-blocking notes

- **N1 — Pre-existing: exact-id purge of an auto-promoted CLI memory by its memory id commits an
  intent that cannot apply.** Not introduced by `6660ae2` (reproduced identically at `606e722` with
  a credential-free memory), but ADR-0031 item 6 now sends memories to "the exact-id purge, whose
  closure already handles their lifecycle", and that claim is only true when the owner passes the
  observation or candidate id. `_required_by_selected` does not pull the candidate in from the
  memory, so for any CLI memory (ADR-0018 auto-promotion puts the `policy_auto` promote event on the
  candidate) `aptuni privacy purge preview <memory_id>` selects the memory (and its own events);
  `PURGE` returns `incomplete_retryable` (`candidate promotion must admit exactly one root memory`),
  the intent stays, and every write fails `privacy_action_in_progress` until `cancel` (the message
  does say "retry or cancel"). Active and forgotten memories alike; purging by candidate or
  observation id works. Doctor lists all three ids, so purging what doctor lists succeeds. Fix in its
  own slice (privacy/deletion is high-risk, so with review): run the same unlink-then-validate check
  at preview for every scope, and/or close the memory upward to its candidate and observation when
  the candidate admitted only that memory; add a confirm-level test (the existing
  `test_a_purge_scope_includes_accept_and_pin_events_on_the_memory` checks only the preview scope).
  Meanwhile correct the ADR sentence to "purge the ids `doctor` lists" and make the `nothing_to_purge`
  message for `--credential-history` say that memory and Fact history uses the exact-id purge rather
  than "leave through a source sync".
- **N2 — One-token table values drop some real layouts.** Requiring `len(value.split()) == 1`
  removes the prose false positives but also misses `` `Zq1999abc!` rotated `` and a mixed-case
  value with a space. Judging the **first** token of the cell gives the same protection against
  `rotated 2025`, `12+ chars` and `signs session cookies` (first tokens are not secret-shaped) and
  keeps the first two. Add "a table cell with trailing words" to the ADR residuals if it stays.
- **N3 — Stale pending state of a removed source is kept.** The refusal exemption is correct, but a
  `.pending.json` left by an interrupted pre-guard sync can hold delta operations with the old text,
  and neither `--credential-history` nor `doctor` covers it. Listing `source_state:<id>:pending`
  for removed sources among the managed copies of a credential-history purge would close it;
  otherwise state it as a residual.
- **N4 — Residuals still open from Review 95 N2/N4:** `token: SentencePiece` and a `| Token |`
  vocabulary column with a ≥ 12-character word are flagged (withheld in sync); a separator-less
  credential table that follows another table is missed once flattened. ADR-0031 lists the
  outer-pipe and empty-cell residuals; add these two.
- **N5 — `validate_remaining` is all-or-nothing.** One chain whose removal would orphan a kept
  record refuses the whole credential-history preview, and the message does not say which. Dropping
  only the offending candidates (validate per candidate closure, then the union) would keep the
  other chains purgeable.

## Verified as correct

- **Review 95 B1-new closed.** `credential_history_scope` considers only `evidence` candidates and
  accepts one only when its full closure is Evidence, review events and Facts with none current
  (current = `current_facts()` plus non-superseded, non-retraction Evidence, independent of
  exposure). Memory chains (CLI memory forgotten, host proposal rejected, accepted, accepted then
  forgotten) and owner Facts are never selected, so the half-chain purge of Review 95 cannot recur;
  Evidence-derived Profile Facts and their promotion events are still erased and re-derived after a
  clean edit. `validate_remaining` runs in `create_purge_preview` before the pending preview is
  written, so a scope that would leave the Vault inconsistent is refused with `purge_scope_invalid`
  and no intent; confirm's `vault_seq` check guarantees the validated set is the one purged. A
  test pins the forgotten-memory case and that writes still work.
- **Review 95 N3 (refusal) closed.** `refuse_pending_sources` skips sources in
  `removed_source_ids()`; an active source with a pending state is still refused at preview and at
  confirm, before the intent is written; both paths call the same function.
- **Review 95 N1 and N2 closed as specified.** Qualified labels no longer need 12 characters; table
  headers are re-read at each separator, so later tables start afresh; prose cells are clean.
  Detection remains linear. ADR-0031 item 1 and the residual list match the code (apart from N2/N4).

## Verdict rationale

The Review 95 blocker is closed: `--credential-history` now selects only source Evidence chains whose
closure is fully withdrawn, leaves memory chains and owner Facts to the exact-id purge, and validates
the remaining Vault at preview so a failing scope never commits an intent. The removed-source
exemption and the detector changes behave as the ADR states, with strictly fewer misses and false
positives than the parent on the probe set and linear runtime. The one wedge still reachable (N1)
lives in the pre-existing ADR-0010 exact-id purge of an auto-promoted memory by its memory id, which
this commit did not change; it is recoverable with `cancel` and avoidable by purging the ids `doctor`
lists, but it should be fixed in its own reviewed slice, and the ADR sentence pointing owners there
should be corrected meanwhile.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

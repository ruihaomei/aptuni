# Pitfalls already hit

| Pitfall | What to do instead |
|---|---|
| Bare `python3` resolves to Anaconda 3.12 on the maintainer's Mac | Use `/opt/homebrew/bin/python3.13` or `.tools/bin/uv run` |
| zsh `set -- $spec` does not word-split | Run spec loops under `/bin/bash -c` |
| Claude Code writes `.claude/logs/` into the working directory | Ignored by git and by the relay checker; never commit it |
| `--ignore-user-config` in Codex also drops the repository trust entry, so project `.codex/` is skipped | Use a temporary `CODEX_HOME` with one explicit trust entry |
| `/tmp` is writable inside default host sandboxes | Use `/Users/Shared/...` for write canaries |
| Model replies sometimes omit the probe JSON even when the tool ran | Treat as a failed run and retry; never count it as evidence |
| Vendor quota/429 looks like a tool failure | The canary runner labels it `host_blocked_external` |
| `git filter-branch --all` also rewrites `refs/stash` and leaves Codex `refs/codex/turn-diffs/*` holding old blobs | Drop stashes, delete stale checkpoint refs, expire reflogs, `gc --prune=now`, then scan every blob |
| Slice-based string rewrites can match the wrong occurrence and truncate a file | Use exact-match Edit with uniqueness checks |
| Rechecking policy only after retrieval still leaves a race during response composition | Recheck the Vault sequence after hydration, layering, and budget packing; discard and retry the whole response on change |
| MarginNote 4 `BackupSnapshots_v4.sqlite` snapshots are incremental (only changed notes after the first; `note_count` holds the true total). Treating each as a full tree invents thousands of deletions | Overlay deltas in order and evaluate only while the overlay size equals `note_count` (`spikes/s05b_marginnote/replay.py`) |
| Reading another app's container (`~/Library/Containers/...`) blocks on a macOS privacy prompt; the process sleeps with ~0 CPU | Ask the maintainer to approve the prompt; do not busy-retry |
| All-terms FTS queries return nothing for natural task requests | Keep all-terms first, then a ranked any-term fallback (ADR-0004 amendment 2026-09-19) |
| Building evidence from `ancestor_path` or unknown OPML attributes copies the whole mind map into the Vault | Minimize the MarginNote locator before shipping ingest (full-content retention, ADR-0006) |
| A purge that freezes an exact copy set silently drifts: a content-bearing derived copy created *after* the preview is outside the frozen set, so a "complete" receipt can leave purged text behind | Make invalidation of derived projections always-run rather than preview-conditional (Review 30 R1) |
| Restoring by clearing live replay state before publishing the replacement destroys recovery state on any later failure | Stage the replacement and a durable journal first; recovery then finishes one unambiguous generation switch (Review 30 R2) |
| Guarding only the writer you happened to think of (source sync) leaves a frozen purge scope wedgeable by any other canonical writer, permanently disabling deletion | Guard the single shared commit seam, map an unsatisfiable scope to a retryable terminal state, and always ship an owner cancel path (Review 31 F1) |
| Adding a field to an on-disk manifest silently breaks artifacts the previous version wrote -- here a purged Vault failed `doctor` and its backup became unrestorable | Bump the format, keep the old one readable, migrate on open, and amend the ADR in the same change (Review 31 F2) |
| Printing a user-controlled source path raw lets a crafted folder name forge adjacent rows on the surface the owner reads to decide what to delete | Route every owner-facing render of a source-controlled name through one bounded escaped/delimited helper (Review 30 R3, Review 31 N2) |
| Pinning application dependencies does not pin isolated PEP 517 build code, and a clean-wheel smoke can silently resolve a different runtime set than the one audited | Lock build/audit tools in a dedicated group, seed them before `--no-build-isolation`, build offline, then install the audited hash-locked runtime set before installing the wheel `--no-deps` (Review 40) |
| Claude file permission rules that look absolute with one leading slash are settings-relative; path-scoped `Write(path)` rules are not consulted | Generate filesystem-root rules with `Read(//...)` and `Edit(//...)`, test the exact serialized rules, and keep absent tool attempts as `unverified` rather than inferring a denial (Slice 17) |
| A broad any-term fallback can pass hand-picked natural requests while violating a precommitted negative-query gate, and a failed CI metric can lose its own report if upload runs only on success | Score production code against the frozen corpus, gate fallback on actual task-language removal, and upload a written failure manifest from one contract-tested `always()` step (Reviews 42–44) |
| An agent skill can promise a deterministic no-fetch audit while `uv run` silently synchronizes its environment first | Require a prepared locked environment and use `uv run --no-sync`; make the fixture smoke execute that exact command shape (Reviews 45–46) |
| Mem0 2.0.20 interaction inference retains raw messages, while `Memory.delete()` can leave marker bytes in Qdrant/history | Populate only accepted canonical records with `infer=False`; for privacy deletion close and remove the whole managed projection root, then rebuild active records from the Vault (S10, Review 52) |
| A full canonical check can reject corruption that incremental commit validation accidentally admits when the new record is only one side of a linked transition | Validate global uniqueness and target type from every newly appended transition event, not only from the linked content record; add a regression that the bad commit itself fails and `doctor` remains green (Review 59) |
| Treating a missing exact Notion MCP root as deletion, or coercing malformed completeness metadata, can silently withdraw or ingest incomplete Evidence | MCP absence is not proof of remote deletion: retain prior Evidence until explicit unlink/purge, require exact provenance/completeness types, and test the real SDK result shape plus the exact identity/fetch call sequence (ADR-0021, Review 60) |
| Taking the source-operation lock before a fresh process opens the Vault can deadlock recovery; deleting a managed directory before validating every child can leave a partial failed reset | Open/recover before the shared lock, preflight the complete bounded directory before unlinking, and exercise the CLI through a fresh service instance plus contaminated-state fixtures (ADR-0022, Review 61) |
| Checking only a destination leaf with `O_NOFOLLOW` still lets an ancestor swap redirect installation, while checking only ancestors can return success after the leaf itself moved | Open the resolved path component-by-component from the filesystem root, retain every parent descriptor and child inode, perform writes relative to pinned descriptors, and revalidate the full chain plus final target before success (ADR-0023, Review 62) |
| Treating a manifest preview as consumed only after grant publication lets concurrent or interrupted apply create hidden duplicate authority; checking revocation only before a read also leaks through an in-flight race | Bind one deterministic grant generation to each preview, serialize calls/apply/cancel/revoke/privacy cleanup under one no-follow cross-process lock, reconcile published grants on cancel, and revalidate persisted authority before returning (ADR-0024, Review 63) |
| Treating every official Notion URL query as either trustworthy or invalid breaks real `app.notion.com` activation: page creation appends a benign `pvs` hint, while arbitrary query fields may carry credentials or ambiguity | Allow exactly one bounded numeric `pvs` hint, discard it during stable-ID canonicalization, reject every other/duplicate/malformed query, and keep Aptuni's Keychain OAuth boundary distinct from an agent host's Notion connector (ADR-0021 amendment, Review 64) |
| Sorting a mixed Context response by disclosure layer (all L3 before L4) silently discards retrieval rank, so an explicitly requested, better-matching Evidence unit is the one a budget truncates | Treat L0–L4 as what was requested, not a priority: keep the permission-filtered retrieval rank across layers and report `layers` canonically; measure each context mode separately in dogfooding (ADR-0005/ADR-0022 amendments, Review 66) |
| MCP SDK 2.2.0 reloads OAuth tokens without their expiry; a stale access token then looks valid, its 401 triggers a full browser authorization and the stored refresh token is never used | Persist an absolute expiry (with a small margin) beside the tokens in the same Keychain item and restore it in a pinned-provider `_initialize` override from one read; a falsy expiry means "unknown = valid" to the SDK, so "due" must be a positive past time (ADR-0021 amendment, Review 67) |
| A complete source pipeline can accumulate tens of thousands of valid Evidence records while leaving Profile empty if no explicit policy bridge consumes them | Keep providers Evidence-only, but run a deterministic canonical Evidence→Profile policy after admission; require an exact strong authority dimension, make the result active before retrospective review, and let Profile activation retrieve exposure Evidence without turning mentions into durable claims (ADR-0028) |
| Deriving per-item canonical records by rebuilding a growing `RecordSet` (and rescanning `current_facts()`/`ids()`) for each Evidence item is O(N²): fine on fixtures, minutes at the real 27k-Evidence Vault; per-target scans inside validation repeat it at commit and `doctor` | Build supersession, owner-decision, grant and promotion indexes once per snapshot, derive the batch in one pass against the pre-delta view, commit once, and keep a 25k-scale regression with a stated envelope (Review 82 B5) |
| Resolving a derived record's predecessor from a view that already contains the new source version finds nothing, so the replacement is written as a fresh assertion and owner decisions made one generation earlier stop applying | Resolve lineage against the pre-delta snapshot and walk the whole source-subject lineage; treat an owner reject/edit anywhere in it as permanent, and make the invariant recompute the exact expected predecessor (Review 82 B1/B2) |

## Knowledge model on a real MarginNote library (ADR-0029 rehearsal, 2026-09-30)

- A real library's most frequent card titles are not topics: `(image)` (MarginNote's placeholder for
  untitled image cards) and role headings such as `Proof`, `Summary`, `EXAMPLE 2`, `总结`. Aggregating
  by title merged thousands of unrelated cards. Such a card is about its parent; resolve headings to
  the parent (curated list plus "an unregistered title under ≥5 different parents").
- NFKC + casefold keeps Latin and CJK in one `\w` token (`xgboost视频笔记`), so an alias never
  matches. Split at the script boundary before tokenising.
- Legacy summaries begin with the owner's own title and notebook name, so any regex over Aptuni's
  summary must anchor on Aptuni's own segment and take the last match (Review 85 N1).
- Only ~14% of User #1's 26,415 blanket-`studied` cards were isolated one-line cards; most cards in a
  real study library do organise, collect or annotate. Expect reclassification to narrow, not gut,
  a Profile.

## Unnamed-candidate selection on lexical concept retrieval (b10 R1 trace, 2026-10-08)

- Infer the failing stage from replayed tool calls, never from the final answer. Recording the
  real `concepts`/`limit`/`max_units` and replaying them offline through the product projection,
  concept, diversify and pack code reproduced the returned sets exactly and localized the loss
  in minutes at zero model cost.
- "Choose two of my X that show Y" has no nameable concept. Quality words (Y) rarely occur in the
  records; artifact words match broadly and lose candidates to the Agent's small `limit`. Either
  way roughly a quarter to a third of eligible entities reach the packet. Guidance can move the
  loss between R1b (no match) and R1c (cutoff) but not remove it.
- A development fix found on the very cases a lead has inspected can over-fit one corpus
  region (here software repositories). Freeze fresh tasks across unlike shapes (study subjects,
  extracurriculars, cross-category) before believing it.
- Codex accounts can return `usageLimitExceeded` mid-batch; it arrives during the setup turn with
  zero model output. Predeclare a retry-once rule for zero-model upstream refusals and run
  concurrent arms so a quota cut does not hit one arm only.
- Check the module/source-kind census before blaming query or cutoff. On User #1's Vault every
  record (and every candidate) is `knowledge`; `projects` is granted but empty, so a selection
  request cannot scope to its candidate class. Scoping alone did not help, though: the packet
  (≈555 bytes per Evidence, 6–9 records per 4,000 units) and vocabulary gaps still bind.
- Units are UTF-8 bytes, not tokens. A 4,000-unit packet is a small share of a ~90k-token
  Agent session, so judge widening by recall ceiling, not by unit multiples.

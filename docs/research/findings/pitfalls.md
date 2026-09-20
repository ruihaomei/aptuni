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
| A broad any-term fallback can pass hand-picked natural requests while violating a precommitted negative-query gate, and a failed CI metric can lose its own report if upload runs only on success | Score production code against the frozen corpus, gate fallback on actual task-language removal, and upload a written failure manifest from one contract-tested `always()` step (Reviews 42–44) |
| An agent skill can promise a deterministic no-fetch audit while `uv run` silently synchronizes its environment first | Require a prepared locked environment and use `uv run --no-sync`; make the fixture smoke execute that exact command shape (Reviews 45–46) |

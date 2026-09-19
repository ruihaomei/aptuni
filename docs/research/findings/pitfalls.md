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

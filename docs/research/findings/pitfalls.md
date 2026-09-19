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

<p align="center"><img src="assets/brand/logo/aptuni-icon.svg" width="120" alt="Aptuni"></p>

<h1 align="center">Aptuni</h1>
<p align="center"><b>Context, attuned to you.</b></p>

Aptuni gives AI agents the right personal context — without giving them everything about you.
The more you use it, the better it understands what matters.

> **Status: pre-alpha.** Milestone 1 is under active development. Interfaces will change.

Documentation grows with each milestone slice; see `docs/dev/STATE.md` for the current state.

The current local-first CLI can create a Vault, record user-declared facts, control ingestion and
exposure per module, and sync minimized evidence from an explicitly approved folder:

```sh
aptuni init ~/Aptuni
aptuni remember "Prefers concise answers." --module preferences
aptuni source add-folder ~/Documents/portfolio --module projects --role portfolio
aptuni source list
aptuni sync SOURCE_ID
aptuni evidence --source SOURCE_ID
aptuni doctor
```

Folder sync currently admits UTF-8-oriented Markdown, text, and CSV files. It skips hidden files,
common secret names, symlinks, VCS/cache folders, unsupported formats, and oversized files by
default. A file mention creates only `exposure` evidence—it never claims that the user studied or
mastered the topic.

Licensed under [Apache-2.0](LICENSE).

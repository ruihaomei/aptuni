# Project Agent Contract

Build a portable personal-context framework whose open-format Profile Vault is the only source of
truth. Databases, indexes, memory engines, and graphs are rebuildable projections.

## Start every substantive task

1. Read `docs/dev/STATE.md`, `docs/dev/HANDOFF.md`, `docs/dev/reviews/STATUS.json`,
   `docs/dev/KNOWN_ISSUES.md`, relevant ADRs, and `git status`.
2. Read `PROJECT_KNOWLEDGE.md` and run the documented Research Memory status command if that file
   exists. Do not create it without maintainer confirmation.
3. Run the smallest relevant baseline check before editing.

## Invariants

- Preserve Fact history, evidence, temporal fields, provenance, review state, and stable IDs.
- Enforce `ingest_enabled` and `expose_enabled` independently; deletion is explicit.
- Raw conversations and telemetry are off by default. Never commit secrets or private source data.
- Host-assisted inference is separate from canonical storage and provider contracts.
- Do not make generated indexes or optional providers canonical.
- Do not silently change public schemas, plugin contracts, or heavy dependencies; write/revise an ADR.
- Prefer dependency/adapter use over copied upstream code; copied code requires license review.

## Working rules

- Investigate before editing; keep changes scoped; preserve unrelated user work.
- Add behavior tests before or with behavior changes. Test failure, privacy, migration, and rebuild
  paths, not only happy paths.
- Use exact, sanitized fixtures. Never infer expertise from document mention alone.
- Before handoff, run relevant checks and update `STATE.md` plus concise `HANDOFF.md`.
- Adding a review or drill report: in the same change, register it in `docs/dev/reviews/STATUS.json`
  (`kind` review|drill, `current`, `verdict`, `supersedes`), end it with one anchored
  `**Verdict:** **…**` line, and update the single `Review status manifest:` line in both STATE and
  HANDOFF. Remediation files start with a header line of the form
  ``- **Responds to:** `<report>` `` and never carry a verdict line.
- Production code is blocked until Gate 0 in `docs/dev/ROADMAP.md` passes.

## Current commands

No production toolchain exists yet. Development-relay validation is available now:

```sh
python3.13 -m unittest tests/dev/test_check_relay.py
python3.13 tools/check_relay.py
```

Use the pinned Gate 0 interpreter (`/opt/homebrew/bin/python3.13`, CPython 3.13.3); bare `python3`
may resolve to a different installation. `git diff --check` covers only tracked files; the checker's
workspace-text check covers untracked files too.

Milestone 1.1 Slice 1 will add verified install/build/lint/type/test commands.

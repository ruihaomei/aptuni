# Cold Claude Code Relay Drill Remediation

- **Date:** 2026-09-18
- **Responds to:** `11-cold-claude-relay-drill.md`
- **Status:** harness defects addressed

| Defect | Remediation |
|---|---|
| D1 new reports collide with checker | Registration is now a documented same-change step in AGENTS.md; the failure is intentional (unregistered verdicts must not be silently ignored). |
| D2/D3 stale STATE/HANDOFF | Rewritten from a fresh run; `git diff --check` caveat recorded; chat-dependent wording removed. |
| D4 missing lineage tests | Covered by execution remediation 10 (18 tests). |
| D5 finding-ID mismatch 08↔remediation | Historical; remediation 10 uses the re-review's own IDs (NF1–NF8) verbatim. |
| D6 read order | AGENTS.md read order now includes `reviews/STATUS.json` and `KNOWN_ISSUES.md`. |
| D7 interpreter | Commands pin `python3.13`; AGENTS.md explains why bare `python3` is unsafe here. |
| D8 `.claude/` host state | `.gitignore` ignores `.claude/*.lock` and `.claude/settings.local.json`; shared project settings may be added deliberately later. |
| D9 global-default precedence | CLAUDE.md states the repository contract overrides user-level Research Memory / Obsidian bootstrap defaults. |

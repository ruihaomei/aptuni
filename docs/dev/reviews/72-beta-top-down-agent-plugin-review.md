# Review 72 — Beta Top-Down Learning Agent Plugin

**Date:** 2026-09-27
**Scope:** standalone public-API-only Top-Down Learning package; Claude Code and Codex manual skill
wrappers; owner grant, live revocation and optional memory proposal boundaries; STDIO confinement;
progress integrity; clean source-checkout installation
**Reviewer:** independent agent (`code-reviewer`)

## Findings

The first review found two blockers. Caller-provided `completed_slugs` could forge a valid progress
prefix and skip a prerequisite, and the documented install was unsatisfiable while the repository
still identified itself as 0.1.0 but the plugin required the Beta API range. The MCP tools now use a
per-process HMAC-SHA256 continuation whose progress cannot be edited by the caller. Check and gap
tools no longer accept a caller-owned goal or completed list. The repository's SemVer Beta candidate
is 0.2.0b1, matching the plugin dependency, and the documented two-tool install completed in a
fresh isolated uv tool root.

The first continuation revision exposed a third blocker: a 500-character multibyte goal produced a
token larger than the check tool accepted. Signed-payload and tool-input bounds now cover the full
accepted goal domain, including JSON expansion, and a 500-CJK-character round-trip regression is
green.

The final package imports Aptuni only through `aptuni.api.v1`, declares no egress, revalidates the
exact owner grant on each public API operation, stops after live revocation, and keeps optional gap
capture quarantined and fail-closed when not granted. MCP responses omit canonical identifiers and
preference text; they expose only bounded progress plus the current teaching turn. Claude and Codex
wrappers validate independently, remain manual-only UX safeguards, and share a regression-locked
workflow body. No release-blocking findings remain.

## Verification

- Full repository gate: 830 passed, 3 optional-runtime skips and 62 subtests.
- Ruff, strict source mypy and strict standalone-plugin mypy: passed.
- Codex plugin, Codex skill and Claude plugin validators: passed.
- Fresh isolated `uv tool install` for Aptuni plus the plugin, followed by init, grant, installed
  STDIO startup and the first personalized turn: passed.

**Verdict:** **APPROVE**

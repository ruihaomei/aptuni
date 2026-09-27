# Review 74 — Beta Top-Down Learning Flagship Plugin #1

**Date:** 2026-09-27
**Scope:** ADR-0026 portable `aptuni.top-down-learning.context@1` schema and strict parser;
task-scoped retrieval and minimization; learner verification gate; stable/dynamic state; local
just-in-time progress loop; cloud export; explicit memory proposals; eight stateless MCP tools; Claude
Code and Codex manual wrappers; flagship demo contexts
**Reviewer:** independent agent (`code-reviewer`)

## Findings

The first round returned **BLOCK** on two findings. B1 (privacy): the learning-preference filter
used substring matching on generic cues ("project", "practice", "图"). Unrelated personal preferences,
such as working on projects with a therapist, therefore entered the verified context and the cloud
export. B2 (public-format correctness): the renderer accepted values its own strict parser rejected.
These were ` — ` inside Agent summaries, ` › ` in a target, and values equal to the empty-section
marker. A normal tool call could therefore write a learner file that could not be resumed.

Both were remediated test-first. Preferences are admitted only when they explicitly mention learning
or teaching, matched as whole words. Lines about health, family, money or faith are excluded. Every
`render_context` now parses its own output and refuses any mismatch. Agent text has the format's
separators neutralized on input, and direct model values that cannot round-trip are rejected. The
same round also closed several review notes and self-found issues:

- Cloud export refuses private-shaped text anywhere in the body.
- Position concepts must be unique and present in the map.
- A demonstrated-understanding proposal needs two distinct timestamps and is worded as recorded by
  the teaching Agent.
- Lone surrogates, U+0085, U+2028 and C1 controls fail as invalid context.
- Cloud guidance and the cloud teaching contract are regenerated after progress, revision and export.
- The package root no longer imports Aptuni, so the portable modules work without Aptuni installed.

The re-review confirmed both fixes against the original reproducers and near-miss variants. It
raised no new blockers. Its remaining notes went to BACKLOG: residual keyword-filter false positives
(since narrowed further), forged demonstrations with distinct timestamps (still quarantined) and
unspaced separators (rejected with a clear error). Retrieval acting as an evidence-term oracle is
documented in the plugin README. Verification remains workflow integrity, not authentication, as in
ADR-0025.

## Verification

- Full repository suite: 888 passed, 3 optional-runtime skips, 62 subtests; dev suite OK.
- Top-Down focused suites (context, flagship, plugin/STDIO): 77 passed.
- Ruff, strict source mypy, strict standalone-plugin mypy, relay, supply-chain secrets: passed.
- Codex skill, Codex plugin and Claude plugin validators: passed.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

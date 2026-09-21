# Slice 17 privacy and host-confinement review

## Blocking findings

1. The required full gate had not yet passed at review time.
2. The normative install-path row remained pending and the sanitized matrix did not record the
   built-wheel interpreter/package classification.
3. The daily-task runner recorded, but did not enforce, equality between requested and resolved
   frozen host versions.

## Non-blocking assessment

- Credential environment values are excluded; the Codex auth copy is confined to a mode-0700
  temporary tree.
- Daily-task evidence supports all four MCP journeys and no-approval launches.
- Raw model output, prompts, paths, tokens, auth data and sessions are not committed.
- Absent Read/Write attempts are handled conservatively: no denial or confinement claim is made.
- Apple Event evidence, session binding, marker/token observations and absence of `--add-dir` are
  sanitized and truthfully qualified.

**Verdict:** **BLOCK**

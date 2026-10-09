# Review 115 — Research guard accepts Claude's socketpair stdio

- **Date:** 2026-10-08
- **Scope:** commit `1a24b3d`: `install_guard` in `tools/agent_e2e_discovery.py` (research-only
  harness, not installed) and one regression test.
- **Method:** independent code-reviewer agent. Read the diff and verified on this macOS host with
  `.venv/bin/python`: socketpair inode uniqueness across 4,000 pairs, dup identity, pipe vs socket
  `st_dev`, and internet-socket identities.

## Blocking findings

None.

## Notes (disposition)

- Internet sockets all report `(S_IFSOCK, 0, 0)`, so an inet stdout would have matched any inet
  socket. **Fixed:** sockets with inode 0 are refused as the wire.
- No negative test showed that an unrelated socketpair is refused. **Added.**
- The error message mentioned only pipes. **Fixed.**
- Pre-existing gaps (`os.write`, `sendto`, new sockets are not audited) are unchanged and match the
  guard's "not an OS sandbox" docstring.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

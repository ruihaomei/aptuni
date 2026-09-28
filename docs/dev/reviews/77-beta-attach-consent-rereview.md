# Review 77 — Beta P2/P3 re-review (remediation `629dba2`)

**Scope:** remediation of Review 76's blocking finding. Independent reviewer; read-only.

- Finding 1 resolved: the consent screen now states that each suggestion is saved in the Vault as a
  pending item, becomes Memory only when accepted and stays in history until purged; this matches
  `MemoryService.observe` (quarantined Observation + CandidateMemory, host proposals never promoted).
  The write line is limited to editing or deleting existing records, which holds for API v1.
- Findings 2 and 3 resolved: network use is stated as a declaration Aptuni cannot enforce; the read
  heading no longer claims per-request relevance. "Does not import or run the plugin's code" is
  still true: no code under `src/aptuni` loads a manifest `entry_point`.
- Finding 4 resolved (`SchemaVersionError` → `vault_unverified`); finding 7 partly resolved (error
  handler tolerates an unreadable config; bare `input()` stays in BACKLOG).
- Findings 5 and 6 are recorded in `docs/dev/BACKLOG.md`.
- Non-blocking note: the Chinese test did not pin the "becomes Memory only after you accept"
  sentence. Addressed afterwards with an assertion in `tests/integration/test_grant_consent.py`.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

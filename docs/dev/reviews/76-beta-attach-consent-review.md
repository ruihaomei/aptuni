# Review 76 — Beta P2 Vault attach and P3 plugin grant consent

**Scope:** local commit `e99b1f6` (`aptuni attach`, setup adoption of an existing Vault, bilingual
plugin grant consent screen). Independent reviewer; read-only.

## Confirmed correct

- Attach never writes inside the Vault. It avoids `Vault.open()`/`recover()`, verifies read-only,
  rejects a state directory inside the Vault, requires `HEAD.json`, refuses switching away from a
  different configured Vault, and writes only `config.json` in the state directory after `verify().ok`.
  `Vault.__init__`, `check_vault_filesystem`, `head()`, `_read_segments` and `unexpected_files` are
  read-only; `verify()` takes no lock.
- The consent screen is rendered from the real `PluginGrantPlan`; untrusted plugin names are
  delimited; the derived revoke grant ID matches `apply`; `--json` output is unchanged.

## Findings

1. **BLOCKING — consent overclaimed retention and write scope.** "Nothing is kept until you accept
   it" and "no permission in this grant can change them" were false: `memory.propose` commits an
   Observation and a quarantined CandidateMemory into canonical Vault records, and a rejected
   suggestion stays in history until purged.
2. Non-blocking — "no egress" read as enforced; Aptuni refuses egress-declaring manifests but does not
   sandbox the plugin.
3. Non-blocking — "only what is relevant to each request" is untrue for `profile.read` and
   `memory.review.read`.
4. Non-blocking — `SchemaVersionError` escaped attach verification into the generic error path.
5. Non-blocking — whether setup creates or attaches is decided at render and apply time, not frozen
   in the plan digest (both outcomes are safe).
6. Non-blocking — no attach test over an interrupted restore/purge Vault.
7. Non-blocking — the attach error handler re-read a possibly corrupt config; text-mode
   `grant apply` still uses bare `input()` (already in BACKLOG).

## Remediation (test-first)

- 1–3: consent text now says suggestions are saved in the Vault as pending items, become Memory only
  when accepted, and stay in history until purged; the write line covers editing or deleting
  existing records; the network line is a declaration that Aptuni cannot enforce; the read heading
  no longer claims per-request relevance. New English and Chinese tests assert the truthful wording.
- 4: attach catches `SchemaVersionError` and reports `vault_unverified` (new test).
- 7: the attach error handler tolerates an unreadable config.
- 5, 6 and the `input()` note go to `docs/dev/BACKLOG.md`.

**Verdict:** **BLOCK**

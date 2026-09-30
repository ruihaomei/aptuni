# Review 85 — Beta knowledge evidence model (ADR-0029), commit `fd8d0b6`

- **Scope:** `git show fd8d0b6`: ADR-0029 (which amends ADR-0028 items 2 and 8), the Vault ceiling
  invariant, the MarginNote per-item classifier, GitHub Standard concept items with their usage
  cache, the `knowledge.applied` grant, `source authorize` re-derivation, `source reclassify`,
  concept resolution, Knowledge State and compact `aptuni.profile`.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Checks run:** the full `pytest` suite passes (3 skipped). `ruff check .` is clean.
  `mypy src` reports no issues in 119 files. Scratch probes under `/private/tmp/.../scratchpad`
  used only temporary Vaults; the live Vault was not touched.

## Probes

| Probe | Result |
|---|---|
| Owner reject of a legacy blanket `Studied Boosting.`, then `reclassify` (downgrade), then the card gains an annotation and syncs as `studied` | No Fact is re-formed. The rejection holds across the correction lineage. Re-applying the old digest raises `confirmation_stale`. `doctor` is OK. |
| Privacy purge of the same Fact (scope: Fact + promotion event), then `reclassify` and the same upgrade | No Fact is re-formed, because the ledger digest is honoured through the lineage. `doctor` is OK. |
| GitHub: `knowledge.applied` granted, then the tree is truncated and `src/train.py` is not listed (partial coverage) | XGBoost and pandas stay `applied`. The unlisted file item is carried forward and its cached usage is reused. |
| GitHub: `src/train.py` is renamed ambiguously to two identical files (both `needs_review`) | Concept evidence is re-written with a modify whose paths are the two files still under review (see N2). |
| Host `aptuni.profile` with the grant `{knowledge}`, plus an owner fact in `skills` naming XGBoost | Knowledge State counts only `knowledge` records. The `skills` fact appears neither in the unit nor in the rows. |
| Legacy summary `"3 annotated examples [NB]; 0 excerpts, 0 annotated, …"` on an isolated card | `marginnote_signal` returns `studied` (see N1). |
| `aptuni knowledge XGBoost --limit 150` | Fails with an uncaught `AptuniError invalid_context` (see N5). |

## Findings

1. **NON-BLOCKING — The legacy-summary fallback can read a card or notebook title as an annotation count.**
   `src/aptuni/knowledge/classify.py:21,32`. `_ANNOTATED.search(summary)` takes the *first*
   `\d+ annotated` in the summary. The summary begins with the untrusted card path and the notebook
   name (`src/aptuni/sources/marginnote4/digest.py:88`), and only then gives the structured
   `N excerpts, N annotated, …` segment.
   *Failure scenario:* legacy Evidence (a `marginnote.locator@2` locator without `annotated`) from a
   notebook named e.g. "2 annotated readings", or a card titled "3 annotated examples". `source
   reclassify` then keeps (or grants) `studied` for isolated cards and forms or keeps
   `Studied …` Facts. This is a narrow over-claim in exactly the migration the ADR runs on User #1's
   26k cards. It is owner-confirmed and bounded, so it does not block.
   *Fix:* anchor the pattern on Aptuni's own segment, e.g.
   `re.compile(r"(\d+) excerpts, (\d+) annotated, \d+ sub-concepts")`, and take the last match.
   Add a unit test with a card title and a notebook name that contain "N annotated". Do this before
   running the migration on the real Vault.

2. **NON-BLOCKING — Concept items read files whose identity is still under review, and record their paths.**
   `src/aptuni/application/ingest.py:379` filters only `held`. Newly observed items whose file
   operations are `needs_review` (ambiguous rename) are scanned. Their paths enter canonical concept
   Evidence (the probe excerpt was
   `applied in 2 files … (src/a_train.py, src/b_train.py, …)`), and under a `knowledge.applied`
   grant this re-derives the Applied Facts.
   A concept seen only through a truly `held` file has the opposite problem. Under complete coverage
   it is *removed*, although held semantics say "never tombstoned until review resolves"
   (`src/aptuni/sources/github_concepts.py:95-98`).
   Nothing crosses the approved source scope, so this is not a privacy failure. It is still an
   inconsistency with the reconcile contract.
   *Fix:* derive concept usage from items whose file operation was admitted. Treat a concept
   supported only by held or pending items like partial coverage (carry it forward).

3. **NON-BLOCKING — The per-blob usage cache has no classifier or registry version.**
   `src/aptuni/sources/github_concepts.py:27,49` reuses `usage` whenever the blob id matches.
   *Failure scenario:* a later build amends the registry or the `applied` rule. Unchanged files keep
   their old judgement indefinitely, so concept evidence depends on the order of history rather than
   on the current classifier. That weakens the ADR's "recomputed deterministically" property and
   any future `reclassify` for GitHub.
   *Fix:* key the cache by `(CONCEPT_VERSION, registry digest)` and drop it on mismatch.

4. **NON-BLOCKING — Downgrade behaviour is fail-closed but undocumented.**
   A 0.2.0b6 build reading a Vault that contains a `source_authority_applied` v3 grant rejects the
   `ReviewEvent` at load, because its v3 gate only knows `source_authority_studied`. Its
   `default_registry` also rejects `annotated` and `github.concept` in source state. This is safe:
   it fails closed. However, neither ADR-0029 nor the release notes say that a Vault used with this
   build can no longer be opened by b6.
   *Fix:* add one line to ADR-0029's Consequences and to the next release note.

5. **NON-BLOCKING — `aptuni knowledge QUERY --limit 101..200` crashes.**
   `src/aptuni/cli/knowledge_cli.py:29` clamps to 200, but `knowledge_states` passes that limit to
   `context()` (`src/aptuni/application/knowledge_commands.py:59`), which accepts at most 100.
   *Fix:* clamp to 100, or cap the context limit separately from the state limit.

6. **NON-BLOCKING — Compact activation cites at most 8 of the ids it omits.**
   `src/aptuni/application/knowledge_commands.py:23,28,76`. `covered` contains *all* Evidence ids of
   each state, and every one of those rows is removed. The unit cites only the first 8, so a host
   cannot follow provenance for the rest. Also, if `pack_units` drops a knowledge unit for budget,
   its covered rows are gone as well. `truncated` is set, but the content is lost.
   *Fix:* omit only the cited ids, or add a count such as "+N more"; pack the knowledge units before
   deciding which rows to drop.

7. **NON-BLOCKING — Some registry `calls` are not "constructs or calls it".**
   `src/aptuni/knowledge/concepts.py`: `py.pydantic` (`\bBaseModel\b`), `ml.pytorch`
   (`torch\.(nn|optim|…)\b`, which matches an attribute reference) and `ml.tensorflow`
   (`tf\.\w+`) match references rather than calls. `data.pandas` / `data.numpy` count any single
   call (for example `pd.read_csv(`) as `applied`, which yields a Fact such as "Applied pandas." ADR-0029
   item 3 describes the rule as import plus construction/call, which these entries loosen. They are
   heuristics owned by the ADR, but they should match its wording or the ADR should list them.

8. **NON-BLOCKING — The reclassify preview can overstate what will be added.**
   `source.reclassify.effect` says the `{up}` items "are added to your Profile". An upgrade whose
   lineage holds an owner reject, edit or purge correctly forms no Fact (verified by the probe), so
   the copy overstates. `_reclassify_preview` could count only upgrades where
   `owner_decided(...)` is false.

9. **NON-BLOCKING — Test coverage is behind the ADR's Verification section.**
   ADR-0029 says GitHub concept "removal" is tested, but no test removes a concept under complete
   coverage. There are also no tests for:
   - crash replay of a sync with concept operations (pending state with the cache);
   - concept carry-forward under partial coverage;
   - held or pending items;
   - host module scoping of `knowledge_state` units;
   - `reclassify` with an owner reject or purge in the lineage.

   The probes above passed for partial coverage, host scoping, reject and purge. Each should become
   a regression test.

## Verified sound

- **Backward compatibility of the ceiling.** Every pre-ADR-0029 `studied` producer (1c4f4af,
  1b1af8c, e8d72a9) emitted `studied` only when `knowledge.studied` was in the effective authority:
  either `primary_for` or the ADR-0028 v3 grant committed in the same batch as its corrections.
  `_check_evidence_ceiling` uses the same `EvidenceLineage.authority()` union, so no existing Vault
  with blanket `studied` Evidence, grant events or retractions fails `validate()`, `doctor`, backup
  verification, restore or purge. Purges are whole-source, so no `studied` Evidence can outlive its
  `source_config`. No other writer emits a non-exposure signal (checked with `grep`).
- **No silent reclassification on sync.** The MarginNote fingerprint excludes locator fields. The
  summary already carried `N annotated`, so adding `annotated` to the locator produces no
  operations. Only new or changed cards go through the classifier.
- **Owner control, atomicity, staleness.** `reclassify` and `authorize` hold the source-operations
  lock and the per-source sync lock. They refuse a committed purge and recompute the preview under
  the lock against the digest. Each commits one batch at `expected_seq`. Correction ids are
  deterministic and domain-separated (`authority:{event}` vs `authority:reclassify:{digest}`).
  Re-applying an old digest is refused as stale. Owner edits are `declared_statement` Facts without
  `evidence_ids`, so they survive a downgrade. Rejects and purges are honoured through
  `owner_decided`.
- **Privacy.** Concept items carry only concept id, level, per-level counts, at most five paths and
  the repository name. The only content they keep is the concept-id map, and no code text; a test
  asserts no code line leaks. The cache lives in non-canonical source state, which privacy purge
  already deletes. Host activation requires a non-empty module set inside the host grant plus
  `evidence.read`. `knowledge_index` filters `exposable()` by those modules, and the cache key
  includes the module tuple. Knowledge units are marked tainted.
- **GitHub reconciliation.** File reconciliation receives a file-only prior snapshot, so no
  concept locator reaches the path-keyed code. The combined snapshot id feeds the delivery guard,
  and unchanged syncs are admitted as duplicates. The pending state carries the cache for crash
  recovery. Removal happens only under complete coverage.
- **No over-claim.** No proficiency value is stored. Exposure never forms a Fact
  (`strongest_signal` has no `exposure`). The level ladder ignores owner claims and is labelled
  "derived from Evidence, not a proficiency measure" in the summary, the payload and both locales.
  GitHub Standard can never reach `demonstrated`, and `knowledge.applied` can be granted only to
  source type `github`.

## Remediation (implementing agent)

Non-blocking notes 1, 2, 3, 5, 6, 7 and 8 were applied with regressions before release: the legacy
annotation count is read from the last Aptuni counts segment only; held or review-pending files feed
no concept and make concept coverage partial; the per-blob cache carries a rules version; the CLI
limit matches the context bound; compact Profile drops only rows a packed unit cites; the
pydantic/torch/tf/jax/django rules need a real call; and the reclassify preview names the owner
exception. Notes 4 and 9 (older-build lock-out documentation, held/partial/crash regressions beyond
the ones added) are in `BACKLOG.md`. The reviewer's verdict is unchanged.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**

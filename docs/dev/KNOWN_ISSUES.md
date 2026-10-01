# Known Issues and Open Risks

| ID | Severity | Issue | Disposition |
|---|---|---|---|
| KI-009 | Deferred | Graphiti projection loses canonical semantics and needs a ledger. | S11 before Milestone 3 adapter. |
| KI-016 | High | S01 findings F1–F3: whole-Vault revalidation per commit, integrity mismatch blocks all reads, purge needs startup `recover()`. | Mandatory M1.1 Slice 3 requirements (incremental validation + compaction; out-of-band edits → quarantine; recover before serving); fold into ADR-0001/0010 on acceptance. |
| KI-017 | High | S02 F1: pip RECORD does not hash `.pyc`; a forged bytecode file passes closure verification and executes. | M1.1 sets `sys.pycache_prefix` to a core-owned directory before importing plugins (proven in S02) and adds F2/F3 (manifest placement; lockfile artifact hashes). |
| KI-018 | High | S03 used a templated synthetic corpus; broad two-character queries admitted top-5 distractors even though aggregate gates passed. | M1 adds dogfood judgments and per-result context-noise tests; retain size telemetry and score/reranking seam before user-facing quality claims. 2026-09-25 real data point: on a 10-record Vault, an Evidence-answerable query in default L3-only Context returned 2/2 noise via the ADR-0004 any-term fallback, whose 25% floor is relative to the best *remaining* hit and therefore admits single-term matches when no strong L3 candidate exists. Deliberately not retuned on one trial; collect more real `profile_memory` trials (now separated by `evaluate report`) before changing the frozen lexical contract. 2026-10-01 (ADR-0004 amendment): multi-keyword queries now fall back to whole keywords, so a two-word phrase can return a record matching one word (e.g. “machine translation” → a machine-learning note); judge with real trials before adding a phrase rule. 2026-10-01 experiment (`docs/research/findings/retrieval-experiments.md`): 4 of 6 negative queries still return items via generic single words; neither jieba nor a small dense model with a score floor separated them. 2026-10-02 (ADR-0030): solved for callers that pass host `concepts` (0% leakage on 12 should-be-empty queries); plain queries keep the b9 behaviour (67% leakage); semantic gates reach 25% but were not adopted. |
| KI-021 | Medium | The opt-in hybrid semantic lane has no relevance floor: Mem0 is queried with `threshold=0.0`, so a query with no lexical match still returns exposable accepted memories up to the requested limit. The lexical path deliberately has the opposite guarantee (relative-score floor). | Documented in ADR-0004's 2026-09-22 amendment and the READMEs. Opt-in, owner-CLI only, and every row already passed the final exposure check, so this is an honesty/quality gap, not a leak. Decide a floor or a reranking seam before any hybrid quality claim or before hybrid reaches the Context API. |
| KI-019 | High | Portable `realpath`/`stat` cannot identify APFS clone ancestry. The pinned native bridge is implemented, but this APFS Data volume does not advertise `VOL_CAP_FMT_CLONE_MAPPING`; therefore real positive clone-family cases are unavailable on the Gate 0 host. | Predicate and fail-closed adversarial tests pass. Foundation `fileContentIdentifier` is diagnostic only. Missing capability, incomplete scans and absent matches remain `unverified`; no negative result proves confinement. Focused review decides closure. |
| KI-022 | Low | Aptuni's Notion OAuth item uses the legacy file-keychain `SecKeychain*` APIs (deprecated but functional). New items trust the creating Python interpreter, so any script run by that same interpreter can read the token without a prompt; the old `security` CLI path trusted `/usr/bin/security` instead. | Accepted for the local-first single-owner model (Review 65 N4). Revisit with a data-protection keychain or a signed helper before multi-user or distributed binaries. |
| KI-023 | Medium | ADR-0029 v1 classifiers are deterministic heuristics: MarginNote `studied` = sub-concepts, ≥2 further excerpts or an annotation; GitHub `applied` = import plus a registered construct/call; only ~35 registered concepts are detected in code. The first GitHub sync after upgrading reads every selected manifest/code/doc file once more (an unauthenticated user can hit the 60-request/hour limit and retry later). | Tune only with an ADR-0029 amendment and owner-labelled evidence; extend the registry as real repositories need it. |

Resolved issues move to an appended history section; do not silently delete them.

## Resolved history

- **KI-008 (2026-09-22):** S10 isolated Mem0 2.0.20 and conditionally admitted only a disposable
  local projection populated with `infer=False`. Upstream inference retains raw messages and is
  rejected. `Memory.delete()` leaves marker bytes in Qdrant/history, so privacy deletion must close
  and remove the entire provider root and rebuild active records from the canonical Vault. Fresh
  rebuild, exact projection equality, canonical-byte isolation, guarded network paths and complete
  managed-root purge passed; focused Review 52 approved the boundary with non-blocking notes.
- **KI-014 (2026-09-21):** Slice 17 completed the exact frozen Claude Code 2.1.267/2.1.266 and
  Codex 0.155.0/0.154.0 daily-task matrix plus focused Claude file-tool and Apple Event
  observations. The file-tool calls were not emitted, so no denial is claimed; both Apple Event
  attempts produced no outer effect. Complete effective settings remain unavailable and status
  stays `unverified`. Review 48 independently approved the conservative evidence contract.
- **KI-021 (2026-09-20):** Resolved by ADR-0016. The deletion ledger and in-flight restore journal are canonical Vault state, so deletion and restore recovery survive a wiped state directory; reads union the Vault ledger with any not-yet-migrated legacy file, and `recover()` migrates legacy ledger/journal state safely. `aptuni backup create | verify | list | restore` is the supported path, and a folder without a manifest is refused. Verified end to end on a simulated new machine: restoring a pre-purge backup dropped the purged record, kept the survivor, `doctor` passed, and a raw byte scan found no purged marker. Permanent regressions live in `tests/integration/test_backup.py`; Review 39 closed the stream **APPROVE**.
- **KI-020 (2026-09-20):** The canonical MarginNote 4 integration no longer depends on OPML. The
  accepted direct local source uses native IDs, a fail-closed schema fingerprint and text-free
  `marginnote.locator@2`; real-library sync and focused re-review 25 passed. OPML remains an optional
  compatibility path whose exporter shape is unverified, not a production blocker.
- **KI-004 (2026-09-20):** Direct MarginNote 4 native IDs replace unproven export identity for the
  flagship macOS path. Unknown layouts stop before producing deltas (ADR-0015, review 25).
- **KI-002 (2026-09-19):** License confirmed as Apache-2.0 (ADR-0009 accepted).
- **KI-010 (2026-09-19):** Thin research memory initialized (`PROJECT_KNOWLEDGE.md` → `docs/research/`).

- **KI-001 (2026-09-18):** S00 selected temporary development distribution
  `personal-context-core` / import `personal_context_core`; public naming remains a release workstream.
- **KI-012 (2026-09-18):** Execution review stream reached APPROVE WITH NON-BLOCKING NOTES (report 10);
  its notes NF1–NF8 are addressed in remediation 10.
- **KI-013 (2026-09-18):** Cold Claude Code relay drill passed (report 11); defects fixed in
  remediation 11.
- **KI-011 (2026-09-18):** Security stream reached APPROVE WITH NON-BLOCKING NOTES (report 14) after the
  maintainer chose the honest host trust boundary (ADR-0013); notes addressed in remediation 14.
- **KI-006 (2026-09-18):** S01 proved the Vault write protocol on the Gate 0 baseline (46 tests; crash at
  four boundaries, 8-process concurrency, lock-holder SIGKILL, purge/restore). Power-loss durability
  remains an assumption (`spikes/S01-vault.md` F4).
- **KI-007 (2026-09-18):** S02 proved entry-point discovery without execution, isolation of duplicate,
  broken and incompatible plugins, approval bound to the installed closure, and drift denial
  (12 tests). Undeclared-network checks are detection only.
- **KI-003 (2026-09-19):** S03 measured all three extension-free FTS5 strategies on frozen bilingual
  evidence. Deterministic 2–4-character CJK lexemes passed development, 25k-scale, and untouched
  holdout gates (23 tests); generalization and broad-query noise continue as KI-018.
- **KI-015 (2026-09-19):** S04 ran the required Codex current/preceding stable pair (0.155.0 and
  0.154.0); both returned `HOST_OK 61` on the bounded annotated read path. Installed 0.153.4 remains
  an additional observation, not the release target.
- **KI-005 (2026-09-19):** After the account limit reset, Claude Code 2.1.267 and 2.1.266 each called
  the bounded strict-config MCP tool exactly once and returned `HOST_OK 61`. Both versions also
  completed baseline and project-merge host canaries.

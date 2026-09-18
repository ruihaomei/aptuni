# Proof-of-Concept Spikes

Spikes answer decisions, produce fixtures/results under `docs/dev/spikes/`, and are discarded unless
the execution plan explicitly promotes code. A spike is complete only when its acceptance criteria
and ADR impact are recorded.

## Phase 0 — before the production scaffold

### S00 — Public namespace and license check

- **Question:** Which distribution/import/repository name is collision-free, and does the maintainer
  accept Apache-2.0?
- **Method:** Search PyPI/GitHub/package metadata and trademark-risk surface; record alternatives.
- **Accept:** A collision-checked temporary namespace permits scaffolding; maintainer confirms public
  name and project license before release/external contributions.
- **Affects:** ADR-0002, ADR-0009. **Blocking:** complete for local engineering; still a release gate.
- **Result:** `spikes/S00-name-license.md`.

### S01 — Canonical schema and crash-safe/concurrent Vault round trip

- **Question:** Can all v1 canonical records, including interaction memory and source authority,
  round-trip without loss and survive interrupted/concurrent writes?
- **Method:** JSON Schema/Pydantic prototype including trust/taint, policy epoch, retention label,
  confirmation, deletion receipt/ledger; golden records; temp-write/fsync/rename; migration from a
  deliberately older fixture.
- **Accept:** Exact semantic round trip; invalid references fail; interrupted write leaves prior or
  next valid state, never partial state. A documented single-writer/optimistic-version protocol
  yields one valid serial outcome under simultaneous append/supersede, stale writer, lock crash,
  reader-during-commit, and abandoned-lock recovery on the fixed Gate 0 macOS 26.2/APFS baseline;
  directory durability is explicit and unknown/network/synced filesystems fail closed. Run with
  `/opt/homebrew/bin/python3.13`; the result records and asserts `sys.executable`, `sys.version`,
  `sqlite3.sqlite_version`, `sw_vers`, and `statfs` of the Vault volume (APFS data volume,
  `/System/Volumes/Data`). Fail-closed detection uses `statfs` `f_fstypename` = `apfs` with the local
  flag plus a denylist of sync roots (`~/Library/Mobile Documents`, `~/Library/CloudStorage`,
  Dropbox); injected non-APFS, non-local, and synced-root probes must refuse. M1.1 later admits
  Linux/ext4 before claiming Linux support.
- **Affects:** ADR-0001, ADR-0006, ADR-0010, ADR-0011, ADR-0012. **Blocking:** yes.

### S02 — Installed plugin discovery and isolation

- **Question:** Does standard entry-point discovery support explicit activation with honest trust
  warnings and failure isolation?
- **Method:** Build one fixture distribution plus duplicate-ID, broken-import, incompatible-version,
  and undeclared-network cases.
- **Accept:** Discovery performs no provider work; one failure does not stop core; activation validates
  manifest/contract and records manifest plus the complete resolved lock/SBOM closure (names,
  versions, artifact hashes, sources/indexes, extras, edges); transitive drift denies or requires new
  approval; warnings state in-process plugins are trusted code. This proves failure isolation, not
  malicious-code containment.
- **Affects:** ADR-0002. **Blocking:** yes.

### S03 — Bilingual SQLite retrieval

- **Question:** Which extension-free strategy meets Chinese/English MVP quality?
- **Method:** Compare `unicode61`, `trigram`, and `unicode61` plus deterministic CJK lexemes on a
  versioned bilingual corpus.
- **Metrics:** recall@5, MRR, false-positive rate, two-character recall, p95 latency, index size.
- **Accept:** Corpus, query judgments, metric code, numeric thresholds, checksum, and untouched
  holdout are frozen before comparative runs. Chosen design clears every blocking threshold and the
  runner exits non-zero otherwise; otherwise propose a
  segmentation dependency ADR.
- **Affects:** ADR-0004. **Blocking:** yes.

### S04 — MCP capability and privacy conformance

- **Question:** Do target hosts invoke the proposed tools consistently without hidden network or
  telemetry behavior?
- **Method:** Minimal pinned Python SDK server over STDIO; probe Claude Code, Codex, Cursor, and
  Claude Desktop; capture capability negotiation, principals/scopes, bounded results, and mutation
  confirmation.
- **Accept:** Run the MCP/application process with socket creation denied or an isolated network
  namespace. Claude Code and Codex pass required tools; forged caller, stale/replayed/mismatched
  confirmation, confused deputy, disabled module, and mid-request policy change all deny;
  source/model/MCP text cannot mint approval, unconfirmed consequential writes deny, and candidates
  cannot auto-promote; every ADR-0013 Verification case passes in the real host — in particular
  approval is terminal-only and a confined agent's attempt fails closed; hostile names never reach a
  command line; `doctor` never claims confinement, reports `not_in_effect` on every core-observed
  canary success or observable escape key/flag/writable-root path, and reports `unverified` for
  skipped/misdirected legs and unobservable launch flags; evidence is session-bound; read-deny works
  where supported; narrowing edits are honored and widening/mixed/retag edits quarantine; revoked
  egress ends in `cancelled_policy`; the flag/env/config enumeration shows no override; host status
  and `views/Status.md` carry no marker path; and the per-host required-key rows and core-observable
  evidence sources are recorded in `COMPATIBILITY.md`;
  model-behavior injection probes are defense in depth, not authorization proof;
  unsupported resources/prompts degrade cleanly; no undeclared server/dependency network destination;
  bounded STDIO disclosure to the configured host is expected and synthetic-only in hosted probes;
  a fake proven-local host and declared remote/unknown host enforce strict-local denial and
  consent-bound module release; core policy alone admits proven-local after pinned adapter/runtime
  and end-to-end model egress evidence; schemas snapshot.
- **Affects:** ADR-0005. **Blocking:** yes for Claude/Codex; other hosts may remain documented gaps.

### S05A — Common source identity and delta contract (Gate 0)

- **Question:** Can the common SourceLocator/Snapshot/CandidateDelta/SourceConfig envelope represent
  all three MVP source identity families before v1 freezes?
- **Method:** Representative sanitized/synthetic Folder rename, MarginNote edit/move/delete OPML, and
  GitHub commit/path/blob/truncation fixtures against the draft common contract.
- **Accept:** Identical replay is idempotent; source-specific identity fits versioned extension fields
  without changing common invariants; unknown/ambiguous identity is representable and reviewable;
  disappearance never deletes facts; authority conflicts and locators round-trip.
- **Affects:** ADR-0006. **Blocking:** yes before v1 schema freeze.

### S05B — Provider admission suites

Before each Folder/MarginNote/GitHub provider ships, run real provider-specific identity/replay plus
approved-root/origin, symlink/TOCTOU, parser-bomb, secret exclusion, redirect/pagination/rate-limit,
offline-mode, deceptive metadata, and instruction-injection canaries. Discoveries must stay within
the accepted extension/version boundary or trigger a schema ADR/migration before provider release.

## Provider admission spikes

### S10 — Mem0 local/privacy/portability

Run fully local inference, disable telemetry, audit raw retention, exercise additive/correction
behavior, and rebuild from canonical records. Admit only when a network canary remains silent and
provider deletion/rebuild leaves canonical files unchanged. Target: Milestone 2.

### S11 — Graphiti temporal/provenance projection

Test node-attribute mutation, fact-edge mapping, out-of-order corrections, provenance round trip,
projection ledger, and full rebuild on a disposable database. Admit only with documented loss and
no canonical dependency. Target: Milestone 3.

### S12 — Host L0 injection

Measure a bounded pre-rendered L0 card in Claude Code command hooks and the supported Codex adapter
path. Require restrictive permissions, atomic render, size/content allowlist, policy epoch,
invalidation, purge/uninstall cleanup, and no excerpts/secrets/raw interaction. Accept when a module
disabled between render and startup cannot leak and startup works with MCP unavailable. Test fake
proven-local and declared remote/unknown hosts: strict local-only denies personal L0 to the latter,
and consent releases only granted modules with honest external-retention messaging. **Blocking before
each host adapter ships.**

## Non-blocking discovery spikes

- **S20:** Affected-component plus dependant test selection after the package graph exists.
- **S21:** Streamable HTTP authentication/authorization, CSRF/origin/rebinding, revocation, and tenant
  boundary before any remote deployment; HTTP remains disabled until accepted.
- **S22:** Plugin manifest-to-doc/catalog generation before a community registry.

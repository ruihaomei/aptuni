# Upstream Research: source identity and incremental deltas

> Researched 2026-09-18 · PRD refs: §8–§10, §22–§23, §31, §35, §48, §51

## TL;DR

- MarginNote officially advertises Markdown/OPML export and OPML preserves a tree, but neither the
  OPML 2.0 specification nor the public MarginNote material inspected promises a stable per-node ID
  across exports. Stable identity must be proven against real MarginNote 4 fixtures; it cannot be an
  MVP assumption.
- Keep source/document/node identity distinct from content fingerprints. Hashes answer "did bytes
  change?"; they are not durable identity because legitimate edits change hashes.
- Maintain a source-local identity manifest. Prefer a verified vendor ID; otherwise reconcile new
  exports against the previous tree and reuse generated IDs only for unambiguous matches. Ambiguous
  matches become reviewable candidate deltas, never silent destructive changes.
- GitHub provides stronger snapshot primitives: repository ID, commit SHA, tree/blob SHAs and path.
  A blob SHA is content identity, not file-history identity; path changes and edits still need delta
  logic.

## Sources inspected

- [MarginNote research workflow — Markdown/OPML export](https://www.marginnote.com/en/scenarios/research.html)
- [MarginNote support — OPML export through focus branch](https://forum.marginnote.com/t/exporting-a-mind-map/1926/7)
- [MarginNote support — OPML may include page number, document name and tags](https://forum.marginnote.com/t/automatic-citations-and-referances-in-margin-note-2/4425/28)
- [OPML 2.0 specification](https://2005.opml.org/spec2.html)
- [GitHub REST API — Git trees](https://docs.github.com/en/rest/git/trees)
- [GitHub REST API — repository contents](https://docs.github.com/en/rest/repos/contents)
- [GitHub REST API — Git blobs](https://docs.github.com/en/rest/git/blobs)

MarginNote's public site is primary product evidence. The support forum is useful but not a schema
contract. Claims based only on support posts are labelled accordingly.

## MarginNote OPML

### Verified facts

MarginNote's current product site says mind maps can be exported to Markdown and OPML. Public support
material describes exporting an OPML branch and reports that OPML exports may carry page number,
document name and tags.

OPML 2.0 represents an outline as nested `<outline>` elements. Each node requires a `text` attribute
and may have arbitrary additional string attributes and child outline elements. The base OPML
specification does **not** require an `id` attribute or define stable node identity.

### Important negative finding

No inspected official/public MarginNote source specifies:

- exact OPML attribute names for MarginNote 4;
- which card/source fields are always exported;
- whether a node identifier exists;
- whether any identifier survives repeated export, text edits, moves, branch export, notebook copy,
  or application upgrades.

Therefore "OPML node ID is stable" is unverified. A parser must preserve unknown attributes so a
useful vendor ID is not discarded, but the system may not treat an arbitrary attribute as stable
without a fixture-based contract.

### Proposed identity strategy

```text
source_id          generated once for a configured MarginNote source
export_snapshot_id hash + observed/export timestamp + parser version
vendor_node_id     optional, preserved exactly, trusted only after spike
canonical_node_id  project-generated UUID, persisted in source manifest
content_fingerprint normalized node content, never the canonical ID
structure_context  parent/sibling/child signatures used for reconciliation
```

On first import, assign a `canonical_node_id` to every parsed node. On later exports:

1. match a verified vendor ID if present;
2. otherwise match exact content plus strong structural context;
3. otherwise score text, source locator, ancestor path, sibling neighborhood and child signatures;
4. reuse identity only above a conservative threshold with a unique winner;
5. emit ambiguous matches for review;
6. represent unmatched old/new nodes as candidate remove/add, not immediate fact deletion/addition.

Moves and edits should be first-class delta operations. A path-derived ID is unsuitable because a
move would change identity; a content-hash ID is unsuitable because an edit would change identity.

## Generic folder sources

### Snapshot model

For each configured folder:

```yaml
source_id: <generated UUID>
root_locator: <user-approved path>
files:
  <document_id>:
    relative_path: ...
    byte_hash: sha256:...
    size: ...
    mtime_hint: ...
    parser_id: ...
    parser_version: ...
    parse_artifact_hash: ...
```

`mtime` and size are cheap scan hints; a strong byte hash confirms equality. The parser/version is
part of derived-artifact identity so a parser upgrade can trigger a controlled reparse even when
source bytes are unchanged.

Exact-hash rename detection can retain `document_id` when one old path disappears and one new path
appears with the same content. A renamed-and-edited file is inherently ambiguous without filesystem
history; treat it conservatively or ask for review rather than fabricating continuity.

Deletion from a source is evidence withdrawal, not necessarily proof that a Profile fact became
false. Emit a source-removal delta, re-evaluate facts with remaining evidence, preserve historical
provenance, and use tombstones/audit records where required.

### Format-specific provenance

The common provider should normalize locators while retaining parser-specific addresses:

- Markdown/text: relative path + heading/line or stable block locator where possible;
- DOCX: relative path + paragraph/table locator;
- XLSX/CSV: relative path + sheet/table/cell range;
- PDF: relative path + page + bounding/text anchor when available;
- OPML: source + canonical node ID + current ancestor path.

Line numbers and cell positions may move. They are evidence locators at a snapshot, not durable fact
IDs.

## GitHub Standard source

### Verified API constraints

GitHub's Git Trees API returns path, object type, size and SHA for tree entries. Recursive responses
are capped at 100,000 entries or 7 MB and set `truncated: true`; clients must then traverse
non-recursive subtrees. The Repository Contents API caps directory listings at 1,000 entries, has
special handling above 1 MB, and does not support files above 100 MB.

### Provenance and delta design

Record at least:

```text
github_repository_id
owner/name at observation time
ref requested by user/policy
resolved commit SHA
path
blob SHA
provider mode (Lite/Standard/Deep)
observed_at
```

The resolved commit makes an ingestion snapshot reproducible. A blob SHA identifies file contents;
the same blob at a new path provides strong rename evidence. When both path and blob change, compare
commits/diffs or treat it as a remove/add candidate unless continuity is clear.

Standard mode should be budgeted and selective: metadata, README, dependency manifests, directory
shape and representative files. It must not recursively fetch every blob merely because the tree API
can enumerate it. Record selection rationale so later updates revisit the same scope consistently.

## Candidate delta contract requirements

Every source provider should emit a common, non-destructive envelope:

```yaml
delta_id: ...
source_id: ...
base_snapshot: ...
new_snapshot: ...
parser: {id: ..., version: ...}
operations:
  - op: add | modify | move | remove | ambiguous_match
    subject_id: ...
    before: ...
    after: ...
    evidence_locator: ...
    match_confidence: ...
    reasons: [...]
impact_candidates: [...]
```

The provider reports source changes. A later fact-consolidation layer decides whether those changes
add, supersede, invalidate or leave canonical facts untouched. Keeping these layers separate prevents
a parser from silently rewriting the user's Profile.

## Security and privacy implications

- Folder discovery does not authorize ingestion; only configured, confirmed roots are scanned.
- Resolve symlinks and enforce the approved-root boundary before reading a file.
- Default-deny secrets, VCS internals, caches and oversized/binary formats; show the effective
  include/exclude plan before expensive processing.
- XML parsing must disable external entities and network resolution.
- GitHub tokens stay in host secret storage/environment, never the vault or candidate deltas.
- Provider logs should contain stable IDs and hashes, not raw sensitive document text by default.

## ADR implications

1. Separate canonical identity, source locators and content fingerprints in every schema.
2. Require provider snapshots and candidate deltas before any Profile mutation.
3. Treat source removals as evidence changes, not automatic historical fact deletion.
4. Preserve unknown source attributes/metadata losslessly where practical, but whitelist what may be
   exposed to agents.
5. Make parser and normalization versions explicit so projections are reproducible and rebuildable.

## PoC spikes

- **S1 — MarginNote identity:** obtain a small maintainer-created MarginNote 4 notebook and export it
  repeatedly after: no-op, text edit, node move, duplicate, delete/recreate, branch export and app
  restart. Diff all attributes and determine whether any vendor ID is stable.
- **S2 — OPML tree delta:** implement a fixture-only parser/reconciler preserving unknown attributes;
  measure add/modify/move/delete and ambiguous duplicate-text cases.
- **S3 — folder identity:** verify unchanged skip, edit, exact rename, rename+edit, deletion and parser
  upgrade using Markdown/DOCX/XLSX/PDF fixtures.
- **S4 — GitHub Standard budget:** against small, monorepo and >1,000-entry fixtures, verify tree
  truncation fallback, deterministic file selection, commit/blob provenance and bounded API calls.

## 2026-09-19 GitHub S05B admission refresh

- Current official Git Trees documentation keeps recursive responses bounded at 100,000 entries or
  7 MB and requires non-recursive subtree traversal when `truncated=true`:
  <https://docs.github.com/en/rest/git/trees>.
- Official guidance requires following typed `Link` headers rather than constructing pagination,
  conditional requests with ETag where appropriate, and stopping on 403/429 according to
  `retry-after` or `x-ratelimit-reset`:
  <https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api>,
  <https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api>, and
  <https://docs.github.com/rest/guides/best-practices-for-integrators>.
- An anonymous read-only probe of `octocat/Hello-World` using API version `2026-03-10` resolved
  repository ID `1296269`, default branch `master`, commit
  `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d`, and one-entry complete tree
  `b4eecafa9be2f2006ce1b709d6857b07069b4608`. This proves the public baseline only; it does not
  replace the sanitized maintainer-repository fixture or private/enterprise redirect/auth cases.

## 2026-09-19 GitHub S05B implementation and dogfood

- The maintainer explicitly authorized `ruihaomei/ctffr-app` as representative public source
  evidence. GitHub reported repository ID `1352604752`, default branch `main`, 10 commits and 50 HEAD
  paths. Initial configured sync selected 38 bounded text/code paths, wrote only 280-character
  minimized excerpts with canonical SHA-256 hashes, and passed `doctor`; repeat sync was a no-op.
- Comparing real commits `e346b6d023187e4cf4a848818874c23f2d2c4556` and
  `fb9fa9863c1b4a1b62a3f9ffda2b7cb5ee16fdc0` under stable repository identity produced complete
  coverage and one removal for `HANDOFF.md`. The repository contains no rename commit, so live rename
  is not claimed; unique blob rename remains covered by deterministic and integration fixtures.
- Production uses the unpaginated Git Trees endpoints: recursive responses are bounded and fall back
  to a request/entry-bounded non-recursive subtree walk. No list endpoint requiring `Link` pagination
  is used by Standard mode. Redirects remain exact-origin and bounded; 403/429 retry/reset signals
  stop without automatic sleeping.
- Independent Review 17 found crash/ref-advance, exclusion, URL credential, malformed-tree, blob
  identity and concurrent-journal defects. The implementation now journals final source state before
  canonical commit, recovers it under a per-source process lock, excludes secret/hidden/VCS/cache
  paths before fetch, canonicalizes origins, strictly validates tree identity, and recomputes each
  fetched Git blob object hash. Review 18 approved the remediation.

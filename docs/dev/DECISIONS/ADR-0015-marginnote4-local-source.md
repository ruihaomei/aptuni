# ADR-0015: Read MarginNote 4 directly and store a knowledge digest, not its text

- **Status:** Accepted (2026-09-20, focused re-review 25)
- **Date:** 2026-09-19
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent
- **PRD refs:** §7, §8, §22, §23, §25, §35
- **Research refs:** `spikes/s05b_marginnote/README.md`; `docs/research/upstream/marginnote4-local-store.md`
- **Needs maintainer confirmation:** no (the maintainer set the priority order on 2026-09-19)

## Context

PRD §8 assumed OPML export as the MarginNote path. Current MarginNote 4 documentation does not clearly
expose OPML as a native export, and asking every user to export files contradicts automatic
onboarding. On the maintainer's Mac (MarginNote 4.4.6, macOS 26.2), MarginNote 4 keeps its library in a
Core Data SQLite store, `MN4NotebookDatabase/<n>/MarginNotes.sqlite`, inside its app container. It
holds `ZTOPIC` notebooks and `ZBOOKNOTE` cards with native UUIDs (`ZTOPICID`, `ZNOTEID`), mind-map
children (`ZMINDLINKS`), merged excerpts (`ZGROUPNOTEID`), a per-row save counter (`Z_OPT`) and a store
UUID. S05B proved on real history that native note IDs persist across edits and moves.

The S05A locator also stored every node's full `ancestor_path` text and unknown attributes, which
reproduced the whole mind map in the Vault (full-content retention under ADR-0006).

## Decision drivers

- Automatic, permissioned onboarding with no manual export
- Exact identity instead of text matching; no weakened ambiguity guarantees
- Agents need the learning *structure* (path, coverage, depth, boundary), not source text
- Strictly read-only; unknown layouts fail safely

## Options considered

1. **Direct read-only store access (chosen).** Exact native IDs, full hierarchy and incremental sync.
   It depends on a private schema, so the schema is fingerprinted and fails closed.
2. **Minimal Add-on/API bridge (fallback).** MarginNote ships a JSBridge add-on API (preview
   documentation; `marginnoteapp/Addon` type definitions) and registers the `marginnote4app` URL
   scheme. It works where the container is unreachable (iPadOS) or after schema drift. It needs code
   running inside MarginNote, packaging and signing, so it is deferred until option 1 fails.
3. **Manual structured export / `.marginpkg` (last resort).** The existing OPML reconciler remains
   for compatibility; it is not the onboarding path.
4. **GUI export automation.** Rejected as a production architecture.

## Decision

- **Discovery is not permission.** `aptuni source discover-marginnote` runs only when the user asks.
  It probes the container in a child process with a timeout, because macOS privacy protection
  (TCC, "access data from other apps") blocks a reading process until the prompt is answered. It
  reports `found`, `permission_pending`, `permission_denied` or `not_found`, and per library
  `supported` or `marginnote_schema_unsupported`, each with a plain-language next step. It lists notebooks for the user's own terminal and persists
  nothing. `aptuni source add-marginnote` with explicit notebooks (or `--all-notebooks`) is the
  ingestion permission.
- **Read-only access.** The store opens with `mode=ro` and `PRAGMA query_only`, and every sync reads
  inside one transaction, including the schema check, for a consistent WAL snapshot. Sync decides
  whether a store lies in the MarginNote container from the path string alone, then runs the probe
  before anything touches the container. Only minimized columns are selected: card
  titles are truncated, excerpts are read to 48 characters (as a label fallback only), and comment
  blobs are tested for presence and never decoded. As a normal WAL reader, SQLite may update the
  shared-memory index file; the database and WAL are never written.
- **Schema gate.** Required tables and columns must exist, and the Core Data
  `NSStoreModelVersionHashesDigest` must be a known layout. Otherwise the sync stops with
  `marginnote_schema_unsupported` before producing any delta, so no evidence is withdrawn.
- **Identity.** The source subject is the native `ZNOTEID`. Move is a parent change, modify is a digest
  change, a copied card is a new ID (add), and a vanished ID is a removal. A selected notebook that
  disappears entirely carries its items forward as partial coverage (`marginnote_notebook_missing`)
  and is not treated as mass deletion: while coverage is partial, every previously known card that
  was not observed is carried forward, and no card is withdrawn. A complete read that finds no
  concepts where the previous snapshot had some stops with `marginnote_store_empty` rather than
  withdrawing everything.
- **`marginnote.locator@2` holds identity and structure only:** `database_id` (hash of the store
  UUID), `notebook_id`, `note_id`, `revision` (`Z_OPT`), optional `parent_id`, `depth`,
  `sibling_index`, `child_count`, `subtree_concepts`, `excerpt_count`. It holds no text.
- **Knowledge digest instead of text.** One Evidence record per *concept*: a standalone card with a
  title or with children. Untitled excerpt leaves and merged excerpts become counts on their
  concept (merged-into-merged chains resolve to the final card). The Evidence `subject` is a bounded
  label path (≤5 labels, each ≤32 characters). A label is the card title; an untitled parent card is
  labelled by the first ≤32 characters of its excerpt, a heading-sized label rather than its body. The
  280-character `excerpt` is a structured summary covering path, the concepts the node covers
  (≤8 child labels), excerpt and annotation counts, depth below, source document and pages, and
  first/last study month. It never copies excerpt bodies beyond that label, or any comments.
- **Signals.** `exposure` by default. `studied` only when the source's authority policy lists
  `knowledge.studied` (ADR-0006: authority is user policy, never hard-coded).
- **Deep link (inferred, not verified).** `marginnote4app://note/<ZNOTEID>` is derived for display,
  not stored. The installed app registers the `marginnote4app` scheme; the path form is inferred from
  MarginNote's documented `marginnote3app://note/<id>` card links and was not opened, to avoid
  switching the user's app.

## Consequences

- **Positive:** Zero-export onboarding and exact incremental sync (3.6 s for a full 83,096-note read).
  No mind-map text copy. Agents see learning path and boundary in about 70 tokens per concept.
- **Negative / risks:** The schema is private and may change; each new layout needs a fixture and a
  digest entry. Only macOS is covered. A TCC denial requires the user to change a system setting.
- **Follow-ups:** Add-on bridge if the store becomes unreachable; consolidation of concept digests
  into Profile facts (Milestone 2).

## Verification

A synthetic MN4-shaped fixture store covers discovery states, the schema gate, read-only behavior,
identity operations (add/modify/move/remove/copy/notebook missing), digest bounds and a no-text
locator. The real store is used for dogfood (counts only). Independent review is required.

# Backlog

Non-blocking improvements from reviews and self-review. Each item records where it came from.
Pick an item up when its owning slice starts; do not open a review round for these alone.

| Item | Source | Owning slice |
|---|---|---|
| Out-of-band-edit path: quarantine and diff a hash mismatch instead of a read refusal | S01 F2; ADR-0013 item 5 | M1 Vault hardening |
| Segment compaction (chain-preserving rewrite) | S01 F1 | M1 Vault hardening |
| ADR-0001 untested items: same-valid-time conflict, out-of-order observation, export/import round-trip | Review 15 F4 | M1 ingestion + export slices |
| Plugin approval-to-import atomicity; files not listed in RECORD | Review 15 F5 (S02) | Plugin activation slice |
| `spikes/s03_fts/frozen/thresholds.json` says "24k-document" (actual 25,000); the file is hash-frozen, so fix only in a new versioned protocol | Review 15 F6 | none (evidence stays frozen) |
| Re-run S01 in a fresh pinned venv to refresh its recorded run | Review 15 F1 | optional |
| OPML/Folder held-item review loop, stale review items, held growth | S05A rounds 2–3 | Review workflow slice |
| Pending-review ops may also flag dependent facts | S05A round 3 note 2 | Review workflow slice |
| Tests for bad locator values, `records/` and state-directory permissions, and revoking a memory candidate | Review 19 N4 | Next Vault slice |
| Manifest schema: strict typing (`contract_version = true` coerces), duplicate egress/recipe entries, file name must equal `id`, orphan message keys, `suggested_sources` vocabulary | Review 20 N3 | Plugin activation slice |
| i18n polish: localized `recipe show` unknown-id error, CJK list separator `、`, CJK column widths, `--lang fr` notice, Claude Desktop file-access wording, retention heading vs provider-managed data | Review 20 N7, Review 21 | i18n pass |
| R3-demoted parent's children become moves under the parent's new generated ID | Review 22/23 | MarginNote ingest slice |
| Replay harness: hidden truth attribute inflates modify/no-op counts; restart stopped chains at later full snapshots; order roots by canvas position | Review 22/23 | MarginNote ingest slice |
| MarginNote: permanent no-parent-stat TCC pre-probe test; deterministic multi-parent ordering; refresh Evidence on locator-only drift; source-specific crash/replay test | Review 25 R1–R3 | MarginNote hardening |
| Profile export: injected render/rename/race tests, broader adversarial Markdown/control characters, explicit corrected/retracted Fact and withdrawn Evidence chains | Review 27 N2–N5 | Export hardening |
| Memory proposals: extend high-confidence protected-pattern corpus and keep errors/logs content-free; preserve forced concurrent-idempotency regression | Review 28 N3–N4 | Memory hardening |
| Restore journal: fold segment-read failure into journal validation, and tell "journal not applicable, keep the old generation" apart from genuine corruption | Review 31 N1 | Vault hardening |
| Route `source list` and the `source add-folder` / `add-github` echoes through `_delimited_untrusted()` as `privacy status` now does | Review 31 N2 | Source UX hardening |
| Narrow the confusable flag to real confusable/bidi characters so ordinary CJK or accented names are not labelled | Review 31 N6 | i18n pass |
| Strict schema validation for stored purge previews and intent result values (`_preview_from_dict` still coerces) | Review 30, Review 31 | Privacy hardening |
| Make `_owned_child()` and the deletion that follows descriptor-relative (`dir_fd`, no-follow) before broadening the threat claim | Review 30, Review 31 | Privacy hardening |
| `privacy status` column widths overflow for long control labels | Self-review 2026-09-20 | i18n/CLI polish |
| `src/aptuni/application/privacy.py` is past the 400-line guidance; split inventory, preview and confirm once the contract stops moving | Self-review 2026-09-20 | Privacy hardening |
| An unreadable committed purge intent still wedges canonical writes with no in-product remedy | Review 32 N3 | Privacy hardening |
| A wedged purge action id is not discoverable from any surface; `privacy status` should name the committed intent | Review 32 N6 | Privacy hardening |
| Backup restore preview can still accept a manifest whose ledger-drop simulation is refused only at confirmation; align the claim or move the simulation earlier | Review 37 N17 | Backup/restore hardening |
| Backup verification: pin symlinked `HEAD.json`/`records`/manifest tests, validate every digest read, tolerate Finder `.DS_Store`, and clarify source-folder versus replay-state wording | Review 36 N13/N15; Review 37 N18–N20 | Backup/restore hardening |
| Resolve the sync-root filesystem gate against a resolved home path so a symlinked `HOME` cannot bypass it | Review 37 observation | Vault filesystem hardening |

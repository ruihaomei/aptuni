# Rejected approaches

Considered and rejected, with the evidence. Reopen one only if new evidence shows a concrete defect
in the chosen alternative.

| Rejected | Chosen instead | Evidence |
|---|---|---|
| A backend database (Mem0, Graphiti, SQLite) as source of truth | Open-format Vault; everything else is a projection | ADR-0001, S01 |
| One distribution per component from day one | One `src/` distribution with entry-point seams | ADR-0002 option A |
| Trusting a plugin manifest as a sandbox | Detection-only integrity; activated plugins are trusted code | ADR-0002, S02 F4 |
| SQLite FTS5 `trigram` or plain `unicode61` for bilingual search | `unicode61` over 2–4-char CJK lexemes | S03 (two-character Chinese terms unanswerable otherwise) |
| A broker that claims host confinement (`confined` status) | Honest host trust boundary: `not_in_effect` / `unverified` only | ADR-0013, S04 |
| Trusting MarginNote OPML vendor node IDs | Generated IDs + conservative structural matching; vendor ID only when proven | S05A, KI-020 |
| Content-addressed delta id as the delivery identity | Per-source `sequence` inside `delta_id` | S05A review round 2 |
| Treating a partial scan's unseen items as moved or deleted | Explicit `coverage`; partial never infers moves/removals | S05A review round 1 |
| jieba query segmentation for CJK retrieval (2026-10-01) | Keep 2–4-char lexemes; whole-keyword fallback | `findings/retrieval-experiments.md`: no precision gain, negatives worse |
| Dense lane with `BAAI/bge-small-zh-v1.5` (2026-10-01) | Lexical + concept diversification; retest with a multilingual model | `findings/retrieval-experiments.md`: lower P@10 in every style; no score floor separates negatives |
| IDF / information-coverage gates and generic-word lists on the plain-query fallback (2026-10-02) | Host concepts matched whole (ADR-0030) | `findings/retrieval-experiments.md`: empties long/task queries or keeps leaks |
| Optional dense or cross-encoder semantic backend (2026-10-02) | Lexical concept mode; revisit only if hosts omit concepts | Same note: leaks 67%→25% on plain queries, no relevance gain, 0.22–1.04 GB models |
| Guidance exception: concrete artifact/method concepts for choosing among unnamed own items (2026-10-08) | Ordinary concept guidance; candidate discovery remains an open owner-level design question | `docs/dev/b10-continuation/r1-localization-results.md`: dev gain over-fit software repos; fresh strict 1/6 vs 1/6, entity recall 5/21 vs 7/21; moved R1b to R1c |
| Bounded cutoff/diversity widening for selection (one-per-group round-robin, deep over-fetch, limit 20, 8,000 units; offline, 2026-10-08) | Not adopted | Same report: 12 → 17 of 42 pool entities at twice the budget |

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

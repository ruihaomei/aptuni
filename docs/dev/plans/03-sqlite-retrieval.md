# Milestone 1 Slice 3 — SQLite/FTS Retrieval

**Status:** Complete (implementation and local verification; checkpoint pending)
**Decision basis:** ADR-0004 accepted after S03; no new architecture research required.

## User-visible capability

`aptuni search QUERY` retrieves current, permitted canonical Facts, Memories, and Evidence in English,
Chinese, or mixed text. `aptuni index status|rebuild|delete` makes the disposable projection visible
and controllable.

## TDD acceptance map

1. Deterministic NFKC/casefold normalization emits ASCII terms plus overlapping 2–4-character CJK
   lexemes, matching S03's selected implementation.
2. FTS metacharacters are treated as data; empty/punctuation-only queries return no rows.
3. Only `RecordSet.exposable()` current records are indexed, and every result is rehydrated and
   rechecked against a stable final Vault snapshot before return.
4. Module filters, result limits, corrections, retractions, and expose-policy changes are enforced.
5. The projection records its schema/lexeme/Vault sequence, rebuilds automatically when stale or
   missing, exposes size/count, and can be deleted/rebuilt without changing canonical Vault bytes.
6. Rebuild is atomic, private (`0700` directory, `0600` database), serialized across processes, and
   never replaces a newer projection with an older Vault sequence.
7. Missing FTS5 or corrupt projection state yields a stable application error, never a traceback.

## Exact verification

```sh
.tools/bin/uv run pytest tests/unit/retrieval tests/integration/test_retrieval.py tests/integration/test_cli.py
.tools/bin/uv run pytest
.tools/bin/uv run ruff check .
.tools/bin/uv run mypy src
python3.13 tools/check_relay.py
```

## Explicit exclusions

No embeddings, model inference, remote service, automatic query expansion, or Context API layering
in this slice. S03's synthetic-corpus and broad-short-query noise limits remain explicit.

## Exit evidence

- Full suite: 148 tests and 47 subtests passed.
- Ruff and mypy strict passed; relay checker and its 20 unit tests passed.
- Frozen S03 evidence reproduced on CPython 3.13.3 / SQLite 3.53.2.
- Wheel and sdist built; a clean wheel install completed `init → remember → bilingual search →
  index status`, and dependency checking passed.

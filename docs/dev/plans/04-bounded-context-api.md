# Milestone 1 Slice 4 — Bounded Context API

**Status:** Complete (implementation and local verification; checkpoint pending)
**Decision basis:** ADR-0005, ADR-0007, ADR-0012, PRD §§18–19, and the accepted SQLite projection.

## User-visible capability

- `aptuni identity --budget N` returns a conservative L0 identity card from current permitted
  identity facts.
- `aptuni context QUERY --module M --budget N [--evidence]` returns deterministic L1–L4 context
  units with canonical IDs, provenance, layer markers, and exact conservative budget accounting.

This slice serves the local owner CLI only. MCP/host callers require the next slice's principal,
scope, and `host_model_egress` enforcement and cannot treat this as pre-authorized remote output.

## TDD acceptance map

1. Unit cost is canonical JSON UTF-8 bytes plus 32 units per section/record, with a 32-unit response
   metadata reserve; used units never exceed the requested budget.
2. Records are indivisible. Omitted sections/records set `truncated`; response reports requested,
   used, remaining, included layers, Vault sequence, and policy epoch.
3. L0 conservatively contains only current exposable user-declared identity facts, avoiding taint
   laundering inside a composite card. L1/L2 contain only permitted typed metadata. L3
   contains current Facts/Memories. L4 is opt-in and contains minimized Evidence, never raw files.
4. Every L3/L4 unit carries a canonical ID, module, trust/taint, and source ID when present.
5. Ranking and tie breaks come from the accepted retriever; module selection, limit, malformed
   requests, CJK text, and FTS metacharacters are deterministic.
6. Composition retries when the Vault/policy changes and rechecks `exposable()` immediately before
   returning; hidden, pending, quarantined, retracted, and superseded records never appear.
7. CLI JSON and direct service calls share the same response shape and stable application errors.

## Verification

```sh
.tools/bin/uv run pytest tests/unit/application/test_context.py tests/integration/test_context.py tests/integration/test_cli.py
.tools/bin/uv run pytest
.tools/bin/uv run ruff check .
.tools/bin/uv run mypy src
python3.13 tools/check_relay.py
```

## Explicit exclusions

No MCP transport, host principal admission, remote-model egress grant, embeddings, summarizing model,
raw-source expansion, automatic memory promotion, or generated L0 cache in this slice.

## Exit evidence

- 166 tests plus 47 subtests passed; Ruff and mypy strict passed.
- Relay checker and all 20 relay unit tests passed; S03 retrieval evidence still reproduces.
- Budget tests cover UTF-8 bytes, exact fit, indivisible records, truncation, query/limit bounds,
  frozen context-noise arithmetic, and deterministic unchanged responses.
- Exposure tests cover hidden identity, L4 opt-in, taint/provenance, policy changes during retrieval,
  and policy changes during response packing.
- sdist/wheel built successfully. A clean wheel install completed `init → remember identity/fact →
  L0 identity → bilingual L1–L3 context`; dependency checking passed.
- Review 16 remains `BLOCK`, explicitly pending independent focused re-review.

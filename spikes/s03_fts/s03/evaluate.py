"""S03 evaluation logic, fixed before comparative execution."""

from __future__ import annotations

import json
import math
import tempfile
import time
from pathlib import Path
from typing import Any

from s03.metrics import check_thresholds, summarize
from s03.retrieval import SearchDocument, SqliteRetriever, VARIANTS


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def as_documents(records: list[dict[str, Any]]) -> list[SearchDocument]:
    return [SearchDocument(str(record["id"]), str(record["text"]), str(record["lang"]))
            for record in records]


def evaluate_variant(
    variant: str,
    documents: list[SearchDocument],
    queries: list[dict[str, Any]],
) -> tuple[dict[str, float], dict[str, list[str]]]:
    with SqliteRetriever(variant, documents) as retriever:
        results = {str(query["id"]): retriever.search(str(query["text"])) for query in queries}
    return summarize(queries, results), results


def select_variant(
    summaries: dict[str, dict[str, float]],
    scaled: dict[str, dict[str, float]],
    per_split_thresholds: dict[str, float],
    scaled_thresholds: dict[str, float],
) -> tuple[str, dict[str, list[str]]]:
    """Choose only among variants clearing every dev and scale threshold.

    The frozen quality ordering is recall@5, MRR, two-character found rate, then lower false-positive
    rate. The variant name is a final deterministic tie-break; it has no semantic preference.
    """
    misses: dict[str, list[str]] = {}
    eligible: list[str] = []
    for variant in VARIANTS:
        variant_misses = check_thresholds(summaries[variant], per_split_thresholds)
        variant_misses.extend(check_thresholds(scaled[variant], scaled_thresholds))
        misses[variant] = variant_misses
        if not variant_misses:
            eligible.append(variant)
    if not eligible:
        raise RuntimeError("no S03 variant clears all precommitted dev and scale thresholds")
    chosen = max(
        eligible,
        key=lambda name: (
            summaries[name]["recall_at_5"],
            summaries[name]["mrr"],
            summaries[name]["two_char_found_rate"],
            -summaries[name]["false_positive_rate"],
            name,
        ),
    )
    return chosen, misses


def _p95(values: list[float]) -> float:
    if not values:
        raise ValueError("p95 requires observations")
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def measure_scaled(
    variant: str,
    documents: list[SearchDocument],
    queries: list[dict[str, Any]],
    copies: int,
) -> dict[str, float]:
    expanded = [
        SearchDocument(f"{document.doc_id}--{copy:03d}", document.text, document.lang)
        for copy in range(copies)
        for document in documents
    ]
    raw_bytes = sum(len(document.text.encode("utf-8")) for document in expanded)
    with tempfile.TemporaryDirectory() as raw_tmp:
        database = Path(raw_tmp) / f"{variant}.sqlite3"
        retriever = SqliteRetriever(variant, expanded, database)
        timings: list[float] = []
        for _ in range(3):
            for query in queries:
                started = time.perf_counter()
                retriever.search(str(query["text"]))
                timings.append((time.perf_counter() - started) * 1000)
        retriever.close()
        size = database.stat().st_size
    return {
        "documents": float(len(expanded)),
        "p95_latency_ms": _p95(timings),
        "index_size_bytes": float(size),
        "source_text_bytes": float(raw_bytes),
        "index_size_ratio": size / raw_bytes,
    }

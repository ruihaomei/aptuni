"""Frozen S03 metric definitions (checksummed in FREEZE.json before any comparison)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

K = 5
MRR_DEPTH = 10


def recall_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int = K) -> float:
    """|relevant ∩ top-k| / min(|relevant|, k); 1.0 is achievable when |relevant| > k."""
    if not relevant:
        raise ValueError("recall is undefined for a query with no relevant documents")
    return len(set(ranked[:k]) & set(relevant)) / min(len(relevant), k)


def reciprocal_rank(ranked: Sequence[str], relevant: Sequence[str], depth: int = MRR_DEPTH) -> float:
    for position, doc_id in enumerate(ranked[:depth], start=1):
        if doc_id in relevant:
            return 1.0 / position
    return 0.0


def found_in_top_k(ranked: Sequence[str], relevant: Sequence[str], k: int = K) -> bool:
    return bool(set(ranked[:k]) & set(relevant))


def summarize(queries: Sequence[dict[str, Any]], results: dict[str, list[str]]) -> dict[str, float]:
    """Aggregate blocking metrics for one variant over one query split."""
    positive = [q for q in queries if q["relevant"]]
    negative = [q for q in queries if not q["relevant"]]
    two_char = [q for q in positive if q["kind"] == "zh_two_char"]
    return {
        "queries": float(len(queries)),
        "recall_at_5": sum(recall_at_k(results[q["id"]], q["relevant"]) for q in positive) / len(positive),
        "mrr": sum(reciprocal_rank(results[q["id"]], q["relevant"]) for q in positive) / len(positive),
        "two_char_found_rate": (sum(found_in_top_k(results[q["id"]], q["relevant"]) for q in two_char)
                                / len(two_char)) if two_char else 1.0,
        "false_positive_rate": (sum(bool(results[q["id"]]) for q in negative) / len(negative))
        if negative else 0.0,
    }


def check_thresholds(summary: dict[str, float], thresholds: dict[str, float]) -> list[str]:
    """Return human-readable threshold misses (empty list means pass)."""
    misses = []
    for name, bound in thresholds.items():
        if name.endswith("_min"):
            metric, upper = name[: -len("_min")], False
        elif name.endswith("_max"):
            metric, upper = name[: -len("_max")], True
        else:
            misses.append(f"threshold {name} must end in _min or _max")
            continue
        if metric not in summary:
            misses.append(f"metric {metric} missing from summary")
            continue
        value = summary[metric]
        if (upper and value > bound) or (not upper and value < bound):
            misses.append(f"{metric}={value:.3f} violates {'<=' if upper else '>='} {bound}")
    return misses

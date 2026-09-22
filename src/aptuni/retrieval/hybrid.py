"""Deterministic reciprocal-rank fusion for explicit hybrid retrieval."""

from __future__ import annotations

from collections.abc import Sequence

from aptuni.retrieval.sqlite import SearchRow

RRF_K = 60


def reciprocal_rank_fusion(
    lexical: Sequence[SearchRow], semantic: Sequence[SearchRow], *, limit: int,
) -> list[SearchRow]:
    """Fuse ranks only; upstream score scales are intentionally ignored."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    ranks: dict[str, dict[str, int]] = {}
    for lane, rows in (("lexical", lexical), ("semantic", semantic)):
        seen: set[str] = set()
        for rank, row in enumerate(rows, start=1):
            if row.record_id in seen:
                raise ValueError("duplicate retrieval id in one lane")
            seen.add(row.record_id)
            ranks.setdefault(row.record_id, {})[lane] = rank

    def score(lane_ranks: dict[str, int]) -> float:
        return sum(1.0 / (RRF_K + rank) for rank in lane_ranks.values())

    ordered = sorted(
        ranks,
        key=lambda record_id: (
            -score(ranks[record_id]),
            -len(ranks[record_id]),
            -("lexical" in ranks[record_id]),
            record_id,
        ),
    )
    return [SearchRow(record_id, score(ranks[record_id])) for record_id in ordered[:limit]]

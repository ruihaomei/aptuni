"""Deterministic rank-only fusion for the opt-in hybrid retrieval preview."""

from aptuni.retrieval.hybrid import reciprocal_rank_fusion
from aptuni.retrieval.sqlite import SearchRow


def test_fusion_deduplicates_and_rewards_agreement() -> None:
    lexical = [SearchRow("mem_lex", 1000.0), SearchRow("mem_both", 1.0)]
    semantic = [SearchRow("mem_sem", -999.0), SearchRow("mem_both", -1000.0)]

    rows = reciprocal_rank_fusion(lexical, semantic, limit=3)

    assert [row.record_id for row in rows] == ["mem_both", "mem_lex", "mem_sem"]
    assert len({row.record_id for row in rows}) == 3


def test_fusion_ignores_input_scores_and_is_stable_by_lane_then_id() -> None:
    first = reciprocal_rank_fusion(
        [SearchRow("mem_z", -1e12)],
        [SearchRow("mem_a", 1e12)],
        limit=2,
    )
    second = reciprocal_rank_fusion(
        [SearchRow("mem_z", 1e12)],
        [SearchRow("mem_a", -1e12)],
        limit=2,
    )

    assert [row.record_id for row in first] == ["mem_z", "mem_a"]
    assert first == second


def test_fusion_rejects_duplicate_ids_within_one_lane() -> None:
    rows = [SearchRow("mem_duplicate", 1.0), SearchRow("mem_duplicate", 0.5)]

    try:
        reciprocal_rank_fusion(rows, [], limit=2)
    except ValueError as error:
        assert str(error) == "duplicate retrieval id in one lane"
    else:
        raise AssertionError("duplicate lane rows must fail closed")


def test_fusion_breaks_a_full_tie_on_the_canonical_id() -> None:
    """Both ids appear in both lanes at mirrored ranks, so only the id can order them."""
    forward = reciprocal_rank_fusion(
        [SearchRow("mem_b", 1.0), SearchRow("mem_a", 0.5)],
        [SearchRow("mem_a", 1.0), SearchRow("mem_b", 0.5)],
        limit=2,
    )
    mirrored = reciprocal_rank_fusion(
        [SearchRow("mem_a", 0.5), SearchRow("mem_b", 1.0)],
        [SearchRow("mem_b", 0.5), SearchRow("mem_a", 1.0)],
        limit=2,
    )

    assert [row.record_id for row in forward] == ["mem_a", "mem_b"]
    assert [row.record_id for row in mirrored] == ["mem_a", "mem_b"]


def test_fusion_rejects_a_limit_outside_the_bounded_range() -> None:
    for limit in (0, 101, True):
        try:
            reciprocal_rank_fusion([SearchRow("mem_a", 1.0)], [], limit=limit)  # type: ignore[arg-type]
        except ValueError as error:
            assert str(error) == "limit must be between 1 and 100"
        else:
            raise AssertionError(f"limit {limit!r} must fail closed")

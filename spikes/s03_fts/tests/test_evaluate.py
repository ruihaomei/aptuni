"""Pin S03 variant selection and percentile behavior before comparison."""

from __future__ import annotations

import unittest

from s03.evaluate import _p95, select_variant


THRESHOLDS = {"recall_at_5_min": 0.85, "mrr_min": 0.70,
              "two_char_found_rate_min": 1.0, "false_positive_rate_max": 0.10}
SCALED_THRESHOLDS = {"p95_latency_ms_max": 50.0, "index_size_ratio_max": 10.0}


def quality(recall: float, mrr: float, two_char: float = 1.0, fpr: float = 0.0) -> dict[str, float]:
    return {"recall_at_5": recall, "mrr": mrr, "two_char_found_rate": two_char,
            "false_positive_rate": fpr}


class SelectionTests(unittest.TestCase):
    def test_only_threshold_clean_variant_can_win(self) -> None:
        summaries = {
            "unicode61": quality(0.90, 0.90, two_char=0.0),
            "trigram": quality(0.95, 0.95, two_char=0.0),
            "cjk_lexemes": quality(0.90, 0.80),
        }
        scaled = {name: {"p95_latency_ms": 5.0, "index_size_ratio": 2.0} for name in summaries}
        chosen, misses = select_variant(summaries, scaled, THRESHOLDS, SCALED_THRESHOLDS)
        self.assertEqual("cjk_lexemes", chosen)
        self.assertTrue(misses["unicode61"])

    def test_scaled_failure_disqualifies_variant(self) -> None:
        summaries = {name: quality(0.90, 0.80) for name in
                     ("unicode61", "trigram", "cjk_lexemes")}
        scaled = {name: {"p95_latency_ms": 5.0, "index_size_ratio": 2.0} for name in summaries}
        scaled["cjk_lexemes"]["p95_latency_ms"] = 51.0
        chosen, misses = select_variant(summaries, scaled, THRESHOLDS, SCALED_THRESHOLDS)
        self.assertNotEqual("cjk_lexemes", chosen)
        self.assertTrue(misses["cjk_lexemes"])

    def test_no_eligible_variant_is_blocking(self) -> None:
        summaries = {name: quality(0.1, 0.1, two_char=0.0) for name in
                     ("unicode61", "trigram", "cjk_lexemes")}
        scaled = {name: {"p95_latency_ms": 5.0, "index_size_ratio": 2.0} for name in summaries}
        with self.assertRaisesRegex(RuntimeError, "no S03 variant"):
            select_variant(summaries, scaled, THRESHOLDS, SCALED_THRESHOLDS)

    def test_nearest_rank_p95(self) -> None:
        self.assertEqual(95.0, _p95([float(value) for value in range(1, 101)]))


if __name__ == "__main__":
    unittest.main()

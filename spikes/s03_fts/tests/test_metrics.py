"""Pin the frozen metric definitions and the threshold gate (both directions)."""

from __future__ import annotations

import unittest

from s03.metrics import check_thresholds, found_in_top_k, recall_at_k, reciprocal_rank, summarize


class MetricTests(unittest.TestCase):
    def test_recall_caps_denominator_at_k(self) -> None:
        relevant = [f"r{i}" for i in range(8)]
        self.assertEqual(1.0, recall_at_k(["r0", "r1", "r2", "r3", "r4"], relevant))
        self.assertEqual(0.4, recall_at_k(["r0", "x", "r1", "y", "z"], relevant))

    def test_recall_requires_relevant_docs(self) -> None:
        with self.assertRaises(ValueError):
            recall_at_k(["a"], [])

    def test_reciprocal_rank(self) -> None:
        self.assertEqual(0.5, reciprocal_rank(["x", "r"], ["r"]))
        self.assertEqual(0.0, reciprocal_rank(["x"] * 10 + ["r"], ["r"]))

    def test_found_in_top_k(self) -> None:
        self.assertTrue(found_in_top_k(["x", "x", "x", "x", "r"], ["r"]))
        self.assertFalse(found_in_top_k(["x", "x", "x", "x", "x", "r"], ["r"]))

    def test_summary_and_false_positives(self) -> None:
        queries = [
            {"id": "p", "kind": "zh_two_char", "relevant": ["a"]},
            {"id": "n1", "kind": "negative", "relevant": []},
            {"id": "n2", "kind": "negative", "relevant": []},
        ]
        summary = summarize(queries, {"p": ["a"], "n1": ["z"], "n2": []})
        self.assertEqual(1.0, summary["recall_at_5"])
        self.assertEqual(1.0, summary["two_char_found_rate"])
        self.assertEqual(0.5, summary["false_positive_rate"])


class ThresholdGateTests(unittest.TestCase):
    def test_minimum_threshold_miss_is_reported(self) -> None:
        self.assertTrue(check_thresholds({"recall_at_5": 0.5}, {"recall_at_5_min": 0.85}))

    def test_maximum_threshold_miss_is_reported(self) -> None:
        self.assertTrue(check_thresholds({"false_positive_rate": 0.2}, {"false_positive_rate_max": 0.1}))

    def test_passing_values_produce_no_misses(self) -> None:
        self.assertEqual([], check_thresholds({"recall_at_5": 0.9, "false_positive_rate": 0.0},
                                              {"recall_at_5_min": 0.85, "false_positive_rate_max": 0.1}))

    def test_missing_metric_is_a_miss_not_a_pass(self) -> None:
        self.assertTrue(check_thresholds({}, {"mrr_min": 0.7}))


if __name__ == "__main__":
    unittest.main()

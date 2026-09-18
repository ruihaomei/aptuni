"""Contract tests for the three isolated SQLite FTS5 variants."""

from __future__ import annotations

import unittest

from s03.retrieval import SearchDocument, SqliteRetriever, cjk_lexemes


DOCS = [
    SearchDocument("survival", "学过生存分析，也学习了删失与KM曲线。", "zh"),
    SearchDocument("forest", "周末喜欢在森林里徒步，也玩生存类游戏。", "zh"),
    SearchDocument("cox", "Studied Cox proportional hazards and hazard ratios.", "en"),
    SearchDocument("hidden", "private Bayesian posterior notes", "en", visible=False),
    SearchDocument("expired", "old Bayesian posterior notes", "en", current=False),
]


class LexemeTests(unittest.TestCase):
    def test_cjk_lexemes_are_deterministic_and_include_two_char_terms(self) -> None:
        first = cjk_lexemes("生存分析 KKT条件")
        self.assertEqual(first, cjk_lexemes("生存分析 KKT条件"))
        self.assertIn("生存", first)
        self.assertIn("kkt", first)
        self.assertEqual(len(first), len(set(first)))


class RetrievalTests(unittest.TestCase):
    def test_all_variants_find_english_terms(self) -> None:
        for variant in ("unicode61", "trigram", "cjk_lexemes"):
            with self.subTest(variant=variant), SqliteRetriever(variant, DOCS) as retriever:
                self.assertEqual("cox", retriever.search("Cox hazards", limit=1)[0])

    def test_cjk_lexemes_finds_two_character_query_without_substring_noise(self) -> None:
        with SqliteRetriever("cjk_lexemes", DOCS) as retriever:
            self.assertEqual(["survival"], retriever.search("生存", limit=1))
            self.assertEqual([], retriever.search("生存游戏攻略"))

    def test_trigram_has_defined_two_character_failure(self) -> None:
        with SqliteRetriever("trigram", DOCS) as retriever:
            self.assertEqual([], retriever.search("生存"))

    def test_permission_and_temporal_filters_are_mandatory(self) -> None:
        for variant in ("unicode61", "trigram", "cjk_lexemes"):
            with self.subTest(variant=variant), SqliteRetriever(variant, DOCS) as retriever:
                self.assertEqual([], retriever.search("Bayesian posterior"))

    def test_fts_metacharacters_are_data_not_query_syntax(self) -> None:
        for variant in ("unicode61", "trigram", "cjk_lexemes"):
            with self.subTest(variant=variant), SqliteRetriever(variant, DOCS) as retriever:
                self.assertEqual([], retriever.search('" OR NOT * : ^'))

    def test_unknown_variant_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown retrieval variant"):
            SqliteRetriever("not-real", DOCS)


if __name__ == "__main__":
    unittest.main()
